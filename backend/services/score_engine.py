"""
IQ Score Engine — 64 indicators -> 8-axis radar scores (0-10).
Each axis is a weighted average of sub-indicators.
"""
from typing import Optional
import logging

log = logging.getLogger(__name__)


def _score_color(v: float) -> str:
    if v >= 8.0: return "#30d158"   # bullish
    if v >= 6.5: return "#0a84ff"   # neutral+
    if v >= 5.0: return "#ffd60a"   # caution
    return "#ff453a"                 # risk


def _clamp(v: float, lo=0.0, hi=10.0) -> float:
    return max(lo, min(hi, v))


# Per-axis scoring functions

def score_business_quality(info: dict) -> float:
    """Business quality: gross margin + operating margin."""
    gm = info.get("grossMargins", 0) or 0
    om = info.get("operatingMargins", 0) or 0
    s = gm * 6 + om * 4
    return _clamp(s * 10, 0, 10)


def score_growth_momentum(info: dict, tech: dict) -> float:
    """Growth momentum: EPS YoY, revenue YoY, price momentum."""
    eps_growth = info.get("earningsQuarterlyGrowth", 0) or 0
    rev_growth = info.get("revenueGrowth", 0) or 0
    momentum = tech.get("momentum_1m", 0) or 0

    eps_s = _clamp((eps_growth + 0.5) * 7, 0, 10)
    rev_s = _clamp((rev_growth + 0.2) * 10, 0, 10)
    mom_s = _clamp((momentum + 5) / 10 * 8, 0, 10)

    return round(_clamp(eps_s * 0.4 + rev_s * 0.4 + mom_s * 0.2), 1)


def score_valuation(info: dict) -> float:
    """Valuation: Forward P/E and PEG. Lower is better."""
    fpe = info.get("forwardPE", None)
    peg = info.get("pegRatio", None)

    s = 5.0  # baseline
    if fpe and fpe > 0:
        pe_s = _clamp(10 - (fpe - 10) * 0.25, 1, 9)
        s = pe_s
    if peg and peg > 0:
        peg_s = _clamp(10 - peg * 2.5, 1, 10)
        s = (s + peg_s) / 2

    return round(s, 1)


def score_market_timing(tech: dict) -> float:
    """Market timing: RSI, Stoch RSI, MA signal."""
    rsi = tech.get("rsi", 50) or 50
    stoch = tech.get("stoch_rsi", 50) or 50
    ma_signal = tech.get("ma_signal", "neutral")

    if 40 <= rsi <= 60:   rsi_s = 7.0
    elif 30 <= rsi < 40:  rsi_s = 8.5   # oversold = buy opportunity
    elif rsi < 30:        rsi_s = 9.5
    elif 60 < rsi <= 70:  rsi_s = 5.5
    else:                 rsi_s = 3.0   # overbought

    if stoch < 20:        stoch_s = 9.0
    elif stoch < 40:      stoch_s = 7.5
    elif stoch < 60:      stoch_s = 6.0
    elif stoch < 80:      stoch_s = 4.5
    else:                 stoch_s = 2.5

    ma_s = 7.0 if ma_signal == "golden" else (4.0 if ma_signal == "dead" else 5.5)

    return round(_clamp(rsi_s * 0.4 + stoch_s * 0.3 + ma_s * 0.3), 1)


def score_financial_health(info: dict) -> float:
    """Financial health: D/E ratio, current ratio, FCF."""
    de = info.get("debtToEquity", None)
    cr = info.get("currentRatio", None)
    fcf_yield = info.get("freeCashflow", None)
    market_cap = info.get("marketCap", 1) or 1

    s = 6.0
    if de is not None and de >= 0:
        de_s = _clamp(10 - de * 0.015, 1, 10)
        s = de_s
    if cr:
        cr_s = _clamp(min(cr * 2.5, 10), 1, 10)
        s = (s + cr_s) / 2
    if fcf_yield and market_cap:
        fcf_s = _clamp((fcf_yield / market_cap) * 100 * 5 + 5, 1, 10)
        s = (s * 2 + fcf_s) / 3

    return round(_clamp(s), 1)


def score_macro_linkage(info: dict, macro: dict) -> float:
    """Macro linkage: sector fit to current macro environment."""
    sector = (info.get("sector") or "").lower()
    vix = macro.get("vix", 20)
    sp_momentum = macro.get("sp_momentum", 0)

    base = 6.0
    if "technology" in sector or "semiconductors" in sector:
        base = 7.5 if sp_momentum > 0 else 5.5

    vix_adj = 1.0 if vix < 20 else (-0.5 if vix < 25 else -1.5)
    sp_adj = 1.0 if sp_momentum > 3 else (0.0 if sp_momentum > 0 else -1.0)

    return round(_clamp(base + vix_adj + sp_adj), 1)


