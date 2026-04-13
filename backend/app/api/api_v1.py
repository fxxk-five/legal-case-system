from fastapi import APIRouter

from app.api.routes_auth import router as auth_router
from app.api.routes_tenants import router as tenants_router
from app.api.routes_users import router as users_router
from app.modules.ai.router import router as ai_router
from app.modules.analytics.router import router as analytics_router
from app.modules.analytics.stats_router import router as stats_router
from app.modules.asr.router import router as asr_router
from app.modules.notifications.router import router as notifications_router
from app.modules.cases.router import router as cases_router
from app.modules.clients.router import router as clients_router
from app.modules.files.router import router as files_router


api_router = APIRouter()
api_router.include_router(asr_router)
api_router.include_router(ai_router)
api_router.include_router(analytics_router)
api_router.include_router(auth_router)
api_router.include_router(cases_router)
api_router.include_router(clients_router)
api_router.include_router(files_router)
api_router.include_router(notifications_router)
api_router.include_router(stats_router)
api_router.include_router(tenants_router)
api_router.include_router(users_router)
