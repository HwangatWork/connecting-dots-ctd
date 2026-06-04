"""
pykrx provider — 한국거래소 무료 데이터.
수급(외국인/기관/개인) + 코스피/코스닥 시세.
"""
from datetime import datetime, timedelta
from typing import Optional
import logging

log = logging.getLogger(__name__)


def _today() -> str:
    return datetime.now().strftime("%Y%m%d")


def _n_days_ago(n: int) -> str:
    return (datetime.now() - timedelta(days=n)).strftime("%Y%m%d")


def get_market_indices() -> dict:
    """코스피/코스닥 현재 지수."""
    result = {"kospi": None, "kosdaq": None}
    try:
        from pykrx import stock
        today = _today()
        one_week_ago = _n_days_ago(7)

        kospi = stock.get_index_ohlcv(one_week_ago, today, "1001")
        kosdaq = stock.get_index_ohlcv(one_week_ago, today, "2001")

        if not kospi.empty:
            row = kospi.iloc[-1]
            prev = kospi.iloc[-2] if len(kospi) > 1 else None
            chg = ((row["종가"] - prev["종가"]) / prev["종가"] * 100) if prev is not None else 0
            result["kospi"] = {
                "value": row["종가"],
                "change_pct": round(chg, 2),
                "up": chg >= 0,
            }
        if not kosdaq.empty:
            row = kosdaq.iloc[-1]
            prev = kosdaq.iloc[-2] if len(kosdaq) > 1 else None
            chg = ((row["종가"] - prev["종가"]) / prev["종가"] * 100) if prev is not None else 0
            result["kosdaq"] = {
                "value": row["종가"],
                "change_pct": round(chg, 2),
                "up": chg >= 0,
            }
    except Exception as e:
        log.warning(f"[KRX] indices failed: {e}")
    return result


def get_supply_data(days: int = 20) -> dict:
    """
    외국인/기관/개인 순매수 금액 (코스피 전체).
    Returns: { foreign, institution, individual } 각각 { amount_100m, direction }
    """
    result = {}
    try:
        from pykrx import stock
        end = _today()
        start = _n_days_ago(days + 5)

        df = stock.get_market_trading_value_by_date(start, end, "KOSPI")
        if df.empty:
            return result

        # 최근 20거래일 합산
        recent = df.tail(days)
        foreign_sum = int(recent["외국인합계"].sum() / 1e8)    # 억원
        institution_sum = int(recent["기관합계"].sum() / 1e8)
        individual_sum = int(recent["개인"].sum() / 1e8)

        def fmt(v: int) -> str:
            sign = "+" if v >= 0 else ""
            return f"{sign}{v:,}억"

        result = {
            "foreign":     {"amount": fmt(foreign_sum),     "direction": 1 if foreign_sum >= 0 else -1,     "pct": min(100, abs(foreign_sum) // 100)},
            "institution": {"amount": fmt(institution_sum), "direction": 1 if institution_sum >= 0 else -1, "pct": min(100, abs(institution_sum) // 100)},
            "individual":  {"amount": fmt(individual_sum),  "direction": 1 if individual_sum >= 0 else -1,  "pct": min(100, abs(individual_sum) // 100)},
        }
    except Exception as e:
        log.warning(f"[KRX] supply failed: {e}")
    return result


def get_stock_price(code: str) -> Optional[dict]:
    """한국 종목 현재가 (코드: 6자리 숫자)."""
    try:
        from pykrx import stock
        today = _today()
        week_ago = _n_days_ago(7)
        df = stock.get_market_ohlcv(week_ago, today, code)
        if df.empty:
            return None
        row = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else None
        chg = ((row["종가"] - prev["종가"]) / prev["종가"] * 100) if prev is not None else 0
        return {
            "price": int(row["종가"]),
            "change_pct": round(chg, 2),
            "up": chg >= 0,
            "volume": int(row["거래량"]),
        }
    except Exception as e:
        log.warning(f"[KRX] stock price failed for {code}: {e}")
        return None
