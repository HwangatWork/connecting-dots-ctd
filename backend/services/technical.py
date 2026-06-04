"""
Technical indicator calculations.
Input: yfinance OHLCV DataFrame
Output: dict of indicator values
"""
import pandas as pd
import numpy as np
from typing import Optional
import logging

log = logging.getLogger(__name__)


def calc_rsi(df: pd.DataFrame, period: int = 14) -> Optional[float]:
    try:
        close = df["Close"].squeeze()
        delta = close.diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
        avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return round(float(rsi.iloc[-1]), 1)
    except Exception as e:
        log.warning(f"RSI calc failed: {e}")
        return None


def calc_stoch_rsi(df: pd.DataFrame, rsi_period: int = 14, stoch_period: int = 14) -> Optional[float]:
    try:
        close = df["Close"].squeeze()
        delta = close.diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.ewm(com=rsi_period - 1, min_periods=rsi_period).mean()
        avg_loss = loss.ewm(com=rsi_period - 1, min_periods=rsi_period).mean()
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        rsi_min = rsi.rolling(stoch_period).min()
        rsi_max = rsi.rolling(stoch_period).max()
        stoch = (rsi - rsi_min) / (rsi_max - rsi_min) * 100
        return round(float(stoch.iloc[-1]), 1)
    except Exception as e:
        log.warning(f"Stoch RSI calc failed: {e}")
        return None


def calc_ma(df: pd.DataFrame, period: int) -> Optional[float]:
    try:
        close = df["Close"].squeeze()
        ma = close.rolling(period).mean()
        return round(float(ma.iloc[-1]), 2)
    except Exception as e:
        log.warning(f"MA{period} calc failed: {e}")
        return None


def calc_bollinger(df: pd.DataFrame, period: int = 20, std: float = 2.0) -> Optional[dict]:
    try:
        close = df["Close"].squeeze()
        mid = close.rolling(period).mean()
        std_dev = close.rolling(period).std()
        upper = mid + std * std_dev
        lower = mid - std * std_dev
        current = float(close.iloc[-1])
        pct_b = float((current - lower.iloc[-1]) / (upper.iloc[-1] - lower.iloc[-1]))
        return {
            "upper": round(float(upper.iloc[-1]), 2),
            "mid": round(float(mid.iloc[-1]), 2),
            "lower": round(float(lower.iloc[-1]), 2),
            "pct_b": round(pct_b, 3),
            "current": round(current, 2),
        }
    except Exception as e:
        log.warning(f"Bollinger calc failed: {e}")
        return None


def calc_momentum(df: pd.DataFrame, days: int = 21) -> Optional[float]:
    """1-month momentum (%)."""
    try:
        close = df["Close"].squeeze()
        if len(close) < days + 1:
            return None
        return round((float(close.iloc[-1]) / float(close.iloc[-days - 1]) - 1) * 100, 2)
    except Exception as e:
        log.warning(f"Momentum calc failed: {e}")
        return None


def calc_all(df: pd.DataFrame) -> dict:
    """Calculate all technical indicators at once."""
    if df is None or df.empty:
        return {}

    ma50 = calc_ma(df, 50)
    ma200 = calc_ma(df, 200)
    current_price = float(df["Close"].squeeze().iloc[-1]) if not df.empty else None

    # MA signal
    ma_signal = "neutral"
    if ma50 and ma200:
        ma_signal = "golden" if ma50 > ma200 else "dead"

    # RSI signal
    rsi = calc_rsi(df)
    rsi_signal = "neutral"
    if rsi:
        if rsi >= 70:   rsi_signal = "overbought"
        elif rsi <= 30: rsi_signal = "oversold"

    return {
        "rsi":        rsi,
        "rsi_signal": rsi_signal,
        "stoch_rsi":  calc_stoch_rsi(df),
        "ma50":       ma50,
        "ma200":      ma200,
        "ma_signal":  ma_signal,
        "bollinger":  calc_bollinger(df),
        "momentum_1m": calc_momentum(df),
        "current_price": current_price,
    }
