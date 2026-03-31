from __future__ import annotations

from fastapi import Request, UploadFile, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import AppError, ErrorCode
from app.core.roles import normalize_role
from app.integrations.storage.service import get_storage_backend
from app.models.user import User
from app.modules.cases.flow import create_case_flow
from app.modules.files.models.file import File
from app.modules.files.case_file_domain_service import CaseFileDomainService
from app.modules.files.case_file_reanalysis_service import CaseFileReanalysisService
from app.modules.files.repository import FilesRepository
from app.modules.files.schemas import FileRead, FileUploadCompleteRequest, FileUploadPolicyRead
from app.modules.files.service import (
    create_direct_upload_completion_token,
    create_stored_file_record,
    decode_direct_upload_completion_token,
    move_storage_object,
    save_upload_file,
    validate_upload_policy_request,
)


class CaseFileService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = FilesRepository(db)
        self.domain_service = CaseFileDomainService(db, repository=self.repo)
        self.reanalysis_service = CaseFileReanalysisService(db, repository=self.repo)

    def list_case_files(self, *, case_id: int, current_user: User) -> list[FileRead]:
        case = self.domain_service.get_case_or_404(case_id=case_id, current_user=current_user)
        self.domain_service.ensure_case_access(case=case, current_user=current_user)
        files = self.repo.list_case_files(case_id=case_id, tenant_id=current_user.tenant_id)
        return [self.domain_service.to_file_read(item, current_user=current_user) for item in files]

    def upload_case_file(
        self,
        *,
        request: Request,
        case_id: int,
        description: str | None,
        upload: UploadFile,
        current_user: User,
    ) -> FileRead:
        case = self.domain_service.get_case_or_404(case_id=case_id, current_user=current_user)
        self.domain_service.ensure_case_access(case=case, current_user=current_user)
        self.domain_service.ensure_case_upload_allowed(case=case, current_user=current_user)

        uploader_role = "client" if normalize_role(current_user.role) == "client" else "lawyer"
        file_record = save_upload_file(
            tenant_id=current_user.tenant_id,
            case_id=case.id,
            uploader_id=current_user.id,
            uploader_role=uploader_role,
            description=description,
            upload=upload,
            db=self.db,
        )
        create_case_flow(
            db=self.db,
            tenant_id=current_user.tenant_id,
            case_id=case.id,
            action_type="file_uploaded",
            content=f"Uploaded file {file_record.file_name}.",
            operator=current_user,
            visible_to="both",
        )
        self.reanalysis_service.run_after_upload(
            request=request,
            case=case,
            upload_user=current_user,
            uploader_role=uploader_role,
        )
        self.repo.commit_and_refresh(file_record)
        return self.domain_service.to_file_read(file_record, current_user=current_user)

    def get_file_upload_policy(
        self,
        *,
        case_id: int,
        file_name: str,
        content_type: str | None,
        current_user: User,
    ) -> FileUploadPolicyRead:
        case = self.domain_service.get_case_or_404(case_id=case_id, current_user=current_user)
        self.domain_service.ensure_case_access(case=case, current_user=current_user)
        self.domain_service.ensure_case_upload_allowed(case=case, current_user=current_user)

        normalized_file_name, detected_mime = validate_upload_policy_request(
            file_name=file_name,
            content_type=content_type,
        )

        backend = get_storage_backend()
        policy = backend.build_upload_policy(
            tenant_id=current_user.tenant_id,
            case_id=case.id,
            file_name=normalized_file_name,
            content_type=detected_mime,
        )
        if policy.mode == "direct_post":
            uploader_role = "client" if normalize_role(current_user.role) == "client" else "lawyer"
            final_storage_key = backend.build_storage_key(
                tenant_id=current_user.tenant_id,
                case_id=case.id,
                file_name=normalized_file_name,
            )
            policy.completion_url = self.domain_service.build_upload_completion_url(case_id=case.id)
            policy.completion_token = create_direct_upload_completion_token(
                tenant_id=current_user.tenant_id,
                case_id=case.id,
                uploader_id=current_user.id,
                uploader_role=uploader_role,
                storage_key=final_storage_key,
                file_name=normalized_file_name,
                content_type=detected_mime,
                upload_storage_key=policy.storage_key,
            )
            policy.expires_in_seconds = settings.FILE_ACCESS_TOKEN_EXPIRE_MINUTES * 60

        return self.domain_service.to_upload_policy_read(policy=policy, backend_name=backend.backend_name)

    def complete_file_upload(
        self,
        *,
        request: Request,
        payload: FileUploadCompleteRequest,
        current_user: User,
        expected_case_id: int | None = None,
    ) -> FileRead:
        token_payload = decode_direct_upload_completion_token(payload.completion_token)
        token_case_id = int(token_payload["case_id"])

        if expected_case_id is not None and token_case_id != expected_case_id:
            raise AppError(
                status_code=status.HTTP_400_BAD_REQUEST,
                code=ErrorCode.FILE_UPLOAD_INVALID,
                message="Completion token case does not match request case.",
                detail="Completion token case does not match request case.",
            )
        if int(token_payload["tenant_id"]) != current_user.tenant_id:
            raise AppError(
                status_code=status.HTTP_403_FORBIDDEN,
                code=ErrorCode.FILE_ACCESS_DENIED,
                message="Completion token tenant does not match current user.",
                detail="Completion token tenant does not match current user.",
            )

        case = self.domain_service.get_case_or_404(case_id=token_case_id, current_user=current_user)
        self.domain_service.ensure_case_access(case=case, current_user=current_user)
        self.domain_service.ensure_case_upload_allowed(case=case, current_user=current_user)

        uploader_role = "client" if normalize_role(current_user.role) == "client" else "lawyer"
        if int(token_payload["uploader_id"]) != current_user.id or str(token_payload["uploader_role"]) != uploader_role:
            raise AppError(
                status_code=status.HTTP_403_FORBIDDEN,
                code=ErrorCode.FILE_ACCESS_DENIED,
                message="Completion token uploader does not match current user.",
                detail="Completion token uploader does not match current user.",
            )

        storage_key = str(token_payload["storage_key"])
        upload_storage_key = str(token_payload.get("upload_storage_key") or storage_key)

        existing_file = self.repo.find_file_by_storage_key(
            tenant_id=current_user.tenant_id,
            storage_key=storage_key,
        )
        if existing_file is not None:
            return self.domain_service.to_file_read(existing_file, current_user=current_user)

        backend = get_storage_backend()
        if upload_storage_key != storage_key:
            if not backend.object_exists(storage_key=storage_key):
                if not backend.object_exists(storage_key=upload_storage_key):
                    raise AppError(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        code=ErrorCode.FILE_UPLOAD_INVALID,
                        message="Uploaded object was not found in storage.",
                        detail="Uploaded object was not found in storage.",
                    )
                try:
                    self.domain_service.validate_uploaded_storage_object_size(storage_key=upload_storage_key)
                except AppError as exc:
                    if exc.status_code == status.HTTP_413_REQUEST_ENTITY_TOO_LARGE:
                        backend.delete_object(storage_key=upload_storage_key)
                    raise
                move_storage_object(source_key=upload_storage_key, target_key=storage_key)
        else:
            if not backend.object_exists(storage_key=storage_key):
                raise AppError(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    code=ErrorCode.FILE_UPLOAD_INVALID,
                    message="Uploaded object was not found in storage.",
                    detail="Uploaded object was not found in storage.",
                )
            self.domain_service.validate_uploaded_storage_object_size(storage_key=storage_key)

        file_record = create_stored_file_record(
            tenant_id=current_user.tenant_id,
            case_id=case.id,
            uploader_id=current_user.id,
            uploader_role=uploader_role,
            storage_key=storage_key,
            file_name=str(token_payload["file_name"]),
            content_type=str(token_payload["content_type"]),
            description=payload.description,
            db=self.db,
        )
        create_case_flow(
            db=self.db,
            tenant_id=current_user.tenant_id,
            case_id=case.id,
            action_type="file_uploaded",
            content=f"Uploaded file {file_record.file_name}.",
            operator=current_user,
            visible_to="both",
        )
        self.reanalysis_service.run_after_upload(
            request=request,
            case=case,
            upload_user=current_user,
            uploader_role=uploader_role,
        )
        self.repo.commit_and_refresh(file_record)
        return self.domain_service.to_file_read(file_record, current_user=current_user)

    def ensure_delete_access(self, *, file_record: File, current_user: User) -> None:
        self.domain_service.ensure_delete_access(file_record=file_record, current_user=current_user)
