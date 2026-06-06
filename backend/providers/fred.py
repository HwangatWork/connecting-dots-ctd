"""
FRED (Federal Reserve Economic Data) provider — 공식 API 키 방식.
엔드포인트: api.stlouisfed.org/fred/series/observations
환경변수: FRED_API_KEY (config.Settings.fred_api_key)

주요 시리즈:
  DGS10    — 미국 10년물 국채 금리 (일간, %)
  DTWEXBGS — 달러인덱스 광의 (주간)
  T10Y2Y   — 장단기 금리차 10Y-2Y (일간, %)
  WALCL    — 연준 총자산 (주간, 백만 달러)
"""
import httpx
import logging
from datetime import datetime, timedelta
import data_registry as dr

log = logging.getLogger(__name__)

_API_BASE = "https://api.stlouisfed.org/fred/series/observations"


def _get_api_key() -> str:
    import os
    return os.getenv("FRED_API_KEY", "")


async def get_series(series_id: str, periods: int = 5) -> list[dict]:
    """
    FRED 공식 API에서 시리즈 최근 N개 유효값 반환.
    Returns: [{"date": "YYYY-MM-DD", "value": float}, ...]
    "." 값(결측치)은 자동 제외.
    """
    api_key = _get_api_key()
    if not api_key:
        log.warning("[FRED] FRED_API_KEY not set - register env var")
        return []

    try:
        params = {
            "series_id":   series_id,
            "api_key":     api_key,
            "file_type":   "json",
            "sort_order":  "desc",
            "limit":       20,  # 충분히 가져온 후 유효값 N개 추출
        }
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(_API_BASE, params=params)
            resp.raise_for_status()

        data = resp.json()
        observations = data.get("observations", [])

        rows = []
        for obs in observations:
            if obs.get("value", ".") == ".":
                continue
            try:
                rows.append({"date": obs["date"], "value": float(obs["value"])})
            except (ValueError, KeyError):
                continue

        # desc 정렬로 받았으므로 최신이 앞 → 뒤집어서 오름차순, 마지막 N개 반환
        rows.reverse()
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
        return {"value": None, "change_pct": 0.0, "date": "—", "source": "fallback"}

    latest = rows[-1]
    prev   = rows[-2]
    value  = latest["value"] / 1e6   # 백만 달러 → 조 달러
    prev_v = prev["value"] / 1e6
    chg    = (value - prev_v) / prev_v * 100 if prev_v else 0

    dr.record("fred_walcl", "FRED", False, f"${round(value, 2)}T")
    return {
        "value":      round(value, 2),
        "change_pct": round(chg, 2),
        "date":       latest["date"],
        "source":     "FRED WALCL",
    }


async def get_rate_spread_10y2y() -> dict:
    """
    장단기 금리차 T10Y2Y (10Y-2Y, %).
    Returns: { value: float | None, date: str }
    """
    rows = await get_series("T10Y2Y", periods=3)
    if not rows:
        dr.record("fred_t10y2y", "FRED", True)
        return {"value": None, "date": "—", "source": "fallback"}
    latest = rows[-1]
    dr.record("fred_t10y2y", "FRED", False, f"{latest['value']:+.2f}%")
    return {"value": latest["value"], "date": latest["date"], "source": "FRED T10Y2Y"}


async def get_us10y() -> dict:
    """
    미국 10년물 국채 금리 (DGS10, %).
    Returns: { value: float | None, date: str }
    """
    rows = await get_series("DGS10", periods=3)
    if not rows:
        dr.record("fred_dgs10", "FRED", True)
        return {"value": None, "date": "—", "source": "fallback"}
    latest = rows[-1]
    dr.record("fred_dgs10", "FRED", False, f"{latest['value']:.2f}%")
    return {"value": latest["value"], "date": latest["date"], "source": "FRED DGS10"}


async def get_dxy_broad() -> dict:
    """
    달러인덱스 광의 (DTWEXBGS — Trade Weighted US Dollar Index: Broad).
    Returns: { value: float | None, date: str }
    """
    rows = await get_series("DTWEXBGS", periods=3)
    if not rows:
        dr.record("fred_dxy", "FRED", True)
        return {"value": None, "date": "—", "source": "fallback"}
    latest = rows[-1]
    dr.record("fred_dxy", "FRED", False, f"{latest['value']:.1f}")
    return {"value": latest["value"], "date": latest["date"], "source": "FRED DTWEXBGS"}
