from fastapi import APIRouter

from api.v1.analytics import router as analytics_router
from api.v1.admin import router as admin_router
from api.v1.anticheat import router as anticheat_router
from api.v1.auth import router as auth_router
from api.v1.blockchain import router as blockchain_router
from api.v1.docs import router as docs_router
from api.v1.economy import router as economy_router
from api.v1.events import router as events_router
from api.v1.explorer import router as explorer_router
from api.v1.leaderboards import router as leaderboards_router
from api.v1.market import router as market_router
from api.v1.marketplace import router as marketplace_router
from api.v1.moderation import router as moderation_router
from api.v1.monitoring import router as monitoring_router
from api.v1.players import router as players_router
from api.v1.pools import router as pools_router
from api.v1.stream import router as stream_router
from api.v1.support import router as support_router
from api.v1.upgrades import router as upgrades_router
from api.v1.telemetry import router as telemetry_router


api_router = APIRouter()
api_router.include_router(analytics_router)
api_router.include_router(admin_router)
api_router.include_router(anticheat_router)
api_router.include_router(auth_router)
api_router.include_router(blockchain_router)
api_router.include_router(docs_router)
api_router.include_router(economy_router)
api_router.include_router(events_router)
api_router.include_router(explorer_router)
api_router.include_router(leaderboards_router)
api_router.include_router(market_router)
api_router.include_router(marketplace_router)
api_router.include_router(moderation_router)
api_router.include_router(monitoring_router)
api_router.include_router(players_router)
api_router.include_router(pools_router)
api_router.include_router(stream_router)
api_router.include_router(support_router)
api_router.include_router(upgrades_router)
api_router.include_router(telemetry_router)
