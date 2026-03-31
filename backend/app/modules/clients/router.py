from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Query as SAQuery
from sqlalchemy.orm import Session, joinedload

from app.core.errors import AppError, ErrorCode
from app.core.roles import can_manage_case_role
from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.models.case import Case
from app.models.file import File
from app.models.user import User
from app.schemas.client import ClientCaseSummary, ClientDetailRead, ClientListItem, ClientUpdate
from app.services.case_visibility import build_visible_case_query


router = APIRouter(prefix="/clients", tags=["Clients"])


def _ensure_client_access(current_user: User) -> None:
    if not can_manage_case_role(current_user.role):
        raise AppError(
            status_code=status.HTTP_403_FORBIDDEN,
            code=ErrorCode.FORBIDDEN,
            message="当前角色不能访问当事人管理。",
            detail="当前角色不能访问当事人管理。",
        )


def _build_visible_cases_query(db: Session, current_user: User) -> SAQuery:
    return build_visible_case_query(db, current_user).options(
        joinedload(Case.client),
        joinedload(Case.assigned_lawyer),
    )


def _load_visible_client_data(db: Session, current_user: User) -> tuple[dict[int, dict], dict[int, list[Case]]]:
    visible_cases = _build_visible_cases_query(db, current_user).all()
    case_ids = [item.id for item in visible_cases]

    last_uploaded_by_case_id: dict[int, datetime] = {}
    if case_ids:
        case_files = (
            db.query(File)
            .filter(File.tenant_id == current_user.tenant_id, File.case_id.in_(case_ids))
            .order_by(File.created_at.desc())
            .all()
        )
        for item in case_files:
            if item.case_id is None or item.case_id in last_uploaded_by_case_id:
                continue
            last_uploaded_by_case_id[item.case_id] = item.created_at

    client_map: dict[int, dict] = {}
    client_cases_map: dict[int, list[Case]] = {}
    for item in visible_cases:
        client = item.client
        if client is None:
            continue
        existing = client_map.get(client.id)
        last_uploaded_at = last_uploaded_by_case_id.get(item.id)
        if existing is None:
            client_map[client.id] = {
                "id": client.id,
                "real_name": client.real_name,
                "phone": client.phone,
                "status": client.status,
                "created_at": client.created_at,
                "updated_at": client.updated_at,
                "case_count": 1,
                "last_uploaded_at": last_uploaded_at,
            }
        else:
            existing["case_count"] += 1
            if last_uploaded_at and (
                existing["last_uploaded_at"] is None or last_uploaded_at > existing["last_uploaded_at"]
            ):
                existing["last_uploaded_at"] = last_uploaded_at

        client_cases_map.setdefault(client.id, []).append(item)

    return client_map, client_cases_map


def _sort_client_items(items: list[dict], *, sort_by: str, sort_order: str) -> list[dict]:
    reverse = sort_order == "desc"
    if sort_by == "case_count":
        return sorted(items, key=lambda item: (item["case_count"], item["updated_at"]), reverse=reverse)
    if sort_by == "last_uploaded_at":
        return sorted(
            items,
            key=lambda item: (
                item["last_uploaded_at"] is None,
                item["last_uploaded_at"] or datetime.min.replace(tzinfo=timezone.utc),
            ),
            reverse=reverse,
        )
    if sort_by == "phone":
        return sorted(items, key=lambda item: item["phone"], reverse=reverse)
    if sort_by == "real_name":
        return sorted(items, key=lambda item: item["real_name"], reverse=reverse)
    return sorted(items, key=lambda item: item["created_at"], reverse=reverse)


@router.get("", response_model=list[ClientListItem])
def list_clients(
    q: str | None = Query(default=None, min_length=1, max_length=100),
    sort_by: str = Query(default="created_at", pattern="^(created_at|real_name|phone|case_count|last_uploaded_at)$"),
    sort_order: str = Query(default="desc", pattern="^(asc|desc)$"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ClientListItem]:
    _ensure_client_access(current_user)
    client_map, _ = _load_visible_client_data(db, current_user)
    items = list(client_map.values())

    keyword = (q or "").strip().lower()
    if keyword:
        items = [
            item
            for item in items
            if keyword in item["real_name"].lower() or keyword in item["phone"].lower()
        ]

    items = _sort_client_items(items, sort_by=sort_by, sort_order=sort_order)
    return [ClientListItem(**item) for item in items]


@router.get("/{client_id}", response_model=ClientDetailRead)
def get_client_detail(
    client_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ClientDetailRead:
    _ensure_client_access(current_user)
    client_map, client_cases_map = _load_visible_client_data(db, current_user)
    client_item = client_map.get(client_id)
    if client_item is None:
        raise AppError(
            status_code=status.HTTP_404_NOT_FOUND,
            code=ErrorCode.USER_NOT_FOUND,
            message="当事人不存在或当前账号无权查看。",
            detail="当事人不存在或当前账号无权查看。",
        )

    cases = sorted(client_cases_map.get(client_id, []), key=lambda item: item.updated_at, reverse=True)
    return ClientDetailRead(
        **client_item,
        cases=[
            ClientCaseSummary(
                id=item.id,
                case_number=item.case_number,
                title=item.title,
                legal_type=item.legal_type,
                status=item.status,
                deadline=item.deadline,
                updated_at=item.updated_at,
                assigned_lawyer_name=item.assigned_lawyer.real_name if item.assigned_lawyer else None,
            )
            for item in cases
        ],
    )


@router.patch("/{client_id}", response_model=ClientDetailRead)
def update_client(
    client_id: int,
    payload: ClientUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ClientDetailRead:
    _ensure_client_access(current_user)
    client_map, _ = _load_visible_client_data(db, current_user)
    if client_id not in client_map:
        raise AppError(
            status_code=status.HTTP_404_NOT_FOUND,
            code=ErrorCode.USER_NOT_FOUND,
            message="当事人不存在或当前账号无权修改。",
            detail="当事人不存在或当前账号无权修改。",
        )

    client = (
        db.query(User)
        .filter(User.id == client_id, User.tenant_id == current_user.tenant_id, User.role == "client")
        .first()
    )
    if client is None:
        raise AppError(
            status_code=status.HTTP_404_NOT_FOUND,
            code=ErrorCode.USER_NOT_FOUND,
            message="当事人不存在。",
            detail="当事人不存在。",
        )

    phone_conflict = (
        db.query(User)
        .filter(
            User.tenant_id == current_user.tenant_id,
            User.phone == payload.phone,
            User.id != client_id,
        )
        .first()
    )
    if phone_conflict is not None:
        raise AppError(
            status_code=status.HTTP_409_CONFLICT,
            code=ErrorCode.USER_ALREADY_EXISTS,
            message="该手机号已被当前租户其他账号使用。",
            detail="该手机号已被当前租户其他账号使用。",
        )

    client.real_name = payload.real_name
    client.phone = payload.phone
    db.add(client)
    db.commit()

    return get_client_detail(client_id=client_id, current_user=current_user, db=db)
