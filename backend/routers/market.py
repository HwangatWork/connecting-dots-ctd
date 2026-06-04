from fastapi import APIRouter
from services.market_service import build_market_response
from config import CACHE_TTL
from cache import cache
from schemas import MarketResponse

router = APIRouter()


@router.get("/market", response_model=MarketResponse)
async def get_market():
    cached = cache.get("market")
    if cached:
        return cached

    result = await build_market_response()
    cache.set("market", result, CACHE_TTL["market"])
    return result
