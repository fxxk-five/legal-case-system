from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.auth.deps import get_current_user
from app.models.user import User
from app.modules.clients.service import ClientService
from app.modules.clients.schemas import ClientDetailRead, ClientListItem, ClientUpdate


router = APIRouter(prefix="/clients", tags=["Clients"])

@router.get("", response_model=list[ClientListItem])
def list_clients(
    q: str | None = Query(default=None, min_length=1, max_length=100),
    sort_by: str = Query(default="created_at", pattern="^(created_at|real_name|phone|case_count|last_uploaded_at)$"),
    sort_order: str = Query(default="desc", pattern="^(asc|desc)$"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ClientListItem]:
    return ClientService(db).list_clients(
        q=q,
        sort_by=sort_by,
        sort_order=sort_order,
        current_user=current_user,
    )


@router.get("/{client_id}", response_model=ClientDetailRead)
def get_client_detail(
    client_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ClientDetailRead:
    return ClientService(db).get_client_detail(
        client_id=client_id,
        current_user=current_user,
    )


@router.patch("/{client_id}", response_model=ClientDetailRead)
def update_client(
    client_id: int,
    payload: ClientUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ClientDetailRead:
    return ClientService(db).update_client(
        client_id=client_id,
        payload=payload,
        current_user=current_user,
    )
