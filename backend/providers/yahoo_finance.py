"""
Yahoo Finance provider — yfinance wrapper.
All external calls go through here. Returns None on failure (caller handles fallback).
429 handling: 0.5s delay between requests + 3 retries with exponential backoff.
"""
import time
import yfinance as yf
import pandas as pd
from typing import Optional
import logging
import data_registry as dr

log = logging.getLogger(__name__)

_DELAY = 0.5       # seconds between requests
_MAX_RETRIES = 3


def _retry(fn, *args, **kwargs):
    """Call fn(*args, **kwargs) up to _MAX_RETRIES times on exception."""
    last_exc = None
    for attempt in range(_MAX_RETRIES):
        try:
            result = fn(*args, **kwargs)
            return result
        except Exception as e:
            last_exc = e
            is_429 = "429" in str(e) or "Too Many" in str(e)
            wait = _DELAY * (2 ** attempt) if is_429 else _DELAY
            log.warning(f"[YF] attempt {attempt+1}/{_MAX_RETRIES} failed ({e}), waiting {wait:.1f}s")
            time.sleep(wait)
    raise last_exc


def get_ticker_info(symbol: str) -> dict:
    """Return basic ticker/index info."""
    try:
        t = yf.Ticker(symbol)
        result = _retry(lambda: t.info)
        r = result or {}
        dr.record(f"info_{symbol}", "Yahoo Finance", not bool(r))
        return r
    except Exception as e:
        log.warning(f"[YF] info failed for {symbol}: {e}")
        dr.record(f"info_{symbol}", "Yahoo Finance", True)
        return {}


def get_price_history(symbol: str, period: str = "6mo", interval: str = "1d") -> Optional[pd.DataFrame]:
    """Return OHLCV history DataFrame. Returns None on failure."""
    try:
        df = _retry(
            yf.download,
            symbol,
            period=period,
            interval=interval,
            progress=False,
            auto_adjust=True,
        )
        if df is None or df.empty:
            dr.record(f"hist_{symbol}", "Yahoo Finance", True)
            return None
        time.sleep(_DELAY)
        dr.record(f"hist_{symbol}", "Yahoo Finance", False, f"{len(df)} rows")
        return df
    except Exception as e:
        log.warning(f"[YF] history failed for {symbol}: {e}")
        dr.record(f"hist_{symbol}", "Yahoo Finance", True)
        return None


def get_current_prices(symbols: list[str]) -> dict[str, dict]:
    """Batch-fetch current prices. Returns {symbol: {price, change_pct, up}}."""
    result = {}
    for sym in symbols:
        try:
            def _fetch(s=sym):
                t = yf.Ticker(s)
                info = t.fast_info
                prev = getattr(info, "previous_close", None)
                last = getattr(info, "last_price", None)
                return prev, last

            prev, last = _retry(_fetch)
            if prev and last:
                chg = (last - prev) / prev * 100
                result[sym] = {
                    "price": last,
                    "change_pct": round(chg, 2),
                    "up": chg >= 0,
                }
                dr.record(f"yf_{sym}", "Yahoo Finance", False, f"{last:.4g}")
            else:
                dr.record(f"yf_{sym}", "Yahoo Finance", True)
            time.sleep(_DELAY)
        except Exception as e:
            log.warning(f"[YF] price failed for {sym}: {e}")
            dr.record(f"yf_{sym}", "Yahoo Finance", True)
    return result


def get_financials(symbol: str) -> dict:
    """Return income statement and financial metrics."""
    out = {"income": pd.DataFrame(), "info": {}}
    try:
        t = yf.Ticker(symbol)
        out["income"]    = _retry(lambda: t.financials)
        time.sleep(_DELAY)
        out["quarterly"] = _retry(lambda: t.quarterly_financials)
        time.sleep(_DELAY)
        out["info"]      = _retry(lambda: t.info) or {}
        out["balance"]   = t.balance_sheet
        out["cashflow"]  = t.cashflow
    except Exception as e:
        log.warning(f"[YF] financials failed for {symbol}: {e}")
    return out
