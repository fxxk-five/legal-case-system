from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.models.case import Case
from app.models.file import File
from app.models.user import User
from app.schemas.auth import UserRegister
from app.schemas.case import CaseCreate, CaseInviteRead, CaseListItem, CaseRead, CaseTimelineItem, CaseUpdate
from app.services.auth import create_user
from app.services.mini_program import create_case_invite_token


router = APIRouter(prefix="/cases", tags=["Cases"])


def _build_case_timeline(db: Session, case: Case) -> list[CaseTimelineItem]:
    timeline = [
        CaseTimelineItem(
            event_type="case_created",
            title="案件已创建",
            description=f"案件 {case.case_number} 已创建，当前状态为 {case.status}。",
            occurred_at=case.created_at,
        )
    ]

    if case.client is not None:
        timeline.append(
            CaseTimelineItem(
                event_type="client_bound",
                title="当事人已关联",
                description=f"当事人 {case.client.real_name} 已关联到案件。",
                occurred_at=case.client.created_at,
            )
        )

    if case.deadline is not None:
        timeline.append(
            CaseTimelineItem(
                event_type="deadline_set",
                title="已设置截止日期",
                description=f"案件截止时间为 {case.deadline.isoformat()}。",
                occurred_at=case.deadline,
            )
        )

    files = (
        db.query(File)
        .options(joinedload(File.uploader))
        .filter(File.case_id == case.id, File.tenant_id == case.tenant_id)
        .order_by(File.created_at.asc())
        .all()
    )
    for file_record in files:
        uploader_name = file_record.uploader.real_name if file_record.uploader else "未知用户"
        timeline.append(
            CaseTimelineItem(
                event_type="file_uploaded",
                title="新增案件材料",
                description=f"{uploader_name} 上传了文件 {file_record.file_name}。",
                occurred_at=file_record.created_at,
            )
        )

    return sorted(timeline, key=lambda item: item.occurred_at, reverse=True)


def _get_case_or_404(db: Session, *, case_id: int, tenant_id: int) -> Case:
    case = (
        db.query(Case)
        .options(joinedload(Case.client), joinedload(Case.assigned_lawyer))
        .filter(Case.id == case_id, Case.tenant_id == tenant_id)
        .first()
    )
    if case is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="案件不存在。")
    return case


@router.post("", response_model=CaseRead, status_code=status.HTTP_201_CREATED)
def create_case(
    case_in: CaseCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Case:
    if current_user.role not in {"lawyer", "tenant_admin"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="当前角色不能创建案件。")

    client = (
        db.query(User)
        .filter(User.tenant_id == current_user.tenant_id, User.phone == case_in.client_phone)
        .first()
    )
    if client is None:
        client = create_user(
            db,
            user_in=UserRegister(
                phone=case_in.client_phone,
                password="client123456",
                real_name=case_in.client_real_name,
            ),
            tenant_id=current_user.tenant_id,
            role="client",
        )

    case = Case(
        tenant_id=current_user.tenant_id,
        case_number=case_in.case_number,
        title=case_in.title,
        client_id=client.id,
        assigned_lawyer_id=current_user.id,
        status="new",
        deadline=case_in.deadline,
    )
    db.add(case)
    db.commit()
    db.refresh(case)

    return _get_case_or_404(db, case_id=case.id, tenant_id=current_user.tenant_id)


@router.get("", response_model=list[CaseListItem])
def list_cases(
    status_filter: str | None = Query(default=None, alias="status"),
    skip: int = 0,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Case]:
    query = (
        db.query(Case)
        .options(joinedload(Case.client))
        .filter(Case.tenant_id == current_user.tenant_id)
        .order_by(Case.created_at.desc())
    )
    if current_user.role == "client":
        query = query.filter(Case.client_id == current_user.id)
    if status_filter:
        query = query.filter(Case.status == status_filter)
    return query.offset(skip).limit(limit).all()


@router.get("/{case_id}", response_model=CaseRead)
def get_case(
    case_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Case:
    case = _get_case_or_404(db, case_id=case_id, tenant_id=current_user.tenant_id)
    if current_user.role == "client" and case.client_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权查看该案件。")
    case.timeline = _build_case_timeline(db, case)
    return case


@router.patch("/{case_id}", response_model=CaseRead)
def update_case(
    case_id: int,
    case_in: CaseUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Case:
    case = _get_case_or_404(db, case_id=case_id, tenant_id=current_user.tenant_id)
    is_owner = case.assigned_lawyer_id == current_user.id
    is_admin = current_user.is_tenant_admin or current_user.role == "tenant_admin"
    if not (is_owner or is_admin):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权修改该案件。")

    if case_in.title is not None:
        case.title = case_in.title
    if case_in.status is not None:
        case.status = case_in.status
    if case_in.deadline is not None:
        case.deadline = case_in.deadline
    if case_in.assigned_lawyer_id is not None:
        lawyer = (
            db.query(User)
            .filter(
                User.id == case_in.assigned_lawyer_id,
                User.tenant_id == current_user.tenant_id,
                User.role.in_(["lawyer", "tenant_admin"]),
            )
            .first()
        )
        if lawyer is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="指派律师不存在。")
        case.assigned_lawyer_id = lawyer.id

    db.add(case)
    db.commit()
    db.refresh(case)
    case = _get_case_or_404(db, case_id=case.id, tenant_id=current_user.tenant_id)
    case.timeline = _build_case_timeline(db, case)
    return case


@router.get("/{case_id}/invite-qrcode", response_model=CaseInviteRead)
def get_case_invite_qrcode(
    case_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CaseInviteRead:
    case = _get_case_or_404(db, case_id=case_id, tenant_id=current_user.tenant_id)
    if current_user.role not in {"lawyer", "tenant_admin"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="当前角色不能邀请当事人。")

    token = create_case_invite_token(case_id=case.id, tenant_id=case.tenant_id)
    path = f"pages/client/entry?token={token}"
    return CaseInviteRead(case_id=case.id, tenant_id=case.tenant_id, token=token, path=path)
