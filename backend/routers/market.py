from fastapi import APIRouter
from backend.services.market_service import build_market_response
from backend.config import CACHE_TTL
from backend.cache import cache
from backend.schemas import MarketResponse

router = APIRouter()


@router.get("/market", response_model=MarketResponse)
async def get_market():
    cached = cache.get("market")
    if cached:
        return cached

    result = await build_market_response()
    cache.set("market", result, CACHE_TTL["market"])
    return result
