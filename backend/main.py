"""
커넥팅닷 (CTD) — FastAPI 백엔드 진입점.
"""
import logging
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

fromconfig import settings
fromcache import cache
fromrouters import market, stocks, ticker
fromschemas import HealthResponse

FRONTEND_DIR = Path(__file__).parent.parent / "frontend"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

app = FastAPI(
    title="커넥팅닷 CTD API",
    description="한국 개인 투자자용 실시간 투자 판단 시스템",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["*"],
)

# ── 라우터 등록 ────────────────────────────────────────────────
PREFIX = settings.api_v1_prefix
app.include_router(ticker.router, prefix=PREFIX, tags=["ticker"])
app.include_router(market.router, prefix=PREFIX, tags=["market"])
app.include_router(stocks.router, prefix=PREFIX, tags=["stocks"])


# ── 헬스 체크 ──────────────────────────────────────────────────
@app.get("/api/v1/health", response_model=HealthResponse, tags=["system"])
async def health():
    return HealthResponse(
        status="ok",
        timestamp=datetime.now(timezone.utc).isoformat(),
        cache_stats=cache.stats(),
    )


@app.delete("/api/v1/cache", tags=["system"])
async def clear_cache():
    cache.clear()
    return {"cleared": True}


# ── 프론트엔드 정적 파일 서빙 ──────────────────────────────────
# API 라우트 이후에 등록해야 /api/* 가 우선 처리됨
@app.get("/", include_in_schema=False)
async def serve_index():
    return FileResponse(FRONTEND_DIR / "index.html")

if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
