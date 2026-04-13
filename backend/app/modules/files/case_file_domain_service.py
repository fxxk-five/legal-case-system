from __future__ import annotations

from fastapi import status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import AppError, ErrorCode
from app.core.roles import can_manage_case_role, normalize_role
from app.integrations.storage.service import get_storage_backend
from app.models.user import User
from app.modules.cases.models.case import Case
from app.modules.cases.policy import ensure_personal_tenant_lawyer_case_visible
from app.modules.files.models.file import File
from app.modules.files.repository import FilesRepository
from app.modules.files.schemas import FileRead, FileUploadPolicyRead
from app.modules.files.service import validate_upload_size_bytes


class CaseFileDomainService:
    def __init__(self, db: Session, *, repository: FilesRepository | None = None) -> None:
        self.db = db
        self.repo = repository or FilesRepository(db)

    def get_case_or_404(self, *, case_id: int, current_user: User) -> Case:
        case = self.repo.get_case(case_id=case_id, tenant_id=current_user.tenant_id)
        if case is None:
            raise AppError(
                status_code=status.HTTP_404_NOT_FOUND,
                code=ErrorCode.CASE_NOT_FOUND,
                message="Case does not exist.",
                detail="Case does not exist.",
            )
        ensure_personal_tenant_lawyer_case_visible(
            self.db,
            current_user=current_user,
            case_id=case.id,
        )
        return case

    def ensure_case_access(self, *, case: Case, current_user: User) -> None:
        if normalize_role(current_user.role) == "client" and case.client_id != current_user.id:
            raise AppError(
                status_code=status.HTTP_403_FORBIDDEN,
                code=ErrorCode.FILE_ACCESS_DENIED,
                message="Current user cannot access this case file.",
                detail="Current user cannot access this case file.",
            )
        ensure_personal_tenant_lawyer_case_visible(
            self.db,
            current_user=current_user,
            case_id=case.id,
            status_code=status.HTTP_403_FORBIDDEN,
            code=ErrorCode.FILE_ACCESS_DENIED,
            message="Current user cannot access this case file.",
            detail="Current user cannot access this case file.",
        )

    def ensure_case_upload_allowed(self, *, case: Case, current_user: User) -> None:
        if normalize_role(current_user.role) != "client":
            return
        if case.client_id is not None:
            return

        raise AppError(
            status_code=status.HTTP_400_BAD_REQUEST,
            code=ErrorCode.FILE_UPLOAD_INVALID,
            message="Current case is not bound to a client user.",
            detail="Current case is not bound to a client user.",
        )

    def ensure_delete_access(self, *, file_record: File, current_user: User) -> None:
        role = normalize_role(current_user.role)
        if role == "client":
            if file_record.uploader_id != current_user.id:
                raise AppError(
                    status_code=status.HTTP_403_FORBIDDEN,
                    code=ErrorCode.FILE_ACCESS_DENIED,
                    message="Client can only delete files uploaded by themselves.",
                    detail="Client can only delete files uploaded by themselves.",
                )
            case = self.repo.get_case(case_id=file_record.case_id, tenant_id=current_user.tenant_id)
            if case is None or case.client_id != current_user.id:
                raise AppError(
                    status_code=status.HTTP_403_FORBIDDEN,
                    code=ErrorCode.FILE_ACCESS_DENIED,
                    message="Current user cannot delete this case file.",
                    detail="Current user cannot delete this case file.",
                )
            return

        if not can_manage_case_role(role):
            raise AppError(
                status_code=status.HTTP_403_FORBIDDEN,
                code=ErrorCode.FILE_ACCESS_DENIED,
                message="Current role cannot delete files.",
                detail="Current role cannot delete files.",
            )

    def to_file_read(self, file_record: File, *, current_user: User) -> FileRead:
        can_download = self._can_download_file(file_record=file_record, current_user=current_user)
        description = file_record.description
        if normalize_role(current_user.role) == "client":
            description = None

        return FileRead(
            id=file_record.id,
            tenant_id=file_record.tenant_id,
            case_id=file_record.case_id,
            uploader_id=file_record.uploader_id,
            uploader_role=file_record.uploader_role,
            file_name=file_record.file_name,
            download_url=file_record.download_url if can_download else None,
            can_download=can_download,
            file_type=file_record.file_type,
            description=description,
            parse_status=file_record.parse_status,
            created_at=file_record.created_at,
            uploader=file_record.uploader,
        )

    def build_upload_completion_url(self, *, case_id: int) -> str:
        return f"{settings.API_V1_STR}/cases/{case_id}/files/complete-upload"

    def to_upload_policy_read(self, *, policy, backend_name: str) -> FileUploadPolicyRead:
        return FileUploadPolicyRead(
            mode=policy.mode,
            upload_url=policy.upload_url,
            method=policy.method,
            headers=policy.headers,
            form_fields=policy.form_fields,
            file_field_name=policy.file_field_name,
            storage_key=policy.storage_key,
            completion_url=policy.completion_url,
            completion_token=policy.completion_token,
            expires_in_seconds=policy.expires_in_seconds,
            backend=backend_name,
        )

    def validate_uploaded_storage_object_size(self, *, storage_key: str) -> None:
        backend = get_storage_backend()
        size_bytes = backend.get_object_size(storage_key=storage_key)
        if size_bytes is None:
            raise AppError(
                status_code=status.HTTP_400_BAD_REQUEST,
                code=ErrorCode.FILE_UPLOAD_INVALID,
                message="Uploaded object metadata could not be verified.",
                detail="Uploaded object metadata could not be verified.",
            )
        validate_upload_size_bytes(size_bytes)

    def can_download_file(self, *, file_record: File, current_user: User) -> bool:
        return self._can_download_file(file_record=file_record, current_user=current_user)

    def _client_can_download_file(self, *, file_record: File, current_user: User) -> bool:
        return file_record.uploader_role == "client" and file_record.uploader_id == current_user.id

    def _can_download_file(self, *, file_record: File, current_user: User) -> bool:
        return normalize_role(current_user.role) != "client" or self._client_can_download_file(
            file_record=file_record,
            current_user=current_user,
        )
