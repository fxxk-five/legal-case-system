from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote

from app.core.config import settings
from app.integrations.storage.base import StorageObjectInfo, storage_error


class TencentCOSClient:
    def __init__(self) -> None:
        try:
            from qcloud_cos import CosConfig, CosS3Client  # type: ignore
        except ImportError as exc:  # pragma: no cover - exercised in deployment, not unit tests
            raise storage_error(
                "COS SDK 未安装，无法启用云对象存储。",
                detail="请安装 cos-python-sdk-v5 后重试。",
            ) from exc

        secret_id = settings.TENCENT_COS_SECRET_ID.strip()
        secret_key = settings.TENCENT_COS_SECRET_KEY.strip()
        bucket = settings.TENCENT_COS_BUCKET.strip()
        region = settings.TENCENT_COS_REGION.strip()

        if not all([secret_id, secret_key, bucket, region]):
            raise storage_error(
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

    def head_object(self, *, storage_key: str) -> Any:
        return self._client.head_object(Bucket=self.bucket, Key=storage_key)

    def exists(self, *, storage_key: str) -> bool:
        try:
            self.head_object(storage_key=storage_key)
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


def create_cos_client() -> TencentCOSClient:
    return TencentCOSClient()
