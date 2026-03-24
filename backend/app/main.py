from __future__ import annotations

import logging
import uuid

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.api_v1 import api_router
from app.api.routes_ws_ai import router as ws_ai_router
from app.core.config import settings
from app.core.errors import AppError, ErrorCode, map_http_status_to_code
from app.services.health import build_liveness_payload, build_readiness_payload


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger("app.main")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)
app.include_router(ws_ai_router)


def _build_error_payload(
    *,
    request: Request,
    code: ErrorCode,
    message: str,
    detail: object | None,
) -> dict:
    return {
        "code": code.value,
        "message": message,
        "detail": detail,
        "request_id": getattr(request.state, "request_id", None),
    }


@app.middleware("http")
async def request_trace_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    request.state.request_id = request_id

    logger.info("request.start id=%s method=%s path=%s", request_id, request.method, request.url.path)
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    logger.info(
        "request.end id=%s method=%s path=%s status=%s",
        request_id,
        request.method,
        request.url.path,
        response.status_code,
    )
    return response


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    payload = _build_error_payload(
        request=request,
        code=exc.code,
        message=exc.message,
        detail=exc.detail if exc.detail is not None else exc.message,
    )
    return JSONResponse(status_code=exc.status_code, content=payload)


@app.exception_handler(HTTPException)
async def http_error_handler(request: Request, exc: HTTPException) -> JSONResponse:
    code = map_http_status_to_code(exc.status_code)
    detail = exc.detail
    message = detail if isinstance(detail, str) else "请求处理失败。"
    payload = _build_error_payload(request=request, code=code, message=message, detail=detail)
    return JSONResponse(status_code=exc.status_code, content=payload, headers=exc.headers)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    errors = exc.errors()
    for item in errors:
        ctx = item.get("ctx")
        if isinstance(ctx, dict) and isinstance(ctx.get("error"), Exception):
            ctx["error"] = str(ctx["error"])

    payload = _build_error_payload(
        request=request,
        code=ErrorCode.VALIDATION_ERROR,
        message="请求参数校验失败。",
        detail=jsonable_encoder(errors),
    )
    return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content=payload)


@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception(
        "request.unhandled id=%s method=%s path=%s",
        getattr(request.state, "request_id", None),
        request.method,
        request.url.path,
    )
    payload = _build_error_payload(
        request=request,
        code=ErrorCode.INTERNAL_ERROR,
        message="服务器内部错误。",
        detail="服务器内部错误。",
    )
    return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=payload)


@app.get("/", tags=["Root"])
def root() -> dict[str, str]:
    return {"message": "Legal case backend is running."}


@app.get(f"{settings.API_V1_STR}/health/live", tags=["Health"])
def health_live() -> dict:
    return build_liveness_payload()


@app.get(f"{settings.API_V1_STR}/health/ready", tags=["Health"])
def health_ready(request: Request):
    session_factory = getattr(request.app.state, "session_factory", None)
    payload, is_ready = build_readiness_payload(
        session_factory=session_factory if callable(session_factory) else None
    )
    if is_ready:
        return payload
    return JSONResponse(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content=payload)


@app.get(f"{settings.API_V1_STR}/health", tags=["Health"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}
