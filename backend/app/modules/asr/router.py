from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, File, UploadFile, status

from app.core.config import settings
from app.core.errors import AppError, ErrorCode
from app.modules.auth.deps import get_current_user, require_mini_program_session
from app.models.user import User
from app.modules.asr.schemas import ASRTranscriptionRead
from app.integrations.asr.service import transcribe_audio_bytes


router = APIRouter(prefix="/asr", tags=["ASR"])

_ALLOWED_AUDIO_FORMATS = {"wav", "pcm", "ogg-opus", "speex", "silk", "mp3", "m4a", "aac", "amr"}
_CONTENT_TYPE_FORMAT_MAP = {
    "audio/wav": "wav",
    "audio/x-wav": "wav",
    "audio/wave": "wav",
    "audio/mpeg": "mp3",
    "audio/mp3": "mp3",
    "audio/mp4": "m4a",
    "audio/x-m4a": "m4a",
    "audio/aac": "aac",
    "audio/amr": "amr",
    "audio/basic": "pcm",
}


def _detect_audio_format(upload: UploadFile) -> str:
    suffix = Path(upload.filename or "").suffix.lower().lstrip(".")
    if suffix in _ALLOWED_AUDIO_FORMATS:
        return suffix

    content_type = (upload.content_type or "").split(";", 1)[0].strip().lower()
    if content_type in _CONTENT_TYPE_FORMAT_MAP:
        return _CONTENT_TYPE_FORMAT_MAP[content_type]

    raise AppError(
        status_code=status.HTTP_400_BAD_REQUEST,
        code=ErrorCode.FILE_UPLOAD_INVALID,
        message="暂不支持该音频格式上传。",
        detail=f"支持的格式：{', '.join(sorted(_ALLOWED_AUDIO_FORMATS))}。",
    )


@router.post("/transcribe", response_model=ASRTranscriptionRead)
async def transcribe_audio(
    audio: UploadFile = File(...),
    _: None = Depends(require_mini_program_session),
    current_user: User = Depends(get_current_user),
) -> ASRTranscriptionRead:
    _ = current_user
    voice_format = _detect_audio_format(audio)
    content = await audio.read()
    if not content:
        raise AppError(
            status_code=status.HTTP_400_BAD_REQUEST,
            code=ErrorCode.FILE_UPLOAD_INVALID,
            message="音频文件不能为空。",
            detail="音频文件不能为空。",
        )
    if len(content) > settings.ASR_MAX_UPLOAD_SIZE_BYTES:
        raise AppError(
            status_code=status.HTTP_400_BAD_REQUEST,
            code=ErrorCode.FILE_UPLOAD_INVALID,
            message="音频文件过大。",
            detail=f"音频文件大小不能超过 {settings.ASR_MAX_UPLOAD_SIZE_BYTES} 字节。",
        )

    text = await transcribe_audio_bytes(content, voice_format=voice_format)
    return ASRTranscriptionRead(text=text)
