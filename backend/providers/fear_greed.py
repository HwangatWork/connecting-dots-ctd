"""
CNN Fear & Greed Index — 미국 주식시장 기반 7개 하위 지표 종합.
https://production.dataviz.cnn.io/index/fearandgreed/graphdata/
키 불필요, 리다이렉트 있음(follow_redirects=True 필요).
"""
import httpx
import logging
from data_registry import record

log = logging.getLogger(__name__)

_API_URL = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata/"
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
    "Referer": "https://www.cnn.com/",
}


async def get_fear_greed() -> dict:
    """
    Returns:
        { value: int, label: str, previous: int, change: int }
    """
    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            resp = await client.get(_API_URL, headers=_HEADERS)
            resp.raise_for_status()
            fg = resp.json()["fear_and_greed"]

        current = round(float(fg["score"]))
        previous = round(float(fg.get("previous_close", current)))
        label = fg.get("rating", "Neutral").title()

        record("fg_index", "CNN", False, current)
        return {
            "value": current,
            "label": label,
            "previous": previous,
            "change": current - previous,
        }
    except Exception as e:
        log.warning(f"[FG] CNN fear_greed fetch failed: {e}")
        record("fg_index", "CNN", True)
        return {"value": 50, "label": "Neutral", "previous": 50, "change": 0}
