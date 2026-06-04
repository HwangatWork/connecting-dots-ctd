from fastapi import APIRouter
from datetime import datetime, timezone

from providers import yahoo_finance as yf_p
from providers import krx as krx_p
from config import INDEX_SYMBOLS, CACHE_TTL
from cache import cache
from schemas import TickerResponse, TickerItem

router = APIRouter()


@router.get("/ticker", response_model=TickerResponse)
async def get_ticker():
    cached = cache.get("ticker")
    if cached:
        return cached

    symbols = {
        "S&P":   INDEX_SYMBOLS["sp500"],
        "NASDAQ": INDEX_SYMBOLS["nasdaq"],
        "VIX":   INDEX_SYMBOLS["vix"],
        "WTI":   INDEX_SYMBOLS["wti"],
        "Gold":  "GC=F",
    }

    prices = yf_p.get_current_prices(list(symbols.values()))
    krx_data = krx_p.get_market_indices()

    items = []

    # USD/KRW
    fx = yf_p.get_current_prices(["KRW=X"])
    fx_v = fx.get("KRW=X", {})
    items.append(TickerItem(label="USD/KRW", value=f"{fx_v.get('price',1380):,.0f}", change=f"{fx_v.get('change_pct',0):+.2f}%", up=fx_v.get("up", True)))

    # Yahoo Finance indices
    for label, sym in symbols.items():
        d = prices.get(sym, {})
        p = d.get("price")
        c = d.get("change_pct", 0)
        if p:
            val = f"{p:,.0f}" if p > 100 else f"{p:.1f}"
            items.append(TickerItem(label=label, value=val, change=f"{c:+.2f}%", up=d.get("up", True)))

    # KOSPI / KOSDAQ
    for label, key in [("KOSPI", "kospi"), ("KOSDAQ", "kosdaq")]:
        d = krx_data.get(key, {})
        if d:
            items.append(TickerItem(label=label, value=f"{d['value']:,.0f}", change=f"{d['change_pct']:+.2f}%", up=d["up"]))

    result = TickerResponse(items=items, updated_at=datetime.now(timezone.utc).isoformat())
    cache.set("ticker", result, CACHE_TTL["ticker"])
    return result
