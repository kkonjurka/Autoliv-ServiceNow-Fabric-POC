import os
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from app.database import init_database
from app.routes.attachments import router as attachments_router
from app.routes.health import router as health_router
from app.routes.incidents import router as incidents_router
from app.routes.kb_articles import router as kb_articles_router


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_database()
    yield


def create_app() -> FastAPI:
    application = FastAPI(
        title="Autoliv Mock ServiceNow API",
        description="SQLite-backed FastAPI service that simulates ServiceNow incidents, knowledge, and related assets.",
        version="1.0.0",
        lifespan=lifespan,
    )
    application.include_router(health_router)
    application.include_router(incidents_router)
    application.include_router(kb_articles_router)
    application.include_router(attachments_router)
    return application


app = create_app()


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=os.getenv("SERVICENOW_API_HOST", "0.0.0.0"),
        port=int(os.getenv("SERVICENOW_API_PORT", "8000")),
        reload=False,
    )
