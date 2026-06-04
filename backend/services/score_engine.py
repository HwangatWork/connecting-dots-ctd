"""
IQ ?�코???�진 ??64�?지????8�??�이???�수 (0~10).
�?축�? ?�러 ?�위 지?�의 가�??�균?�로 계산.
"""
from typing import Optional
import logging

log = logging.getLogger(__name__)

# ?�수 ?�상 기�?
def _score_color(v: float) -> str:
    if v >= 8.0: return "#30d158"   # 강세
    if v >= 6.5: return "#0a84ff"   # 중립+
    if v >= 5.0: return "#ffd60a"   # 주의
    return "#ff453a"                 # ?�험


def _clamp(v: float, lo=0.0, hi=10.0) -> float:
    return max(lo, min(hi, v))


# ?�?� 축별 계산 ?�수 ?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�

def score_business_quality(info: dict) -> float:
    """비즈?�스 ?�질: 매출총이?�률, ?�업?�익�?"""
    gm = info.get("grossMargins", 0) or 0
    om = info.get("operatingMargins", 0) or 0
    # 0~1 범위 ??0~10 ?�수
    s = gm * 6 + om * 4
    return _clamp(s * 10, 0, 10)


def score_growth_momentum(info: dict, tech: dict) -> float:
    """?�장 모멘?�: EPS YoY, 매출 YoY, 주�? 모멘?�."""
    eps_growth = info.get("earningsQuarterlyGrowth", 0) or 0  # -1 ~ +inf
    rev_growth = info.get("revenueGrowth", 0) or 0
    momentum = tech.get("momentum_1m", 0) or 0

    eps_s = _clamp((eps_growth + 0.5) * 7, 0, 10)
    rev_s = _clamp((rev_growth + 0.2) * 10, 0, 10)
    mom_s = _clamp((momentum + 5) / 10 * 8, 0, 10)

    return round(_clamp(eps_s * 0.4 + rev_s * 0.4 + mom_s * 0.2), 1)


def score_valuation(info: dict) -> float:
    """밸류?�이?? Forward P/E, PEG. ??��?�록 좋음."""
    fpe = info.get("forwardPE", None)
    peg = info.get("pegRatio", None)

    s = 5.0  # 기본�?    if fpe and fpe > 0:
        # P/E 10 ?�하 ??9?? 30 ?�상 ??3??        pe_s = _clamp(10 - (fpe - 10) * 0.25, 1, 9)
        s = pe_s
    if peg and peg > 0:
        peg_s = _clamp(10 - peg * 2.5, 1, 10)
        s = (s + peg_s) / 2

    return round(s, 1)


def score_market_timing(tech: dict) -> float:
    """?�장 ?�?�밍: RSI, Stoch RSI, MA ?�호."""
    rsi = tech.get("rsi", 50) or 50
    stoch = tech.get("stoch_rsi", 50) or 50
    ma_signal = tech.get("ma_signal", "neutral")

    # RSI: 40~60??최적 (중립 매수 구간)
    if 40 <= rsi <= 60:   rsi_s = 7.0
    elif 30 <= rsi < 40:  rsi_s = 8.5   # 과매??= 매수 기회
    elif rsi < 30:        rsi_s = 9.5
    elif 60 < rsi <= 70:  rsi_s = 5.5
    else:                 rsi_s = 3.0   # 과매??
    # Stoch RSI
    if stoch < 20:        stoch_s = 9.0
    elif stoch < 40:      stoch_s = 7.5
    elif stoch < 60:      stoch_s = 6.0
    elif stoch < 80:      stoch_s = 4.5
    else:                 stoch_s = 2.5

    ma_s = 7.0 if ma_signal == "golden" else (4.0 if ma_signal == "dead" else 5.5)

    return round(_clamp(rsi_s * 0.4 + stoch_s * 0.3 + ma_s * 0.3), 1)


def score_financial_health(info: dict) -> float:
    """?�무 건전?? 부채비?? Current Ratio, FCF."""
    de = info.get("debtToEquity", None)        # ??��?�록 좋음
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
    """매크�??�계: ?�터 분류 기반 매크�??�경 ?�합??"""
    sector = (info.get("sector") or "").lower()
    vix = macro.get("vix", 20)
    sp_momentum = macro.get("sp_momentum", 0)

    # AI/?�크 ?�터????? 금리 + 강세?�에???�리
    base = 6.0
    if "technology" in sector or "semiconductors" in sector:
        base = 7.5 if sp_momentum > 0 else 5.5

    vix_adj = 1.0 if vix < 20 else (-0.5 if vix < 25 else -1.5)
    sp_adj = 1.0 if sp_momentum > 3 else (0.0 if sp_momentum > 0 else -1.0)

    return round(_clamp(base + vix_adj + sp_adj), 1)


