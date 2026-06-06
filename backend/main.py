"""
Connecting the Dots (CTD) — FastAPI backend entry point.
CI/CD: GitHub Actions auto-deploy enabled (2026-06-06)
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
from routers import market, stocks, ticker, status
from schemas import HealthResponse

FRONTEND_DIR = Path(__file__).parent.parent / "frontend"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

app = FastAPI(
    title="CTD API",
    description="Real-time investment decision system for Korean retail investors",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["*"],
)

# Register routers
PREFIX = settings.api_v1_prefix
app.include_router(ticker.router, prefix=PREFIX, tags=["ticker"])
app.include_router(market.router, prefix=PREFIX, tags=["market"])
app.include_router(stocks.router, prefix=PREFIX, tags=["stocks"])
app.include_router(status.router, prefix=PREFIX, tags=["status"])


# Health check
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


@app.get("/api/v1/debug/price", tags=["debug"])
async def debug_price():
    """DIAGNOSTIC ONLY — compare fast_info vs download vs info for ^GSPC. Remove after diagnosis."""
    import yfinance as yf
    results: dict = {}

    # Method 1: fast_info (current production path)
    try:
        t = yf.Ticker("^GSPC")
        fi = t.fast_info
        results["fast_info"] = {
            "last_price":      getattr(fi, "last_price", None),
            "previous_close":  getattr(fi, "previous_close", None),
            "last_volume":     getattr(fi, "last_volume", None),
        }
    except Exception as e:
        results["fast_info"] = {"error": str(e)}

    # Method 2: yf.download — 5-day window to ensure we get at least one trading day
    try:
        import pandas as pd
        df = yf.download("^GSPC", period="5d", interval="1d", progress=False, auto_adjust=True)
        if not df.empty:
            close_series = df["Close"].squeeze()
            results["download_5d"] = {
                "latest_close": float(close_series.iloc[-1]),
                "latest_date":  str(df.index[-1].date()),
                "rows":         len(df),
            }
        else:
            results["download_5d"] = {"error": "empty dataframe"}
    except Exception as e:
        results["download_5d"] = {"error": str(e)}

    # Method 3: t.info (heavy endpoint — checks regularMarketPrice)
    try:
        t2 = yf.Ticker("^GSPC")
        info = t2.info
        results["info_api"] = {
            "regularMarketPrice": info.get("regularMarketPrice"),
            "previousClose":      info.get("previousClose"),
            "currentPrice":       info.get("currentPrice"),
        }
    except Exception as e:
        results["info_api"] = {"error": str(e)}

    return results


# Serve frontend static files — registered after API routes so /api/* takes priority
@app.get("/", include_in_schema=False)
async def serve_index():
    return FileResponse(FRONTEND_DIR / "index.html")

if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
