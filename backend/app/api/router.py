from fastapi import APIRouter
from app.api.routes.profiles import router as profiles_router
from app.api.routes.collections import router as collections_router
from app.api.routes.analytics import router as analytics_router
from app.api.routes.export import router as export_router
from app.api.routes.ai_insights import router as ai_insights_router

api_router = APIRouter()
api_router.include_router(profiles_router)
api_router.include_router(collections_router)
api_router.include_router(analytics_router)
api_router.include_router(export_router)
api_router.include_router(ai_insights_router)
