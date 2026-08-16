from fastapi import APIRouter

from api.v1.auth import router as auth_router
from api.v1.blockchain import router as blockchain_router
from api.v1.players import router as players_router


api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(blockchain_router)
api_router.include_router(players_router)