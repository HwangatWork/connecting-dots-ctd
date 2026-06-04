"""
Yahoo Finance provider — yfinance wrapper.
모든 외부 호출은 여기서만. 실패 시 None 반환 (상위 계층에서 폴백 처리).
"""
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional
import logging

log = logging.getLogger(__name__)


def get_ticker_info(symbol: str) -> dict:
    """종목/지수 기본 정보 반환."""
    try:
        t = yf.Ticker(symbol)
        return t.info or {}
    except Exception as e:
        log.warning(f"[YF] info failed for {symbol}: {e}")
        return {}


def get_price_history(symbol: str, period: str = "6mo", interval: str = "1d") -> Optional[pd.DataFrame]:
    """OHLCV 히스토리 반환. 실패 시 None."""
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
    """여러 심볼 현재가 일괄 조회. {symbol: {price, change_pct, up}}"""
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
    """손익계산서, 재무지표 반환."""
    out = {"income": pd.DataFrame(), "info": {}}
    try:
        t = yf.Ticker(symbol)
        out["income"] = t.financials      # 연간
        out["quarterly"] = t.quarterly_financials
        out["info"] = t.info or {}
        out["balance"] = t.balance_sheet
        out["cashflow"] = t.cashflow
    except Exception as e:
        log.warning(f"[YF] financials failed for {symbol}: {e}")
    return out
