"""
커넥?�닷 (CTD) ??FastAPI 백엔??진입??
"""
import logging
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from config import settings
from cache import cache
from routers import market, stocks, ticker
from schemas import HealthResponse

FRONTEND_DIR = Path(__file__).parent.parent / "frontend"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

app = FastAPI(
    title="커넥?�닷 CTD API",
    description="?�국 개인 ?�자?�용 ?�시�??�자 ?�단 ?�스??,
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["*"],
)

# ?�?� ?�우???�록 ?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�
PREFIX = settings.api_v1_prefix
app.include_router(ticker.router, prefix=PREFIX, tags=["ticker"])
app.include_router(market.router, prefix=PREFIX, tags=["market"])
app.include_router(stocks.router, prefix=PREFIX, tags=["stocks"])


# ?�?� ?�스 체크 ?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�
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


# ?�?� ?�론?�엔???�적 ?�일 ?�빙 ?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�
# API ?�우???�후???�록?�야 /api/* 가 ?�선 처리??@app.get("/", include_in_schema=False)
async def serve_index():
    return FileResponse(FRONTEND_DIR / "index.html")

if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
