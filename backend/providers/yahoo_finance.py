"""
Yahoo Finance provider — yfinance wrapper.
All external calls go through here. Returns None on failure (caller handles fallback).
"""
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional
import logging

log = logging.getLogger(__name__)


def get_ticker_info(symbol: str) -> dict:
    """Return basic ticker/index info."""
    try:
        t = yf.Ticker(symbol)
        return t.info or {}
    except Exception as e:
        log.warning(f"[YF] info failed for {symbol}: {e}")
        return {}


def get_price_history(symbol: str, period: str = "6mo", interval: str = "1d") -> Optional[pd.DataFrame]:
    """Return OHLCV history DataFrame. Returns None on failure."""
    try:
        df = yf.download(symbol, period=period, interval=interval,
                         progress=False, auto_adjust=True)
        if df.empty:
            return None
        return df
    except Exception as e:
        log.warning(f"[YF] history failed for {symbol}: {e}")
        return None


def get_current_prices(symbols: list[str]) -> dict[str, dict]:
    """Batch-fetch current prices. Returns {symbol: {price, change_pct, up}}."""
    result = {}
    try:
        tickers = yf.Tickers(" ".join(symbols))
        for sym in symbols:
            try:
                info = tickers.tickers[sym].fast_info
                prev = getattr(info, "previous_close", None)
                last = getattr(info, "last_price", None)
                if prev and last:
                    chg = (last - prev) / prev * 100
                    result[sym] = {
                        "price": last,
                        "change_pct": round(chg, 2),
                        "up": chg >= 0,
                    }
            except Exception:
                pass
    except Exception as e:
        log.warning(f"[YF] bulk price failed: {e}")
    return result


def get_financials(symbol: str) -> dict:
    """Return income statement and financial metrics."""
    out = {"income": pd.DataFrame(), "info": {}}
    try:
        t = yf.Ticker(symbol)
        out["income"] = t.financials      # annual
        out["quarterly"] = t.quarterly_financials
        out["info"] = t.info or {}
        out["balance"] = t.balance_sheet
        out["cashflow"] = t.cashflow
    except Exception as e:
        log.warning(f"[YF] financials failed for {symbol}: {e}")
    return out
