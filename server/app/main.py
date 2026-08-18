from fastapi import FastAPI

from api import api_router
from app.middleware import CorrelationIdMiddleware
from domain.genesis.service import get_genesis_service
from shared.database import database_is_configured
from shared.logging import configure_logging, get_logger
from shared.settings import settings


configure_logging()
logger = get_logger("gmn.api")


app = FastAPI(
    title="Global Mining Network API",
    version="0.1.0",
)

app.add_middleware(CorrelationIdMiddleware)
app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "api",
        "environment": settings.environment,
        "database_configured": str(database_is_configured()).lower(),
    }


@app.on_event("startup")
def on_startup() -> None:
    runtime = get_genesis_service().initialize_runtime()
    logger.info(f"api_started genesis_status={runtime['status']}")