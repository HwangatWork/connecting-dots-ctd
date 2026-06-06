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

    items: list[TickerItem] = []

    # ── 1. 야후 파이낸스 지수 (S&P, NASDAQ, VIX, WTI, 금) ──────────
    yf_symbols = {
        "S&P 500": INDEX_SYMBOLS["sp500"],
        "NASDAQ":  INDEX_SYMBOLS["nasdaq"],
        "DOW":     INDEX_SYMBOLS["dow"],
        "닛케이":  INDEX_SYMBOLS["nikkei"],
        "VIX":     INDEX_SYMBOLS["vix"],
        "WTI":     INDEX_SYMBOLS["wti"],
        "금":      "GC=F",
        "SKEW":    INDEX_SYMBOLS["skew"],
        "DXY":     INDEX_SYMBOLS["dxy"],
    }
    prices = yf_p.get_current_prices(list(yf_symbols.values()))

    for label, sym in yf_symbols.items():
        d = prices.get(sym, {})
        p = d.get("price")
        c = d.get("change_pct", 0)
        if p:
            val = f"{p:,.0f}" if p > 100 else f"{p:.2f}"
            items.append(TickerItem(label=label, value=val, change=f"{c:+.2f}%", up=d.get("up", True)))

    # ── 2. USD/KRW ──────────────────────────────────────────────────
    fx = yf_p.get_current_prices(["KRW=X"])
    fx_v = fx.get("KRW=X", {})
    if fx_v.get("price"):
        items.append(TickerItem(
            label="USD/KRW",
            value=f"{fx_v['price']:,.0f}",
            change=f"{fx_v.get('change_pct', 0):+.2f}%",
            up=fx_v.get("up", True),
        ))

    # ── 3. KRX 지수 (코스피, 코스닥) ────────────────────────────────
    krx_data = krx_p.get_market_indices()
    for label, key in [("코스피", "kospi"), ("코스닥", "kosdaq")]:
        d = krx_data.get(key) or {}
        if d.get("value"):
            items.append(TickerItem(
                label=label,
                value=f"{d['value']:,.0f}",
                change=f"{d.get('change_pct', 0):+.2f}%",
                up=d.get("up", True),
            ))

    # 데이터가 없으면 최소 placeholder 유지
    if not items:
        items = [TickerItem(label="S&P 500", value="—", change="—", up=True)]

    result = TickerResponse(items=items, updated_at=datetime.now(timezone.utc).isoformat())
    cache.set("ticker", result, CACHE_TTL["ticker"])
    return result