def score_risk_management(info: dict, tech: dict, supply: dict) -> float:
    """리스??관�? Beta, 변?�성, ?�급."""
    beta = info.get("beta", 1.0) or 1.0
    # Beta 1.0??중립 (5??, ?�을?�록 ?�험
    beta_s = _clamp(10 - (beta - 0.5) * 3, 1, 10)

    # ?�급: ?�국??매수 방향
    foreign_dir = 1 if (supply.get("foreign", {}).get("direction", 0) == 1) else -1
    supply_s = 7.0 if foreign_dir > 0 else 4.0

    return round(_clamp(beta_s * 0.6 + supply_s * 0.4), 1)


def score_after_tax_return(info: dict, is_domestic: bool, target_return: float = 0.3) -> float:
    """?�후 ?�익�? 목표?�익�??��??�후 기�??�익�?"""
    # �?��: ?�도??0%, ?�외: 22%
    tax_rate = 0.0 if is_domestic else 0.22
    after_tax = target_return * (1 - tax_rate)
    # ?�후 30% ?�상 ??9?? 10% 미만 ??4??    s = _clamp(4 + after_tax * 16, 1, 10)
    return round(s, 1)


# ?�?� 메인 계산 ?�수 ?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�

def calculate_iq_score(
    info: dict,
    tech: dict,
    macro: dict,
    supply: dict,
    is_domestic: bool,
) -> dict:
    """
    8�?IQ ?�코??계산.
    Returns: { scores: [8 floats], colors: [8 hex], overall: float }
    """
    axes = {
        "비즈?�스 ?�질": score_business_quality(info),
        "?�장 모멘?�":   score_growth_momentum(info, tech),
        "밸류?�이??:    score_valuation(info),
        "?�장 ?�?�밍":   score_market_timing(tech),
        "?�무 건전??:   score_financial_health(info),
        "매크�??�계":   score_macro_linkage(info, macro),
        "리스??관�?:   score_risk_management(info, tech, supply),
        "?�후 ?�익�?:   score_after_tax_return(info, is_domestic),
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
    """
    ?�장 종합 ?�도 계산 (0~100).
    """
    from config import TEMPERATURE_WEIGHTS

    fg = macro.get("fear_greed", 50)

    # VIX ??0~100 ?�수 (VIX ??��?�록 = 강세)
    vix = macro.get("vix", 20)
    if vix < 15:   vix_s = 85
    elif vix < 20: vix_s = 72
    elif vix < 25: vix_s = 55
    elif vix < 30: vix_s = 38
    else:          vix_s = 22

    # S&P500 1개월 모멘?�
    sp_mom = macro.get("sp_momentum", 0)
    if sp_mom > 8:    sp_s = 85
    elif sp_mom > 4:  sp_s = 75
    elif sp_mom > 1:  sp_s = 65
    elif sp_mom > 0:  sp_s = 55
    elif sp_mom > -2: sp_s = 42
    else:             sp_s = 28

    # HY ?�프?�드 ??�� (??��?�록 = ?�용 건전)
    hy = macro.get("hy_spread", 4.0)
    if hy < 3.0:   hy_s = 82
    elif hy < 3.5: hy_s = 72
    elif hy < 4.5: hy_s = 58
    elif hy < 5.5: hy_s = 42
    else:          hy_s = 28

    # ?�단�?금리�?(?�수 = ?�상, ?�수 = ??��)
    spread = macro.get("rate_spread", 0.0)
    if spread > 0.5:   rate_s = 75
    elif spread > 0:   rate_s = 62
    elif spread > -0.5:rate_s = 48
    else:              rate_s = 32

    # 코스??모멘?�
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
    """?�도 ??(?�단 문장, CSS color var)"""
    if temp >= 75: return "과열 주의 구간",   "var(--re)"
    if temp >= 60: return "분할 매수 구간",   "var(--gr)"
    if temp >= 45: return "중립 관�?구간",   "var(--ac)"
    if temp >= 30: return "분할 매수 ?�작",   "var(--ye)"
    return "?�극 매수 구간",                  "var(--gr)"
