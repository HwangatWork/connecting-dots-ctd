from fastapi import APIRouter
from datetime import datetime, timezone

from providers import fdr as fdr_p
from config import CACHE_TTL
from cache import cache
from schemas import TickerResponse, TickerItem

router = APIRouter()


@router.get("/ticker", response_model=TickerResponse)
async def get_ticker():
    cached = cache.get("ticker")
    if cached:
        return cached

    items: list[TickerItem] = []

    # ── 1. 글로벌 지수 + 원자재 (FDR) ────────────────────────────
    # 야후 심볼 키 사용 — fdr.py 내부에서 FDR 심볼로 변환
    yf_symbols = {
        "S&P 500": "^GSPC",
        "NASDAQ":  "^IXIC",
        "DOW":     "^DJI",
        "닛케이":  "^N225",
        "VIX":     "^VIX",
        "WTI":     "CL=F",
        "금":      "GC=F",
    }
    prices = fdr_p.get_current_prices(list(yf_symbols.values()))

    for label, sym in yf_symbols.items():
        d = prices.get(sym, {})
        p = d.get("price")
        c = d.get("change_pct", 0)
        if p:
            val = f"{p:,.0f}" if p > 100 else f"{p:.2f}"
            items.append(TickerItem(label=label, value=val, change=f"{c:+.2f}%", up=d.get("up", True)))

    # ── 2. USD/KRW (FDR) ─────────────────────────────────────────
    fx = fdr_p.get_current_prices(["KRW=X"])
    fx_v = fx.get("KRW=X", {})
    if fx_v.get("price"):
        items.append(TickerItem(
            label="USD/KRW",
            value=f"{fx_v['price']:,.0f}",
            change=f"{fx_v.get('change_pct', 0):+.2f}%",
            up=fx_v.get("up", True),
        ))

    # ── 3. KOSPI / KOSDAQ (FDR — KRX 심볼 직접 사용) ─────────────
    krx = fdr_p.get_current_prices(["KS11", "KQ11"])
    for label, sym in [("코스피", "KS11"), ("코스닥", "KQ11")]:
        d = krx.get(sym, {})
        if d.get("price"):
            items.append(TickerItem(
                label=label,
                value=f"{d['price']:,.0f}",
                change=f"{d.get('change_pct', 0):+.2f}%",
                up=d.get("up", True),
            ))

    if not items:
        items = [TickerItem(label="S&P 500", value="—", change="—", up=True)]

    result = TickerResponse(items=items, updated_at=datetime.now(timezone.utc).isoformat())
    cache.set("ticker", result, CACHE_TTL["ticker"])
    return result
