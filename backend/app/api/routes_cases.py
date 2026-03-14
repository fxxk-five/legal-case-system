from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.models.case import Case
from app.models.user import User
from app.schemas.case import CaseCreate, CaseListItem, CaseRead, CaseUpdate
from app.services.auth import create_user
from app.schemas.auth import UserRegister


router = APIRouter(prefix="/cases", tags=["Cases"])


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
    return _get_case_or_404(db, case_id=case.id, tenant_id=current_user.tenant_id)
