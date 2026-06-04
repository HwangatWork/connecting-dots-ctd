from pydantic_settings import BaseSettings
from typing import Final

class Settings(BaseSettings):
    api_v1_prefix: str = "/api/v1"
    cors_origins: list[str] = ["*"]

    class Config:
        env_file = ".env"

settings = Settings()

# ── 종목 마스터 ────────────────────────────────────────────────
DOMESTIC_STOCKS: Final[list[dict]] = [
    {"code": "000660", "name": "SK하이닉스",      "yahoo": "000660.KS"},
    {"code": "005930", "name": "삼성전자",        "yahoo": "005930.KS"},
    {"code": "011070", "name": "LG이노텍",        "yahoo": "011070.KS"},
    {"code": "012450", "name": "한화에어로스페이스","yahoo": "012450.KS"},
    {"code": "009150", "name": "삼성전기",        "yahoo": "009150.KS"},
]

OVERSEAS_STOCKS: Final[list[dict]] = [
    {"code": "NVDA",  "name": "NVIDIA",    "yahoo": "NVDA"},
    {"code": "TSM",   "name": "TSMC",      "yahoo": "TSM"},
    {"code": "MSFT",  "name": "Microsoft", "yahoo": "MSFT"},
    {"code": "GOOGL", "name": "Alphabet",  "yahoo": "GOOGL"},
    {"code": "META",  "name": "Meta",      "yahoo": "META"},
]

ALL_STOCKS: Final[dict] = {
    **{s["code"]: {**s, "group": "domestic"} for s in DOMESTIC_STOCKS},
    **{s["code"]: {**s, "group": "overseas"} for s in OVERSEAS_STOCKS},
}

# ── 시장 지수 야후 심볼 ──────────────────────────────────────
INDEX_SYMBOLS: Final[dict] = {
    "sp500":   "^GSPC",
    "nasdaq":  "^IXIC",
    "dow":     "^DJI",
    "nikkei":  "^N225",
    "vix":     "^VIX",
    "dxy":     "DX-Y.NYB",
    "wti":     "CL=F",
    "tnx":     "^TNX",    # 미국 10년물
    "tyx":     "^TYX",    # 미국 30년물
    "ust2y":   "^IRX",    # 미국 2년물 (13주)
}

# ── 시장 온도 계산 가중치 ──────────────────────────────────────
TEMPERATURE_WEIGHTS: Final[dict] = {
    "fear_greed":      0.20,
    "vix_score":       0.20,
    "sp_momentum":     0.20,
    "hy_spread":       0.15,
    "rate_spread":     0.15,
    "kospi_momentum":  0.10,
}

# ── IQ 스코어 8축 이름 ─────────────────────────────────────────
RADAR_AXES: Final[list[str]] = [
    "비즈니스 품질",
    "성장 모멘텀",
    "밸류에이션",
    "시장 타이밍",
    "재무 건전성",
    "매크로 연계",
    "리스크 관리",
    "세후 수익률",
]

# ── 캐시 TTL (초) ─────────────────────────────────────────────
CACHE_TTL: Final[dict] = {
    "ticker":  60,
    "market":  300,
    "stocks":  900,
    "stock":   900,
}
