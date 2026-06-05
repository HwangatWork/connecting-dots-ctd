"""
/api/v1/status — 64-indicator data collection status.
"""
from fastapi import APIRouter, Header, HTTPException
from datetime import datetime, timezone
import data_registry as dr

router = APIRouter()

# ── 64-indicator catalog ───────────────────────────────────────────
# type:
#   "registry"   → look up in data_registry by id
#   "hardcoded"  → always "정상" (constant value, no fetch needed)
#   "calculated" → derived from live data; check parent source availability

INDICATOR_CATALOG = [
    # ── 시장지수 (9) ─────────────────────────────────────────────
    {"id": "yf_^GSPC",     "name": "S&P 500",            "cat": "시장지수",   "type": "registry",   "provider": "Yahoo Finance"},
    {"id": "yf_^IXIC",     "name": "NASDAQ",             "cat": "시장지수",   "type": "registry",   "provider": "Yahoo Finance"},
    {"id": "yf_^DJI",      "name": "DOW Jones",          "cat": "시장지수",   "type": "registry",   "provider": "Yahoo Finance"},
    {"id": "yf_^N225",     "name": "닛케이225",           "cat": "시장지수",   "type": "registry",   "provider": "Yahoo Finance"},
    {"id": "yf_^VIX",      "name": "VIX 공포지수",       "cat": "시장지수",   "type": "registry",   "provider": "Yahoo Finance"},
    {"id": "yf_CL=F",      "name": "WTI 원유",           "cat": "시장지수",   "type": "registry",   "provider": "Yahoo Finance"},
    {"id": "yf_GC=F",      "name": "금 선물",            "cat": "시장지수",   "type": "registry",   "provider": "Yahoo Finance"},
    {"id": "yf_KRW=X",     "name": "USD/KRW 환율",       "cat": "시장지수",   "type": "registry",   "provider": "Yahoo Finance"},
    {"id": "hist_^GSPC",   "name": "S&P500 3M 모멘텀",   "cat": "시장지수",   "type": "registry",   "provider": "Yahoo Finance"},
    # ── 국내지수 (2) ─────────────────────────────────────────────
    {"id": "krx_kospi",    "name": "코스피 지수",         "cat": "국내지수",   "type": "registry",   "provider": "pykrx"},
    {"id": "krx_kosdaq",   "name": "코스닥 지수",         "cat": "국내지수",   "type": "registry",   "provider": "pykrx"},
    # ── 매크로 (7) ───────────────────────────────────────────────
    {"id": "fred_walcl",   "name": "연준 총자산 WALCL",   "cat": "매크로",     "type": "registry",   "provider": "FRED"},
    {"id": "fred_t10y2y",  "name": "장단기금리차 T10Y2Y", "cat": "매크로",     "type": "registry",   "provider": "FRED"},
    {"id": "hy_spread",    "name": "HY 스프레드",         "cat": "매크로",     "type": "hardcoded",  "provider": "하드코딩"},
    {"id": "yf_DX-Y.NYB",  "name": "달러인덱스 DXY",      "cat": "매크로",     "type": "registry",   "provider": "Yahoo Finance"},
    {"id": "yf_^SKEW",     "name": "CBOE SKEW",           "cat": "매크로",     "type": "registry",   "provider": "Yahoo Finance"},
    {"id": "yf_^TNX",      "name": "미국 10Y 금리",       "cat": "매크로",     "type": "registry",   "provider": "Yahoo Finance"},
    {"id": "yf_^IRX",      "name": "미국 2Y 금리",        "cat": "매크로",     "type": "registry",   "provider": "Yahoo Finance"},
    # ── 심리 (3) ─────────────────────────────────────────────────
    {"id": "fg_index",     "name": "Fear & Greed Index",  "cat": "심리",       "type": "registry",   "provider": "Alternative.me"},
    {"id": "put_call",     "name": "Put/Call 비율",        "cat": "심리",       "type": "hardcoded",  "provider": "하드코딩"},
    {"id": "market_temp",  "name": "시장 온도 종합",       "cat": "심리",       "type": "calculated", "provider": "계산값", "deps": ["fg_index", "yf_^VIX"]},
    # ── 수급 (3) ─────────────────────────────────────────────────
    {"id": "krx_foreign",    "name": "외국인 순매수",     "cat": "수급",       "type": "registry",   "provider": "pykrx"},
    {"id": "krx_institution","name": "기관 순매수",       "cat": "수급",       "type": "registry",   "provider": "pykrx"},
    {"id": "krx_individual", "name": "개인 순매수",       "cat": "수급",       "type": "registry",   "provider": "pykrx"},
    # ── 기술적지표 (8) ───────────────────────────────────────────
    {"id": "tech_rsi",     "name": "RSI(14)",             "cat": "기술적지표", "type": "calculated", "provider": "계산값", "deps": ["hist_^GSPC"]},
    {"id": "tech_stoch",   "name": "Stochastic RSI",      "cat": "기술적지표", "type": "calculated", "provider": "계산값", "deps": ["hist_^GSPC"]},
    {"id": "tech_ma",      "name": "이동평균 신호",        "cat": "기술적지표", "type": "calculated", "provider": "계산값", "deps": ["hist_^GSPC"]},
    {"id": "tech_mom1m",   "name": "1개월 모멘텀",         "cat": "기술적지표", "type": "calculated", "provider": "계산값", "deps": ["hist_^GSPC"]},
    {"id": "tech_mom3m",   "name": "3개월 모멘텀",         "cat": "기술적지표", "type": "calculated", "provider": "계산값", "deps": ["hist_^GSPC"]},
    {"id": "tech_mom6m",   "name": "6개월 모멘텀",         "cat": "기술적지표", "type": "calculated", "provider": "계산값", "deps": ["hist_^GSPC"]},
    {"id": "tech_atr",     "name": "ATR(14)",              "cat": "기술적지표", "type": "calculated", "provider": "계산값", "deps": ["hist_^GSPC"]},
    {"id": "tech_bb",      "name": "볼린저밴드 위치",      "cat": "기술적지표", "type": "calculated", "provider": "계산값", "deps": ["hist_^GSPC"]},
    # ── 펀더멘털 (8) ─────────────────────────────────────────────
    {"id": "fund_gm",      "name": "매출총이익률",         "cat": "펀더멘털",   "type": "calculated", "provider": "Yahoo Finance/pykrx", "deps": ["info_000660", "info_NVDA"]},
    {"id": "fund_om",      "name": "영업이익률",           "cat": "펀더멘털",   "type": "calculated", "provider": "Yahoo Finance/pykrx", "deps": ["info_000660", "info_NVDA"]},
    {"id": "fund_eps_g",   "name": "EPS 성장률 YoY",       "cat": "펀더멘털",   "type": "calculated", "provider": "Yahoo Finance",       "deps": ["info_000660", "info_NVDA"]},
    {"id": "fund_rev_g",   "name": "매출 성장률 YoY",      "cat": "펀더멘털",   "type": "calculated", "provider": "Yahoo Finance/pykrx", "deps": ["info_000660", "info_NVDA"]},
    {"id": "fund_fcf",     "name": "잉여현금흐름 FCF",     "cat": "펀더멘털",   "type": "calculated", "provider": "Yahoo Finance/pykrx", "deps": ["info_000660", "info_NVDA"]},
    {"id": "fund_de",      "name": "부채비율 D/E",          "cat": "펀더멘털",   "type": "calculated", "provider": "Yahoo Finance/pykrx", "deps": ["info_000660", "info_NVDA"]},
    {"id": "fund_cr",      "name": "유동비율",              "cat": "펀더멘털",   "type": "calculated", "provider": "Yahoo Finance/pykrx", "deps": ["info_000660", "info_NVDA"]},
    {"id": "fund_roe",     "name": "자기자본이익률",        "cat": "펀더멘털",   "type": "calculated", "provider": "Yahoo Finance/pykrx", "deps": ["info_000660", "info_NVDA"]},
    # ── 밸류에이션 (7) ───────────────────────────────────────────
    {"id": "val_fpe",      "name": "Forward P/E",          "cat": "밸류에이션", "type": "calculated", "provider": "Yahoo Finance",       "deps": ["info_000660", "info_NVDA"]},
    {"id": "val_tpe",      "name": "Trailing P/E",          "cat": "밸류에이션", "type": "calculated", "provider": "Yahoo Finance/pykrx", "deps": ["info_000660", "info_NVDA"]},
    {"id": "val_peg",      "name": "PEG Ratio",             "cat": "밸류에이션", "type": "calculated", "provider": "Yahoo Finance",       "deps": ["info_000660", "info_NVDA"]},
    {"id": "val_ev_rev",   "name": "EV/Revenue",            "cat": "밸류에이션", "type": "calculated", "provider": "Yahoo Finance",       "deps": ["info_000660", "info_NVDA"]},
    {"id": "val_pb",       "name": "P/Book",                "cat": "밸류에이션", "type": "calculated", "provider": "Yahoo Finance/pykrx", "deps": ["info_000660", "info_NVDA"]},
    {"id": "val_dcf",      "name": "DCF 내재가치 업사이드", "cat": "밸류에이션", "type": "calculated", "provider": "계산값",              "deps": ["info_000660", "info_NVDA"]},
    {"id": "val_mktcap",   "name": "시가총액",              "cat": "밸류에이션", "type": "calculated", "provider": "Yahoo Finance/pykrx", "deps": ["info_000660", "info_NVDA"]},
    # ── 리스크 (2) ───────────────────────────────────────────────
    {"id": "risk_beta",    "name": "베타(Beta)",            "cat": "리스크",     "type": "calculated", "provider": "Yahoo Finance",       "deps": ["info_000660", "info_NVDA"]},
    {"id": "risk_vol",     "name": "변동성 30D",             "cat": "리스크",     "type": "calculated", "provider": "계산값",              "deps": ["hist_^GSPC"]},
    # ── 세금/절세 (7) ────────────────────────────────────────────
    {"id": "tax_domestic", "name": "국내 배당소득세 (0%)",  "cat": "세금/절세",  "type": "hardcoded",  "provider": "하드코딩"},
    {"id": "tax_overseas", "name": "해외 배당세 (15.4%)",   "cat": "세금/절세",  "type": "hardcoded",  "provider": "하드코딩"},
    {"id": "tax_capital",  "name": "양도소득세 (22%)",       "cat": "세금/절세",  "type": "hardcoded",  "provider": "하드코딩"},
    {"id": "tax_isa",      "name": "ISA 절세 효과",          "cat": "세금/절세",  "type": "hardcoded",  "provider": "하드코딩"},
    {"id": "tax_pension",  "name": "연금저축 절세",           "cat": "세금/절세",  "type": "hardcoded",  "provider": "하드코딩"},
    {"id": "tax_irp",      "name": "IRP 절세",               "cat": "세금/절세",  "type": "hardcoded",  "provider": "하드코딩"},
    {"id": "tax_fx",       "name": "환율과세",               "cat": "세금/절세",  "type": "hardcoded",  "provider": "하드코딩"},
    # ── IQ 스코어 8축 (8) ────────────────────────────────────────
    {"id": "iq_business",  "name": "비즈니스 품질",          "cat": "IQ 스코어", "type": "calculated", "provider": "계산값", "deps": ["info_000660", "info_NVDA"]},
    {"id": "iq_growth",    "name": "성장 모멘텀",            "cat": "IQ 스코어", "type": "calculated", "provider": "계산값", "deps": ["info_000660", "info_NVDA"]},
    {"id": "iq_valuation", "name": "밸류에이션 점수",        "cat": "IQ 스코어", "type": "calculated", "provider": "계산값", "deps": ["info_000660", "info_NVDA"]},
    {"id": "iq_timing",    "name": "시장 타이밍",            "cat": "IQ 스코어", "type": "calculated", "provider": "계산값", "deps": ["hist_^GSPC"]},
    {"id": "iq_health",    "name": "재무 건전성",            "cat": "IQ 스코어", "type": "calculated", "provider": "계산값", "deps": ["info_000660", "info_NVDA"]},
    {"id": "iq_macro",     "name": "매크로 연계",            "cat": "IQ 스코어", "type": "calculated", "provider": "계산값", "deps": ["fg_index", "yf_^VIX"]},
    {"id": "iq_risk",      "name": "리스크 관리",            "cat": "IQ 스코어", "type": "calculated", "provider": "계산값", "deps": ["info_000660", "info_NVDA"]},
    {"id": "iq_aftertax",  "name": "세후 수익률",            "cat": "IQ 스코어", "type": "hardcoded",  "provider": "하드코딩"},
]


