from fastapi import APIRouter

from app.api.routes_auth import router as auth_router
from app.api.routes_cases import router as cases_router
from app.api.routes_files import router as files_router
from app.api.routes_tenants import router as tenants_router
from app.api.routes_users import router as users_router


api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(cases_router)
api_router.include_router(files_router)
api_router.include_router(tenants_router)
api_router.include_router(users_router)