def score_risk_management(info: dict, tech: dict, supply: dict) -> float:
    """Risk management: beta, volatility, foreign flow."""
    beta = info.get("beta", 1.0) or 1.0
    beta_s = _clamp(10 - (beta - 0.5) * 3, 1, 10)

    foreign_dir = 1 if (supply.get("foreign", {}).get("direction", 0) == 1) else -1
    supply_s = 7.0 if foreign_dir > 0 else 4.0

    return round(_clamp(beta_s * 0.6 + supply_s * 0.4), 1)


def score_after_tax_return(info: dict, is_domestic: bool, target_return: float = 0.3) -> float:
    """After-tax return: expected net return vs target."""
    tax_rate = 0.0 if is_domestic else 0.22
    after_tax = target_return * (1 - tax_rate)
    s = _clamp(4 + after_tax * 16, 1, 10)
    return round(s, 1)


# Main calculation

def calculate_iq_score(
    info: dict,
    tech: dict,
    macro: dict,
    supply: dict,
    is_domestic: bool,
) -> dict:
    """
    Calculate 8-axis IQ score.
    Returns: { scores: [8 floats], colors: [8 hex], overall: float }
    """
    axes = {
        "비즈니스 품질": score_business_quality(info),
        "성장 모멘텀":   score_growth_momentum(info, tech),
        "밸류에이션":    score_valuation(info),
        "시장 타이밍":   score_market_timing(tech),
        "재무 건전성":   score_financial_health(info),
        "매크로 연계":   score_macro_linkage(info, macro),
        "리스크 관리":   score_risk_management(info, tech, supply),
        "세후 수익률":   score_after_tax_return(info, is_domestic),
    }

    scores = list(axes.values())
    colors = [_score_color(v) for v in scores]
    overall = round(sum(scores) / len(scores), 1)

    return {
        "scores": scores,
        "colors": colors,
        "axes": list(axes.keys()),
        "overall": overall,
        "breakdown": axes,
    }


def calculate_market_temperature(macro: dict, supply: dict) -> int:
    """Calculate composite market temperature (0-100)."""
    from config import TEMPERATURE_WEIGHTS

    fg = macro.get("fear_greed", 50)

    vix = macro.get("vix", 20)
    if vix < 15:   vix_s = 85
    elif vix < 20: vix_s = 72
    elif vix < 25: vix_s = 55
    elif vix < 30: vix_s = 38
    else:          vix_s = 22

    sp_mom = macro.get("sp_momentum", 0)
    if sp_mom > 8:    sp_s = 85
    elif sp_mom > 4:  sp_s = 75
    elif sp_mom > 1:  sp_s = 65
    elif sp_mom > 0:  sp_s = 55
    elif sp_mom > -2: sp_s = 42
    else:             sp_s = 28

    hy = macro.get("hy_spread", 4.0)
    if hy < 3.0:   hy_s = 82
    elif hy < 3.5: hy_s = 72
    elif hy < 4.5: hy_s = 58
    elif hy < 5.5: hy_s = 42
    else:          hy_s = 28

    spread = macro.get("rate_spread", 0.0)
    if spread > 0.5:    rate_s = 75
    elif spread > 0:    rate_s = 62
    elif spread > -0.5: rate_s = 48
    else:               rate_s = 32

    kp_mom = macro.get("kospi_momentum", 0)
    kp_s = 65 + kp_mom * 2

    scores = {
        "fear_greed":      fg,
        "vix_score":       vix_s,
        "sp_momentum":     sp_s,
        "hy_spread":       hy_s,
        "rate_spread":     rate_s,
        "kospi_momentum":  max(20, min(90, kp_s)),
    }

    temp = sum(scores[k] * TEMPERATURE_WEIGHTS[k] for k in TEMPERATURE_WEIGHTS)
    return max(0, min(100, round(temp)))


def temperature_to_verdict(temp: int) -> tuple[str, str]:
    """온도 → (판단 문장, CSS color var)"""
    if temp >= 75: return "과열 주의 구간",    "var(--re)"
    if temp >= 60: return "분할 매수 구간",    "var(--gr)"
    if temp >= 45: return "중립 관망 구간",    "var(--ac)"
    if temp >= 30: return "분할 매수 시작",    "var(--ye)"
    return "적극 매수 구간",                   "var(--gr)"