def _resolve_indicator(ind: dict) -> dict:
    itype = ind["type"]
    ind_id = ind["id"]

    if itype == "hardcoded":
        return {
            "id":          ind_id,
            "name":        ind["name"],
            "cat":         ind["cat"],
            "provider":    ind["provider"],
            "status":      "정상",
            "status_type": "hardcoded",
            "last_updated": None,
            "value_hint":  None,
        }

    if itype == "registry":
        s = dr.get_status(ind_id)
        return {
            "id":          ind_id,
            "name":        ind["name"],
            "cat":         ind["cat"],
            "provider":    ind["provider"],
            "status":      s["status"],
            "status_type": s["status"],
            "last_updated": s["last_updated"],
            "value_hint":  s.get("value_hint"),
        }

    # calculated — check deps
    deps = ind.get("deps", [])
    if not deps:
        # no deps to check, mark as "정상" if any stock data is available
        deps = ["hist_^GSPC"]

    any_real = dr.any_collected(*deps)
    any_present = dr.any_registered(*deps)

    if not any_present:
        st = "미수집"
    elif any_real:
        st = "정상"
    else:
        st = "폴백"

    # use the earliest dep timestamp as last_updated
    last_updated = None
    for dep in deps:
        s = dr.get_status(dep)
        if s["last_updated"]:
            last_updated = s["last_updated"]
            break

    return {
        "id":          ind_id,
        "name":        ind["name"],
        "cat":         ind["cat"],
        "provider":    ind["provider"],
        "status":      st,
        "status_type": st,
        "last_updated": last_updated,
        "value_hint":  None,
    }


@router.get("/status")
async def get_data_status():
    """Return 64-indicator collection status grouped by category."""
    resolved = [_resolve_indicator(ind) for ind in INDICATOR_CATALOG]

    # summary counts
    total = len(resolved)
    real     = sum(1 for r in resolved if r["status"] in ("정상",))
    fallback = sum(1 for r in resolved if r["status"] == "폴백")
    uncoll   = sum(1 for r in resolved if r["status"] == "미수집")
    hardcoded = sum(1 for r in resolved if r["status_type"] == "hardcoded")

    real_ratio = round((real + hardcoded) / total * 100, 1)

    # group by category
    cats: dict[str, list] = {}
    for r in resolved:
        cats.setdefault(r["cat"], []).append(r)

    categories = [{"name": k, "indicators": v} for k, v in cats.items()]

    return {
        "summary": {
            "total":       total,
            "real":        real,
            "fallback":    fallback,
            "uncollected": uncoll,
            "hardcoded":   hardcoded,
            "real_ratio":  real_ratio,
            "checked_at":  datetime.now(timezone.utc).isoformat(),
        },
        "categories": categories,
    }
