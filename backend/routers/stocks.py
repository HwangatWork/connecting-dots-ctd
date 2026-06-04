from fastapi import APIRouter, HTTPException, Query
from services.stock_service import get_stocks_list, get_stock_detail
from config import CACHE_TTL, ALL_STOCKS
from cache import cache
from schemas import StocksResponse, StockDetailResponse
from datetime import datetime, timezone

router = APIRouter()


@router.get("/stocks", response_model=StocksResponse)
async def list_stocks(group: str = Query(default="domestic", pattern="^(domestic|overseas)$")):
    cache_key = f"stocks_{group}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    items = await get_stocks_list(group)
    result = StocksResponse(group=group, items=items, updated_at=datetime.now(timezone.utc).isoformat())
    cache.set(cache_key, result, CACHE_TTL["stocks"])
    return result


@router.get("/stocks/{code}", response_model=StockDetailResponse)
async def stock_detail(code: str):
    if code not in ALL_STOCKS:
        raise HTTPException(status_code=404, detail=f"Stock '{code}' not found")

    cache_key = f"stock_{code}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    result = await get_stock_detail(code)
    cache.set(cache_key, result, CACHE_TTL["stock"])
    return result
