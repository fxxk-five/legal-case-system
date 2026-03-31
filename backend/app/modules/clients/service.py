from __future__ import annotations

from datetime import datetime, timezone

from fastapi import status
from sqlalchemy.orm import Session

from app.core.errors import AppError, ErrorCode
from app.core.roles import can_manage_case_role
from app.models.user import User
from app.modules.cases.models.case import Case
from app.modules.clients.repository import ClientsRepository
from app.modules.clients.schemas import ClientCaseSummary, ClientDetailRead, ClientListItem, ClientUpdate


def _mask_phone(phone: str) -> str:
    if len(phone) == 11:
        return f"{phone[:3]}****{phone[-4:]}"
    return "***"


def _ensure_client_access(current_user: User) -> None:
    if not can_manage_case_role(current_user.role):
        raise AppError(
            status_code=status.HTTP_403_FORBIDDEN,
            code=ErrorCode.FORBIDDEN,
            message="当前角色不能访问当事人管理。",
            detail="当前角色不能访问当事人管理。",
        )


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


class ClientService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = ClientsRepository(db)

    def _load_visible_client_data(self, *, current_user: User) -> tuple[dict[int, dict], dict[int, list[Case]]]:
        visible_cases = self.repository.list_visible_cases(current_user=current_user)
        case_ids = [item.id for item in visible_cases]

        last_uploaded_by_case_id: dict[int, datetime] = {}
        for item in self.repository.list_case_files_by_case_ids(tenant_id=current_user.tenant_id, case_ids=case_ids):
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

    def list_clients(
        self,
        *,
        q: str | None,
        sort_by: str,
        sort_order: str,
        current_user: User,
    ) -> list[ClientListItem]:
        _ensure_client_access(current_user)
        client_map, _ = self._load_visible_client_data(current_user=current_user)
        items = list(client_map.values())

        keyword = (q or "").strip().lower()
        if keyword:
            items = [
                item
                for item in items
                if keyword in item["real_name"].lower() or keyword in item["phone"].lower()
            ]

        items = _sort_client_items(items, sort_by=sort_by, sort_order=sort_order)
        for item in items:
            item["phone_masked"] = _mask_phone(item["phone"])

        return [ClientListItem(**item) for item in items]

    def get_client_detail(self, *, client_id: int, current_user: User) -> ClientDetailRead:
        _ensure_client_access(current_user)
        client_map, client_cases_map = self._load_visible_client_data(current_user=current_user)
        client_item = client_map.get(client_id)
        if client_item is None:
            raise AppError(
                status_code=status.HTTP_404_NOT_FOUND,
                code=ErrorCode.USER_NOT_FOUND,
                message="当事人不存在或当前账号无权查看。",
                detail="当事人不存在或当前账号无权查看。",
            )

        cases = sorted(client_cases_map.get(client_id, []), key=lambda item: item.updated_at, reverse=True)
        client_item["phone_masked"] = _mask_phone(client_item["phone"])
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

    def update_client(self, *, client_id: int, payload: ClientUpdate, current_user: User) -> ClientDetailRead:
        _ensure_client_access(current_user)
        client_map, _ = self._load_visible_client_data(current_user=current_user)
        if client_id not in client_map:
            raise AppError(
                status_code=status.HTTP_404_NOT_FOUND,
                code=ErrorCode.USER_NOT_FOUND,
                message="当事人不存在或当前账号无权修改。",
                detail="当事人不存在或当前账号无权修改。",
            )

        client = self.repository.get_client(client_id=client_id, tenant_id=current_user.tenant_id)
        if client is None:
            raise AppError(
                status_code=status.HTTP_404_NOT_FOUND,
                code=ErrorCode.USER_NOT_FOUND,
                message="当事人不存在。",
                detail="当事人不存在。",
            )

        phone_conflict = self.repository.find_phone_conflict(
            tenant_id=current_user.tenant_id,
            phone=payload.phone,
            exclude_user_id=client_id,
        )
        if phone_conflict is not None:
            raise AppError(
                status_code=status.HTTP_409_CONFLICT,
                code=ErrorCode.USER_ALREADY_EXISTS,
                message="该手机号已被当前租户其他账号使用。",
                detail="该手机号已被当前租户其他账号使用。",
            )

        self.repository.update_client_profile(
            client=client,
            real_name=payload.real_name,
            phone=payload.phone,
        )

        return self.get_client_detail(client_id=client_id, current_user=current_user)
