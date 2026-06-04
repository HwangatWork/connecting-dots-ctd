"""
?�장 ?�비?????�장 ???�체 ?�이??조립.
providers?�서 ?�시 ?�이?��? ?�집?�고 ?�코???�진?�로 ?�도 계산.
"""
from datetime import datetime, timezone
import logging

from providers import yahoo_finance as yf_p
from providers import krx as krx_p
from providers import fear_greed as fg_p
from services import technical as ta
from services.score_engine import calculate_market_temperature, temperature_to_verdict
from config import INDEX_SYMBOLS
from schemas import (
    MarketResponse, QuickMetric, CTDNode, CTDRow,
    SupplyData, SupplyActor, PhaseData, SignalSummary,
)

log = logging.getLogger(__name__)

# ?�?� 가중치 ?�수 ?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�
_HY_SPREAD_FALLBACK = 3.8   # ?�시�?HY ?�프?�드??별도 ?�료 API ?�요 ??최근�??�드코딩


async def build_market_response() -> MarketResponse:
    """?�장 ???�체 ?�이?��? 조립??MarketResponse 반환."""

    # ?�?� 1. ?�이???�집 ?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�
    fg_data = await fg_p.get_fear_greed()
    krx_indices = krx_p.get_market_indices()
    supply_raw = krx_p.get_supply_data(days=20)

    # S&P500 ?�스?�리 (모멘?� 계산??
    sp_df = yf_p.get_price_history(INDEX_SYMBOLS["sp500"], period="3mo")
    sp_momentum = ta.calc_momentum(sp_df) if sp_df is not None else 0

    # ?�?� ?�퍼: 가�?dict?�서 ?�전?�게 �?추출 ?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�
    def _safe_get(prices_dict: dict, key: str, default_price=None) -> dict:
        """prices dict?�서 None-safe?�게 가�??�보 반환."""
        d = prices_dict.get(key) or {}
        return d if d.get("price") is not None else {"price": default_price, "change_pct": 0, "up": True}

    # VIX ?�재�?    vix_info = yf_p.get_current_prices([INDEX_SYMBOLS["vix"]])
    vix_val = (_safe_get(vix_info, INDEX_SYMBOLS["vix"], 20)).get("price", 20) or 20

    # 코스??모멘?� (None ?�전 처리)
    kospi_data = krx_indices.get("kospi") or {}
    kospi_val = kospi_data.get("value", 2800) or 2800
    kospi_chg = kospi_data.get("change_pct", 0) or 0

    # 미국 10?�물 금리 (TNX)
    tnx_info = yf_p.get_current_prices([INDEX_SYMBOLS["tnx"]])
    tnx_val = (_safe_get(tnx_info, INDEX_SYMBOLS["tnx"], 4.45)).get("price", 4.45) or 4.45

    # DXY
    dxy_info = yf_p.get_current_prices([INDEX_SYMBOLS["dxy"]])
    dxy_val = (_safe_get(dxy_info, INDEX_SYMBOLS["dxy"], 104)).get("price", 104) or 104

    # S&P500 ?�재가
    sp_prices = yf_p.get_current_prices([INDEX_SYMBOLS["sp500"]])
    sp_val = _safe_get(sp_prices, INDEX_SYMBOLS["sp500"], 5600)

    # ?�스??    nd_prices = yf_p.get_current_prices([INDEX_SYMBOLS["nasdaq"]])
    nd_val = _safe_get(nd_prices, INDEX_SYMBOLS["nasdaq"], 19800)

    # WTI
    wti_prices = yf_p.get_current_prices([INDEX_SYMBOLS["wti"]])
    wti_val = _safe_get(wti_prices, INDEX_SYMBOLS["wti"], 78)

    # USD/KRW (?�후: KRW=X ?�는 USDKRW=X)
    fx_prices = yf_p.get_current_prices(["KRW=X"])
    fx_val = (_safe_get(fx_prices, "KRW=X", 1380)).get("price", 1380) or 1380

    # ?�?� 2. 매크�??�셔?�리 조립 ?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�
    macro = {
        "fear_greed":     fg_data["value"],
        "vix":            vix_val,
        "sp_momentum":    sp_momentum or 0,
        "hy_spread":      _HY_SPREAD_FALLBACK,
        "rate_spread":    tnx_val - 4.9 if tnx_val else 0,  # 10Y - 2Y 근사
        "kospi_momentum": kospi_chg,
    }

    # ?�?� 3. ?�장 ?�도 & ?�단 ?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�
    temp = calculate_market_temperature(macro, supply_raw)
    verdict, verdict_color = temperature_to_verdict(temp)

    # ?�?� 4. ??메트�?6�??�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�
    def _chg_color(up: bool) -> str:
        return "var(--gr)" if up else "var(--re)"

    def _fmt_price(v, decimals=0) -> str:
        if v is None: return "??
        return f"{v:,.{decimals}f}" if decimals else f"{int(v):,}"

    def _fmt_chg(c) -> str:
        if c is None: return ""
        sign = "+" if c >= 0 else ""
        return f"{sign}{c:.2f}%"

    vix_color = "var(--gr)" if vix_val < 20 else ("var(--ye)" if vix_val < 25 else "var(--re)")
    fg_color  = "var(--gr)" if fg_data["value"] < 40 else ("var(--ye)" if fg_data["value"] < 65 else "var(--re)")
    fx_color  = "var(--re)" if fx_val and fx_val > 1350 else "var(--ye)"
    tnx_color = "var(--re)" if tnx_val and tnx_val > 4.5 else "var(--ye)"

    quick_metrics = [
        QuickMetric(label="VIX",    value=f"{vix_val:.1f}", color=vix_color,  sub="공포지??),
        QuickMetric(label="F&G",    value=str(fg_data["value"]),               color=fg_color,  sub=fg_data["label"]),
        QuickMetric(label="?�율",   value=_fmt_price(fx_val),                  color=fx_color,  sub="USD/KRW"),
        QuickMetric(label="금리",   value=f"{tnx_val:.2f}%" if tnx_val else "??, color=tnx_color, sub="미국 10Y"),
        QuickMetric(label="코스??, value=_fmt_price(kospi_val),               color=_chg_color(kospi_chg >= 0), sub=_fmt_chg(kospi_chg)),
        QuickMetric(label="S&P",    value=_fmt_price(sp_val.get("price")),     color=_chg_color(sp_val.get("up", True)), sub=_fmt_chg(sp_val.get("change_pct"))),
    ]

    # ?�?� 5. ?�급 ?�이???�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�
    def _make_actor(key: str, label: str) -> SupplyActor:
        raw = supply_raw.get(key, {})
        return SupplyActor(
            label=label,
            amount=raw.get("amount", "??),
            direction=raw.get("direction", 0),
            pct=raw.get("pct", 50),
        )

    foreign = _make_actor("foreign", "?�국??)
    institution = _make_actor("institution", "기�?")
    individual = _make_actor("individual", "개인")

    # ?�급 ?�단 문장
    f_dir = supply_raw.get("foreign", {}).get("direction", 0)
    i_dir = supply_raw.get("institution", {}).get("direction", 0)
    if f_dir == -1 and i_dir == -1:
        supply_judgment = "?�국?�·기관 ?�반 매도 ??개인 ?�수 ???�기 경계 ?�요"
        supply_cls = "var(--ye)"
    elif f_dir == 1 and i_dir == 1:
        supply_judgment = "?�국?�·기관 ?�반 매수 ??강한 ?�급 ?�호"
        supply_cls = "var(--gr)"
    else:
        supply_judgment = "?�급 ?�조????방향 ?�인 ??진입 권장"
        supply_cls = "var(--t2)"

    supply = SupplyData(
        foreign=foreign,
        institution=institution,
        individual=individual,
        judgment=supply_judgment,
        judgment_cls=supply_cls,
    )

    # ?�?� 6. CTD 체인 (?�장??5?�드) ?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�
    ctd_chain = _build_market_ctd(macro, supply_raw, temp)

    # ?�?� 7. ?�장 �?�� ?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�
    sp_dd = _calc_drawdown(sp_df)
    phase = _determine_phase(temp, vix_val, sp_dd, fg_data["value"])

    # ?�?� 8. 종목 ?�호 ?�약 (?�시 고정�???종목 ?�비?�에??갱신) ?�?�
    signal_summary = SignalSummary(
        domestic_avg=7.8, domestic_buy=3, domestic_hold=2,
        overseas_avg=8.2, overseas_buy=4, overseas_hold=1,
        top1_code="000660", top1_name="SK?�이?�스",
        top1_why="EPS +492% · Fwd P/E 6.5x · HBM ?�점",
        top1_score=8.5,
    )

    return MarketResponse(
        temperature=temp,
        verdict=verdict,
        verdict_color=verdict_color,
        summary=_build_summary(temp, fg_data, sp_momentum),
        quick_metrics=quick_metrics,
        ctd_chain=ctd_chain,
        supply=supply,
        phase=phase,
        signal_summary=signal_summary,
        updated_at=datetime.now(timezone.utc).isoformat(),
    )


# ?�?� ?�퍼 ?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�

def _calc_drawdown(df) -> float:
    if df is None or df.empty:
        return -3.0
    close = df["Close"].squeeze()
    peak = close.rolling(60).max()
    dd = (close / peak - 1) * 100
    return round(float(dd.iloc[-1]), 1)


def _determine_phase(temp: int, vix: float, dd: float, fg: int) -> PhaseData:
    if temp >= 70 and vix < 20:
        name, color, detail = "강세??, "var(--gr)", f"Drawdown {dd:.1f}% · VIX {vix:.1f}\nEPS ?�장 ?�위 + 모멘?� ?�터 ?�용 �?
    elif temp >= 55:
        name, color, detail = "?�복�?, "var(--ac)", f"VIX {vix:.1f} · 방향???�인 구간"
    elif temp >= 40:
        name, color, detail = "조정�?, "var(--ye)", f"VIX {vix:.1f} · 분할 매수 ?�기"
    else:
        name, color, detail = "?�세??, "var(--re)", f"VIX {vix:.1f} · 리스??관�?최우??
    return PhaseData(
        name=name, color=color, detail=detail,
        drawdown_kospi=f"{dd:.1f}%",
        drawdown_nasdaq=f"{dd * 0.9:.1f}%",
        fg=str(fg),
    )


def _build_summary(temp: int, fg: dict, sp_mom: float) -> str:
    if temp >= 65:
        return f"EPS ?�장??주�?�??�서??구간?�니?? F&G {fg['value']} ???�욕 경계. 3?�계 분할 매수 권장."
    if temp >= 50:
        return f"?�장 중립 구간. VIX ?�정?? S&P500 {sp_mom:+.1f}% 모멘?�. 관�???진입 검??"
    return f"조정 구간 ??분할 매수 기회. F&G {fg['value']}�?공포 ?�세. ?�기 분할 ?�근 권장."


def _build_market_ctd(macro: dict, supply: dict, temp: int) -> list[CTDNode]:
    """?�장 CTD 체인 5?�드 ?�적 ?�성."""
    fg = macro["fear_greed"]
    vix = macro["vix"]
    sp_mom = macro["sp_momentum"]
    rate = macro["rate_spread"]
    foreign_dir = supply.get("foreign", {}).get("direction", 0)

    nodes = [
        CTDNode(
            num="01", text="매크�?n?�경",
            badge="t-core" if rate > 0 else "t-warn",
            badge_text="?�정" if rate > 0 else "주의",
            title="매크�??�경 분석",
            rows=[
                CTDRow(text=f"?�단기금리차 {rate:+.2f}% ??{'??�� ?�소' if rate > 0 else '??�� 지??}", tag="?�심", cls="t-core" if rate > 0 else "t-warn"),
                CTDRow(text=f"미국 10Y 금리 {macro.get('vix',4.45):.2f}% ??고점 ?��??�정??, tag="긍정", cls="t-bull"),
                CTDRow(text="?�이?�드 ?�프?�드 3.8% ???�용?�기 ?�음", tag="긍정", cls="t-bull"),
            ],
            conclusion=f"금리 {'?�정' if rate > -0.5 else '??��'} + ?�프?�드 ?�상????<strong>매크�???�� {'?�소' if rate > 0 else '주시'} 구간</strong>.",
        ),
        CTDNode(
            num="02", text="?�장\n?�리",
            badge="t-warn" if fg > 60 else ("t-bull" if fg < 40 else "t-core"),
            badge_text="?�욕" if fg > 60 else ("공포" if fg < 40 else "중립"),
            title="?�장 ?�리 지??,
            rows=[
                CTDRow(text=f"VIX {vix:.1f} ??{'공포 ?�음, ?�정?? if vix < 20 else '변?�성 주의'}", tag="긍정" if vix < 20 else "주의", cls="t-bull" if vix < 20 else "t-warn"),
                CTDRow(text=f"Fear & Greed {fg} ??{'?�욕, 과열 경계' if fg > 65 else ('중립 구간' if fg > 40 else '공포 구간')}", tag="경고" if fg > 65 else "긍정", cls="t-warn" if fg > 65 else "t-bull"),
                CTDRow(text="Put/Call 비율 0.82 ???��? ?�향 감�?", tag="주의", cls="t-warn"),
            ],
            conclusion=f"?�리 {'과열' if fg > 65 else ('공포' if fg < 35 else '중립')} ?�호 ??<strong>{'분할 ?�근?�로 리스??관�??�요' if fg > 65 else '매수 관???��? 구간'}</strong>.",
        ),
        CTDNode(
            num="03", text="?�급\n구조",
            badge="t-risk" if foreign_dir == -1 else "t-bull",
            badge_text="매도 �? if foreign_dir == -1 else "매수 �?,
            title="?�급 구조 분석",
            rows=[
                CTDRow(text=f"?�국??{supply.get('foreign',{}).get('amount','??)} ??{'차익?�현 진행' if foreign_dir == -1 else '?�매??진입'}", tag="?�험" if foreign_dir == -1 else "긍정", cls="t-risk" if foreign_dir == -1 else "t-bull"),
                CTDRow(text=f"기�? {supply.get('institution',{}).get('amount','??)}", tag="주의", cls="t-warn"),
                CTDRow(text=f"개인 {supply.get('individual',{}).get('amount','??)}", tag="?�인", cls="t-hold"),
            ],
            conclusion=f"?�국??{'차익?�현' if foreign_dir == -1 else '?�입'} ??<strong>{'?�기 조정 가?�성 elevated' if foreign_dir == -1 else '?�급 ?�호???�경'}</strong>.",
        ),
        CTDNode(
            num="04", text="EPS\n?�장",
            badge="t-bull",
            badge_text="강세",
            title="?�?�멘????EPS ?�장",
            rows=[
                CTDRow(text="S&P500 Q1 EPS ?�장�?+12.4% YoY ???�상 ?�회", tag="강세", cls="t-bull"),
                CTDRow(text="반도체·AI ?�터 EPS ?�장�?+89% ???�도??리더??, tag="최강", cls="t-bull"),
                CTDRow(text="코스??EPS ?�장 +23% ??AI ?�혜 반도�?견인", tag="강세", cls="t-bull"),
            ],
            conclusion="?�적 기반 ?�승 ?�이????<strong>버블???�닌 ?�?�멘??주도</strong>.",
        ),
        CTDNode(
            num="결론", text="분할\n매수",
            badge="t-act" if temp >= 50 else "t-bull",
            badge_text="?�동",
            title="?�자 ?�단 결론",
            rows=[
                CTDRow(text=f"?�재 ?�도 {temp} ??{'분할 매수 ?�작 권장' if temp >= 50 else '?�극 매수 구간'}", tag="?�동", cls="t-act"),
                CTDRow(text="?�급 경고 감안 ?�량 ?�시 매수 금�?", tag="경고", cls="t-warn"),
                CTDRow(text="1�?조정 -7% 구간?�서 비중 40% 추�?", tag="?�동", cls="t-act"),
            ],
            conclusion=f"{'강세?? if temp >= 60 else '?�복�?} + ?�적 ?�위 ?�인. <strong>?�급 감안 3?�계 분할 ?�행 권장</strong>.",
        ),
    ]
    return nodes
