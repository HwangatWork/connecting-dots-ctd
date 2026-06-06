"""
FinanceDataReader provider — Yahoo Finance 대체 무료 데이터 소스.
yfinance 429 차단 이후 주 데이터 소스로 전환.

심볼 매핑: 야후 심볼 → FDR 심볼 (실호출로 검증된 값)
  ^GSPC → US500   (S&P500,  실측 7,383)
  ^IXIC → IXIC    (NASDAQ,  실측 25,709)
  ^DJI  → DJI     (DOW,     실측 50,866)
  ^N225 → N225    (닛케이,  실측 66,588)
  ^VIX  → VIX     (VIX,     실측 21.51)
  CL=F  → CL      (WTI,     실측 88.58)
  GC=F  → GC=F    (금,      실측 4,337)
  KRW=X → USD/KRW (환율,    실측 1,558)
  KS11  → KS11    (KOSPI,   실측 8,160)
  KQ11  → KQ11    (KOSDAQ,  실측 1,002)

Cross-Source 확장 포인트:
  # TODO: 2차 소스 확보 시 아래 함수에서 비교 로직 추가
  # if abs(primary - secondary) / primary > 0.05: return None
"""
import logging
from datetime import datetime, timedelta
from typing import Optional

import pandas as pd
import data_registry as dr

log = logging.getLogger(__name__)

# Yahoo 심볼 → FDR 심볼 (실호출 검증 완료)
_FDR_MAP: dict[str, str] = {
    "^GSPC":   "US500",
    "^IXIC":   "IXIC",
    "^DJI":    "DJI",
    "^N225":   "N225",
    "^VIX":    "VIX",
    "CL=F":    "CL",
    "GC=F":    "GC=F",
    "KRW=X":   "USD/KRW",
    "KS11":    "KS11",
    "KQ11":    "KQ11",
}

# Range Check: 범위 벗어나면 None 반환 (가짜값 노출 방지)
_RANGE_BOUNDS: dict[str, tuple[float, float]] = {
    "^GSPC":  (3_000,   15_000),
    "^IXIC":  (8_000,   50_000),
    "^DJI":   (10_000, 100_000),
    "^N225":  (5_000,  100_000),
    "^VIX":   (10,       80),
    "CL=F":   (30,      200),
    "GC=F":   (1_500,   8_000),
    "KRW=X":  (900,     2_500),
    "KS11":   (1_500,  15_000),
    "KQ11":   (300,     5_000),
}


def _validate(yahoo_sym: str, price: float) -> bool:
    """Range Check — 범위 밖이면 False (점검 중 처리)."""
    bounds = _RANGE_BOUNDS.get(yahoo_sym)
    if bounds is None:
        return True
    lo, hi = bounds
    ok = lo <= price <= hi
    if not ok:
        log.warning(f"[FDR] Range check FAIL: {yahoo_sym} price={price:.2f} not in [{lo}, {hi}]")
    return ok


def get_current_prices(symbols: list[str]) -> dict[str, dict]:
    """
    배치 현재가 조회. yfinance.get_current_prices()와 동일 반환 형식.
    Returns: {yahoo_symbol: {price, change_pct, up}}
    FDR 실패 또는 Range 벗어남 → 해당 심볼 결과 미포함 (None 금지).
    """
    try:
        import FinanceDataReader as fdr
    except ImportError as e:
        log.error(f"[FDR] finance-datareader import failed: {e}")
        return {}

    result: dict[str, dict] = {}
    start = datetime.now() - timedelta(days=7)
    end = datetime.now()

    for yahoo_sym in symbols:
        fdr_sym = _FDR_MAP.get(yahoo_sym)
        if fdr_sym is None:
            # 매핑 없는 심볼 (SKEW 등) → 등록하지 않음
            log.debug(f"[FDR] No mapping for {yahoo_sym}, skipping")
            dr.record(f"yf_{yahoo_sym}", "FDR", True)
            continue
        try:
            df = fdr.DataReader(fdr_sym, start, end)
            if df is None or df.empty or "Close" not in df.columns:
                log.warning(f"[FDR] Empty response for {yahoo_sym} ({fdr_sym})")
                dr.record(f"yf_{yahoo_sym}", "FDR", True)
                continue

            last = float(df["Close"].iloc[-1])
            prev = float(df["Close"].iloc[-2]) if len(df) > 1 else last

            if not _validate(yahoo_sym, last):
                dr.record(f"yf_{yahoo_sym}", "FDR", True, f"range_fail:{last:.2f}")
                continue

            chg = (last - prev) / prev * 100 if prev else 0
            result[yahoo_sym] = {
                "price":      last,
                "change_pct": round(chg, 2),
                "up":         chg >= 0,
            }
            dr.record(f"yf_{yahoo_sym}", "FDR", False, f"{last:.4g}")

        except Exception as e:
            log.warning(f"[FDR] {yahoo_sym} ({fdr_sym}) failed: {e}")
            dr.record(f"yf_{yahoo_sym}", "FDR", True)

    return result


def get_price_history(yahoo_symbol: str, period: str = "6mo", interval: str = "1d") -> Optional[pd.DataFrame]:
    """
    OHLCV 히스토리. yfinance.get_price_history()와 동일 반환 형식.
    Close 컬럼 포함 DataFrame 또는 None.
    """
    try:
        import FinanceDataReader as fdr
    except ImportError as e:
        log.error(f"[FDR] finance-datareader import failed: {e}")
        return None

    fdr_sym = _FDR_MAP.get(yahoo_symbol)
    if fdr_sym is None:
        return None

    try:
        days = {"1mo": 35, "3mo": 100, "6mo": 185, "1y": 370}.get(period, 185)
        start = datetime.now() - timedelta(days=days)
        df = fdr.DataReader(fdr_sym, start, datetime.now())
        if df is None or df.empty or "Close" not in df.columns:
            dr.record(f"hist_{yahoo_symbol}", "FDR", True)
            return None
        dr.record(f"hist_{yahoo_symbol}", "FDR", False, f"{len(df)} rows")
        return df
    except Exception as e:
        log.warning(f"[FDR] history failed for {yahoo_symbol}: {e}")
        dr.record(f"hist_{yahoo_symbol}", "FDR", True)
        return None
