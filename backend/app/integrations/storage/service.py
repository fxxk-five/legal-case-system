from __future__ import annotations

import hashlib
import hmac
import json
from base64 import b64encode
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.integrations.storage.base import (
    BaseStorageBackend,
    StorageObjectInfo,
    UploadPolicy,
    storage_error as _storage_error,
)
from app.integrations.storage.cos_client import TencentCOSClient, create_cos_client as _create_cos_client
from app.integrations.storage.local_backend import LocalStorageBackend


class COSStorageBackend(BaseStorageBackend):
    backend_name = "cos"

    def __init__(self) -> None:
        self.secret_id = settings.TENCENT_COS_SECRET_ID.strip()
        self.secret_key = settings.TENCENT_COS_SECRET_KEY.strip()
        self.bucket = settings.TENCENT_COS_BUCKET.strip()
        self.region = settings.TENCENT_COS_REGION.strip()
        self.public_base_url = (
            settings.STORAGE_PUBLIC_BASE_URL.strip()
            or f"https://{self.bucket}.cos.{self.region}.myqcloud.com"
        ).rstrip("/")
        self._client: TencentCOSClient | None = None

    def _get_client(self) -> TencentCOSClient:
        if self._client is None:
            self._client = _create_cos_client()
        return self._client

    def _build_key_time(self, *, expires_seconds: int) -> str:
        now = datetime.now(timezone.utc)
        start = int(now.timestamp()) - 5
        end = start + expires_seconds
        return f"{start};{end}"

    def _sign_key(self, key_time: str) -> str:
        digest = hmac.new(
            self.secret_key.encode("utf-8"),
            key_time.encode("utf-8"),
            hashlib.sha1,
        ).hexdigest()
        return digest

    def _build_post_policy(
        self,
        *,
        storage_key: str,
        content_type: str | None,
        expires_seconds: int,
    ) -> tuple[str, dict[str, str]]:
        key_time = self._build_key_time(expires_seconds=expires_seconds)
        expiration = (datetime.now(timezone.utc) + timedelta(seconds=expires_seconds)).strftime("%Y-%m-%dT%H:%M:%SZ")
        conditions: list[Any] = [
            {"bucket": self.bucket},
            {"key": storage_key},
            {"success_action_status": "201"},
            ["content-length-range", 0, settings.FILE_UPLOAD_MAX_SIZE_BYTES],
        ]
        if content_type:
            conditions.append({"Content-Type": content_type})

        policy_raw = {
            "expiration": expiration,
            "conditions": conditions,
        }
        policy = b64encode(json.dumps(policy_raw, separators=(",", ":")).encode("utf-8")).decode("utf-8")
        sign_key = self._sign_key(key_time)
        signature = hmac.new(sign_key.encode("utf-8"), policy.encode("utf-8"), hashlib.sha1).hexdigest()
        fields = {
            "key": storage_key,
            "policy": policy,
            "q-sign-algorithm": "sha1",
            "q-ak": self.secret_id,
            "q-key-time": key_time,
            "q-sign-time": key_time,
            "q-signature": signature,
            "success_action_status": "201",
        }
        if content_type:
            fields["Content-Type"] = content_type
        return f"{self.public_base_url}/", fields

    def build_upload_policy(self, *, tenant_id: int, case_id: int, file_name: str, content_type: str | None) -> UploadPolicy:
        storage_key = self.build_storage_key(tenant_id=tenant_id, case_id=case_id, file_name=file_name)
        if not settings.STORAGE_DIRECT_UPLOAD_ENABLED:
            return UploadPolicy(
                mode="server_proxy",
                upload_url=f"{settings.API_V1_STR}/files/upload?case_id={case_id}",
                storage_key=storage_key,
            )

        pending_storage_key = self.build_pending_storage_key(
            tenant_id=tenant_id,
            case_id=case_id,
            file_name=file_name,
        )
        upload_url, form_fields = self._build_post_policy(
            storage_key=pending_storage_key,
            content_type=content_type,
            expires_seconds=settings.FILE_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )
        return UploadPolicy(
            mode="direct_post",
            upload_url=upload_url,
            method="POST",
            form_fields=form_fields,
            file_field_name="file",
            storage_key=pending_storage_key,
            public_base_url=self.public_base_url,
        )

    def save_local_file(
        self,
        *,
        local_path: Path,
        storage_key: str,
        content_type: str,
    ) -> None:
        self._get_client().put_file(local_path=local_path, storage_key=storage_key, content_type=content_type)
        try:
            if local_path.exists():
                local_path.unlink()
        except OSError:
            pass

    def save_bytes(
        self,
        *,
        data: bytes,
        storage_key: str,
        content_type: str,
    ) -> None:
        self._get_client().put_bytes(data=data, storage_key=storage_key, content_type=content_type)

    def build_private_download_url(
        self,
        *,
        storage_key: str,
        file_name: str,
        content_type: str | None,
        expires_seconds: int,
    ) -> str | None:
        return self._get_client().build_download_url(
            storage_key=storage_key,
            file_name=file_name,
            content_type=content_type,
            expires_seconds=expires_seconds,
        )

    def delete_object(self, *, storage_key: str) -> None:
        try:
            self._get_client().delete(storage_key=storage_key)
        except Exception:
            pass

    def move_object(self, *, source_key: str, target_key: str) -> None:
        client = self._get_client()
        client.copy(source_key=source_key, target_key=target_key)
        client.delete(storage_key=source_key)

    def archive_object(self, *, storage_key: str) -> str | None:
        if not self.object_exists(storage_key=storage_key):
            return None

        archived_key = self.build_retention_storage_key(storage_key=storage_key)
        self.move_object(source_key=storage_key, target_key=archived_key)
        return archived_key

    def object_exists(self, *, storage_key: str) -> bool:
        return self._get_client().exists(storage_key=storage_key)

    def get_object_size(self, *, storage_key: str) -> int | None:
        client = self._get_client()
        try:
            response = client.head_object(storage_key=storage_key)
        except Exception:
            objects = getattr(client, "objects", None)
            if isinstance(objects, dict):
                obj = objects.get(storage_key)
                if isinstance(obj, dict):
                    body = obj.get("body")
                    if isinstance(body, (bytes, bytearray)):
                        return len(body)
            return None
        return self._extract_content_length(response)

    def resolve_local_path(self, *, storage_key: str) -> Path:
        raise _storage_error("COS 存储不支持解析本地文件路径。")

    def list_objects(self, *, prefix: str, suffix: str | None = None) -> list[StorageObjectInfo]:
        objects = self._get_client().list_objects(prefix=prefix)
        if suffix:
            return [item for item in objects if item.file_name.endswith(suffix)]
        return objects

    @staticmethod
    def _extract_content_length(response: Any) -> int | None:
        candidates: list[Any] = [response]
        if isinstance(response, dict):
            headers = response.get("headers")
            if headers is not None:
                candidates.append(headers)
            metadata = response.get("ResponseMetadata")
            if isinstance(metadata, dict):
                http_headers = metadata.get("HTTPHeaders")
                if http_headers is not None:
                    candidates.append(http_headers)

        for candidate in candidates:
            if not isinstance(candidate, dict):
                continue
            for key in ("Content-Length", "content-length", "ContentLength", "contentlength"):
                value = candidate.get(key)
                if value is None:
                    continue
                try:
                    return int(value)
                except (TypeError, ValueError):
                    continue
        return None


def get_storage_backend() -> BaseStorageBackend:
    if settings.STORAGE_BACKEND == "local":
        return LocalStorageBackend()
    if settings.STORAGE_BACKEND == "cos":
        return COSStorageBackend()
    return LocalStorageBackend()
