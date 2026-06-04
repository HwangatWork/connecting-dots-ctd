"""
CNN Fear & Greed Index — Alternative.me 무료 API.
https://api.alternative.me/fng/
키 불필요, 무료, rate limit 없음.
"""
import httpx
import logging
from datetime import datetime

log = logging.getLogger(__name__)

_API_URL = "https://api.alternative.me/fng/?limit=2&format=json"


async def get_fear_greed() -> dict:
    """
    Returns:
        { value: int, label: str, previous: int, change: int }
    """
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(_API_URL)
            resp.raise_for_status()
            data = resp.json()["data"]

        current = int(data[0]["value"])
        previous = int(data[1]["value"]) if len(data) > 1 else current
        label = data[0]["value_classification"]

        return {
            "value": current,
            "label": label,
            "previous": previous,
            "change": current - previous,
        }
    except Exception as e:
        log.warning(f"[FG] fear_greed fetch failed: {e}")
        return {"value": 50, "label": "Neutral", "previous": 50, "change": 0}
