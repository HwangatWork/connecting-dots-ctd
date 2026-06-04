from fastapi import APIRouter
fromservices.market_service import build_market_response
fromconfig import CACHE_TTL
fromcache import cache
fromschemas import MarketResponse

router = APIRouter()


@router.get("/market", response_model=MarketResponse)
async def get_market():
    cached = cache.get("market")
    if cached:
        return cached

    result = await build_market_response()
    cache.set("market", result, CACHE_TTL["market"])
    return result
