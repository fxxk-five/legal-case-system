from __future__ import annotations

import hashlib
import hmac
import json
import shutil
from base64 import b64encode
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote
from uuid import uuid4

from app.core.config import settings
from app.core.errors import AppError, ErrorCode


def _storage_error(message: str, *, detail: str | None = None) -> AppError:
    return AppError(
        status_code=500,
        code=ErrorCode.STORAGE_ERROR,
        message=message,
        detail=detail or message,
    )


@dataclass
class UploadPolicy:
    mode: str
    upload_url: str
    method: str = "POST"
    headers: dict[str, str] = field(default_factory=dict)
    form_fields: dict[str, str] = field(default_factory=dict)
    file_field_name: str = "upload"
    storage_key: str = ""
    public_base_url: str = ""
    completion_url: str | None = None
    completion_token: str | None = None
    expires_in_seconds: int | None = None


@dataclass
class StorageObjectInfo:
    storage_key: str
    modified_at: datetime | None = None

    @property
    def file_name(self) -> str:
        return Path(self.storage_key).name


class BaseStorageBackend:
    backend_name = "base"

    def build_storage_key(self, *, tenant_id: int, case_id: int, file_name: str) -> str:
        suffix = Path(file_name).suffix
        generated_name = f"{uuid4().hex}{suffix}"
        return (Path(f"tenant_{tenant_id}") / f"case_{case_id}" / "files" / generated_name).as_posix()

    def build_pending_storage_key(self, *, tenant_id: int, case_id: int, file_name: str) -> str:
        suffix = Path(file_name).suffix
        generated_name = f"{uuid4().hex}{suffix}"
        return (Path(f"tenant_{tenant_id}") / f"case_{case_id}" / settings.STORAGE_PENDING_PREFIX / generated_name).as_posix()

    def build_retention_storage_key(self, *, storage_key: str, archived_at: datetime | None = None) -> str:
        timestamp = (archived_at or datetime.now(timezone.utc)).strftime("%Y%m%d%H%M%S")
        return (Path(settings.STORAGE_RETENTION_PREFIX) / f"deleted_at={timestamp}" / Path(storage_key)).as_posix()

    def build_upload_policy(self, *, tenant_id: int, case_id: int, file_name: str, content_type: str | None) -> UploadPolicy:
        raise NotImplementedError

    def save_local_file(
        self,
        *,
        local_path: Path,
        storage_key: str,
        content_type: str,
    ) -> None:
        raise NotImplementedError

    def save_bytes(
        self,
        *,
        data: bytes,
        storage_key: str,
        content_type: str,
    ) -> None:
        raise NotImplementedError

    def move_object(self, *, source_key: str, target_key: str) -> None:
        raise NotImplementedError

    def build_private_download_url(
        self,
        *,
        storage_key: str,
        file_name: str,
        content_type: str | None,
        expires_seconds: int,
    ) -> str | None:
        return None

    def delete_object(self, *, storage_key: str) -> None:
        raise NotImplementedError

    def archive_object(self, *, storage_key: str) -> str | None:
        raise NotImplementedError

    def object_exists(self, *, storage_key: str) -> bool:
        raise NotImplementedError

    def resolve_local_path(self, *, storage_key: str) -> Path:
        raise NotImplementedError

    def list_objects(self, *, prefix: str, suffix: str | None = None) -> list[StorageObjectInfo]:
        raise NotImplementedError


class LocalStorageBackend(BaseStorageBackend):
    backend_name = "local"

    def build_upload_policy(self, *, tenant_id: int, case_id: int, file_name: str, content_type: str | None) -> UploadPolicy:
        return UploadPolicy(
            mode="server_proxy",
            upload_url=f"{settings.API_V1_STR}/files/upload?case_id={case_id}",
            storage_key=self.build_storage_key(tenant_id=tenant_id, case_id=case_id, file_name=file_name),
        )

    def save_local_file(
        self,
        *,
        local_path: Path,
        storage_key: str,
        content_type: str,
    ) -> None:
        target_path = self.resolve_local_path(storage_key=storage_key)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(local_path), str(target_path))

    def save_bytes(
        self,
        *,
        data: bytes,
        storage_key: str,
        content_type: str,
    ) -> None:
        target_path = self.resolve_local_path(storage_key=storage_key)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_bytes(data)

    def move_object(self, *, source_key: str, target_key: str) -> None:
        source_path = self.resolve_local_path(storage_key=source_key)
        if not source_path.exists():
            raise _storage_error(
                "Source object does not exist.",
                detail="Source object does not exist.",
            )

        target_path = self.resolve_local_path(storage_key=target_key)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(source_path), str(target_path))

    def delete_object(self, *, storage_key: str) -> None:
        file_path = self.resolve_local_path(storage_key=storage_key)
        try:
            if file_path.exists():
                file_path.unlink()
        except OSError:
            pass

    def archive_object(self, *, storage_key: str) -> str | None:
        source_path = self.resolve_local_path(storage_key=storage_key)
        if not source_path.exists():
            return None

        archived_key = self.build_retention_storage_key(storage_key=storage_key)
        archived_path = self.resolve_local_path(storage_key=archived_key)
        archived_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(source_path), str(archived_path))
        return archived_key

    def object_exists(self, *, storage_key: str) -> bool:
        return self.resolve_local_path(storage_key=storage_key).exists()

    def resolve_local_path(self, *, storage_key: str) -> Path:
        file_ref = Path(storage_key)
        local_root = Path(settings.LOCAL_STORAGE_DIR)
        if file_ref.is_absolute():
            return file_ref
        if len(file_ref.parts) > 0 and file_ref.parts[0] == local_root.name:
            return Path(*file_ref.parts)
        return local_root / file_ref

    def list_objects(self, *, prefix: str, suffix: str | None = None) -> list[StorageObjectInfo]:
        target_dir = self.resolve_local_path(storage_key=prefix)
        if not target_dir.exists() or not target_dir.is_dir():
            return []

        local_root = Path(settings.LOCAL_STORAGE_DIR)
        objects: list[StorageObjectInfo] = []
        for path in target_dir.iterdir():
            if not path.is_file():
                continue
            if suffix and not path.name.endswith(suffix):
                continue
            try:
                storage_key = path.relative_to(local_root).as_posix()
            except ValueError:
                storage_key = path.as_posix()
            objects.append(
                StorageObjectInfo(
                    storage_key=storage_key,
                    modified_at=datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc),
                )
            )
        return objects


