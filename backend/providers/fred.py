"""
FRED (Federal Reserve Economic Data) provider — 무료 API.
API 키 불필요한 공개 시리즈 전용.
주요 시리즈:
  WALCL  — 연준 총자산 (주간, 조 달러)
  DFF    — Fed Funds Rate
  T10Y2Y — 장단기 금리차 (10Y-2Y)
"""
import httpx
import logging
from datetime import datetime, timedelta
import data_registry as dr

log = logging.getLogger(__name__)

_BASE = "https://fred.stlouisfed.org/graph/fredgraph.csv"


async def get_series(series_id: str, periods: int = 5) -> list[dict]:
    """
    FRED CSV 엔드포인트에서 시리즈 최근 N개 반환.
    Returns: [{"date": "YYYY-MM-DD", "value": float}, ...]
    """
    try:
        start = (datetime.now() - timedelta(days=periods * 10)).strftime("%Y-%m-%d")
        url = f"{_BASE}?id={series_id}&vintage_date={start}"
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
        lines = resp.text.strip().split("\n")
        rows = []
        for line in lines[1:]:  # skip header
            parts = line.split(",")
            if len(parts) == 2:
                try:
                    rows.append({"date": parts[0], "value": float(parts[1])})
                except ValueError:
                    pass
        return rows[-periods:] if rows else []
    except Exception as e:
        log.warning(f"[FRED] {series_id} failed: {e}")
        return []


async def get_fed_total_assets() -> dict:
    """
    연준 총자산 (WALCL) — 조 달러.
    Returns: { value: float (조 달러), change_pct: float, date: str }
    """
    rows = await get_series("WALCL", periods=3)
    if not rows or len(rows) < 2:
        dr.record("fred_walcl", "FRED", True)
        return {"value": 7.0, "change_pct": 0.0, "date": "—", "source": "fallback"}

    latest  = rows[-1]
    prev    = rows[-2]
    value   = latest["value"] / 1e6   # 백만 달러 → 조 달러
    prev_v  = prev["value"] / 1e6
    chg_pct = (value - prev_v) / prev_v * 100 if prev_v else 0

    dr.record("fred_walcl", "FRED", False, f"${round(value,2)}T")
    return {
        "value":      round(value, 2),
        "change_pct": round(chg_pct, 2),
        "date":       latest["date"],
        "source":     "FRED WALCL",
    }


async def get_rate_spread_10y2y() -> dict:
    """
    장단기 금리차 T10Y2Y.
    Returns: { value: float (%), date: str }
    """
    rows = await get_series("T10Y2Y", periods=3)
    if not rows:
        dr.record("fred_t10y2y", "FRED", True)
        return {"value": None, "date": "—", "source": "fallback"}
    latest = rows[-1]
    dr.record("fred_t10y2y", "FRED", False, f"{latest['value']:.2f}%")
    return {
        "value":  latest["value"],
        "date":   latest["date"],
        "source": "FRED T10Y2Y",
    }


async def get_us10y() -> dict:
    """
    미국 10년물 국채 금리 (DGS10).
    Returns: { value: float (%) | None, date: str }
    """
    rows = await get_series("DGS10", periods=3)
    if not rows:
        dr.record("fred_dgs10", "FRED", True)
        return {"value": None, "date": "—", "source": "fallback"}
    latest = rows[-1]
    dr.record("fred_dgs10", "FRED", False, f"{latest['value']:.2f}%")
    return {
        "value":  latest["value"],
        "date":   latest["date"],
        "source": "FRED DGS10",
    }


async def get_dxy_broad() -> dict:
    """
    달러인덱스 광의 (DTWEXBGS — Trade Weighted US Dollar Index: Broad).
    ICE DXY (~100)와 다른 지수 — 표시 시 '달러지수(광의)' 레이블 사용.
    Returns: { value: float | None, date: str }
    """
    rows = await get_series("DTWEXBGS", periods=3)
    if not rows:
        dr.record("fred_dxy", "FRED", True)
        return {"value": None, "date": "—", "source": "fallback"}
    latest = rows[-1]
    dr.record("fred_dxy", "FRED", False, f"{latest['value']:.1f}")
    return {
        "value":  latest["value"],
        "date":   latest["date"],
        "source": "FRED DTWEXBGS",
    }
