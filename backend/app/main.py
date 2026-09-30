import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import FileResponse
from starlette.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import settings
from app.api import api_router
from app.scheduler import start_scheduler, shutdown_scheduler
from app.paths import app_paths


class SPAStaticFiles(StaticFiles):
    """StaticFiles handler with fallback to index.html for Single Page Application routes."""
    async def get_response(self, path: str, scope):
        try:
            return await super().get_response(path, scope)
        except (StarletteHTTPException, Exception) as ex:
            if getattr(ex, "status_code", 500) == 404:
                return await super().get_response("index.html", scope)
            raise ex


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler()
    yield
    shutdown_scheduler()


app = FastAPI(
    title="SocialScope API",
    description="Social Media Intelligence and Growth Analytics Platform Backend",
    version="0.1.0",
    lifespan=lifespan
)

# API routes
app.include_router(api_router, prefix="/api")


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": "socialscope-backend"
    }


# Mount compiled React SPA frontend if static bundle exists
frontend_dist = app_paths.get_frontend_dist_dir()
if frontend_dist.exists():
    app.mount("/", SPAStaticFiles(directory=str(frontend_dist), html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.backend_host, port=settings.backend_port, reload=True)