class TencentCOSClient:
    def __init__(self) -> None:
        try:
            from qcloud_cos import CosConfig, CosS3Client  # type: ignore
        except ImportError as exc:  # pragma: no cover - exercised in deployment, not unit tests
            raise _storage_error(
                "COS SDK 未安装，无法启用云对象存储。",
                detail="请安装 cos-python-sdk-v5 后重试。",
            ) from exc

        secret_id = settings.TENCENT_COS_SECRET_ID.strip()
        secret_key = settings.TENCENT_COS_SECRET_KEY.strip()
        bucket = settings.TENCENT_COS_BUCKET.strip()
        region = settings.TENCENT_COS_REGION.strip()

        if not all([secret_id, secret_key, bucket, region]):
            raise _storage_error(
                "COS 配置不完整，无法启用云对象存储。",
                detail="请检查 TENCENT_COS_SECRET_ID / SECRET_KEY / BUCKET / REGION。",
            )

        config = CosConfig(Region=region, SecretId=secret_id, SecretKey=secret_key)
        self._client = CosS3Client(config)
        self.bucket = bucket

    def put_file(self, *, local_path: Path, storage_key: str, content_type: str) -> None:
        with local_path.open("rb") as file_obj:
            self._client.put_object(
                Bucket=self.bucket,
                Body=file_obj,
                Key=storage_key,
                EnableMD5=False,
                ContentType=content_type,
            )

    def put_bytes(self, *, data: bytes, storage_key: str, content_type: str) -> None:
        self._client.put_object(
            Bucket=self.bucket,
            Body=data,
            Key=storage_key,
            EnableMD5=False,
            ContentType=content_type,
        )

    def copy(self, *, source_key: str, target_key: str) -> None:
        self._client.copy_object(
            Bucket=self.bucket,
            Key=target_key,
            CopySource={
                "Bucket": self.bucket,
                "Key": source_key,
                "Region": settings.TENCENT_COS_REGION.strip(),
            },
        )

    def delete(self, *, storage_key: str) -> None:
        self._client.delete_object(Bucket=self.bucket, Key=storage_key)

    def exists(self, *, storage_key: str) -> bool:
        try:
            self._client.head_object(Bucket=self.bucket, Key=storage_key)
            return True
        except Exception:
            return False

    def list_objects(self, *, prefix: str) -> list[StorageObjectInfo]:
        objects: list[StorageObjectInfo] = []
        marker = ""

        while True:
            response = self._client.list_objects(
                Bucket=self.bucket,
                Prefix=prefix,
                Marker=marker,
                MaxKeys=1000,
            )
            contents = response.get("Contents") or []
            for item in contents:
                key = str(item.get("Key") or "").strip()
                if not key or key.endswith("/"):
                    continue
                objects.append(
                    StorageObjectInfo(
                        storage_key=key,
                        modified_at=self._parse_last_modified(item.get("LastModified")),
                    )
                )

            is_truncated = str(response.get("IsTruncated") or "").lower() == "true"
            if not is_truncated:
                break

            marker = str(response.get("NextMarker") or "").strip()
            if not marker and contents:
                marker = str(contents[-1].get("Key") or "").strip()
            if not marker:
                break

        return objects

    @staticmethod
    def _parse_last_modified(value: Any) -> datetime | None:
        if value is None:
            return None
        if isinstance(value, datetime):
            if value.tzinfo is None:
                return value.replace(tzinfo=timezone.utc)
            return value.astimezone(timezone.utc)

        text = str(value).strip()
        if not text:
            return None
        if text.endswith("Z"):
            try:
                return datetime.fromisoformat(text[:-1] + "+00:00").astimezone(timezone.utc)
            except ValueError:
                pass
        try:
            parsed = datetime.fromisoformat(text)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc)
        except ValueError:
            return None

    def build_download_url(
        self,
        *,
        storage_key: str,
        file_name: str,
        content_type: str | None,
        expires_seconds: int,
    ) -> str:
        params: dict[str, str] = {
            "response-content-disposition": f"attachment; filename*=UTF-8''{quote(file_name)}",
        }
        if content_type:
            params["response-content-type"] = content_type
        return self._client.get_presigned_url(
            Method="GET",
            Bucket=self.bucket,
            Key=storage_key,
            Expired=expires_seconds,
            Params=params,
        )


def _create_cos_client() -> TencentCOSClient:
    return TencentCOSClient()


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

    def resolve_local_path(self, *, storage_key: str) -> Path:
        raise _storage_error("COS 存储不支持解析本地文件路径。")

    def list_objects(self, *, prefix: str, suffix: str | None = None) -> list[StorageObjectInfo]:
        objects = self._get_client().list_objects(prefix=prefix)
        if suffix:
            return [item for item in objects if item.file_name.endswith(suffix)]
        return objects

def get_storage_backend() -> BaseStorageBackend:
    if settings.STORAGE_BACKEND == "local":
        return LocalStorageBackend()
    if settings.STORAGE_BACKEND == "cos":
        return COSStorageBackend()
    return LocalStorageBackend()
