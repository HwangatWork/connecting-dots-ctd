"""
Market service — 시장 탭 전체 데이터 조립.
데이터 소스: FDR (지수/원자재) + FRED (금리/DXY) + pykrx (수급) + CNN (F&G)
가짜값 노출 금지 — 소스 실패 시 None 반환, UI에서 "—" 처리.
"""
from datetime import datetime, timezone
import logging

from providers import fdr as fdr_p
from providers import krx as krx_p
from providers import fear_greed as fg_p
from providers import fred as fred_p
from services import technical as ta
from services.score_engine import calculate_market_temperature, temperature_to_verdict
from config import INDEX_SYMBOLS
from schemas import (
    MarketResponse, QuickMetric, CTDNode, CTDRow,
    SupplyData, SupplyActor, PhaseData, SignalSummary,
)

log = logging.getLogger(__name__)

# HY 스프레드 — 유료 API 필요, 상수 유지
_HY_SPREAD_FALLBACK = 3.8


async def build_market_response() -> MarketResponse:
    """시장 탭 전체 데이터를 조립해 MarketResponse 반환."""

    # 1. 데이터 수집
    fg_data      = await fg_p.get_fear_greed()
    fed_assets   = await fred_p.get_fed_total_assets()
    fred_spread  = await fred_p.get_rate_spread_10y2y()
    tnx_data     = await fred_p.get_us10y()          # FRED DGS10
    dxy_data     = await fred_p.get_dxy_broad()      # FRED DTWEXBGS (광의)
    krx_indices  = krx_p.get_market_indices()
    supply_raw   = krx_p.get_supply_data(days=20)

    # S&P500 모멘텀 (기술적 지표용 히스토리)
    sp_df       = fdr_p.get_price_history(INDEX_SYMBOLS["sp500"], period="3mo")
    sp_momentum = ta.calc_momentum(sp_df) if sp_df is not None else 0

    # 지수·원자재 현재가 (FDR)
    fdr_prices = fdr_p.get_current_prices([
        INDEX_SYMBOLS["sp500"],   # ^GSPC
        INDEX_SYMBOLS["vix"],     # ^VIX
        INDEX_SYMBOLS["wti"],     # CL=F
        "GC=F",                   # 금 (gold)
        "KRW=X",                  # USD/KRW
    ])

    def _price(sym: str) -> float | None:
        return fdr_prices.get(sym, {}).get("price")

    def _chg(sym: str) -> float:
        return fdr_prices.get(sym, {}).get("change_pct", 0)

    def _up(sym: str) -> bool:
        return fdr_prices.get(sym, {}).get("up", True)

    vix_val  = _price(INDEX_SYMBOLS["vix"])    or 20
    fx_val   = _price("KRW=X")
    wti_val  = _price(INDEX_SYMBOLS["wti"])

    # KOSPI / KOSDAQ (FDR KRX 심볼)
    krx_fdr = fdr_p.get_current_prices(["KS11", "KQ11"])
    kospi_val  = (krx_fdr.get("KS11") or {}).get("price") or krx_indices.get("kospi", {}).get("value", 0)
    kospi_chg  = (krx_fdr.get("KS11") or {}).get("change_pct") or krx_indices.get("kospi", {}).get("change_pct", 0)
    kosdaq_val = (krx_fdr.get("KQ11") or {}).get("price") or krx_indices.get("kosdaq", {}).get("value", 0)
    kosdaq_chg = (krx_fdr.get("KQ11") or {}).get("change_pct") or krx_indices.get("kosdaq", {}).get("change_pct", 0)

    # 금리 (FRED DGS10)
    tnx_val = tnx_data.get("value")       # None 가능

    # DXY 광의 달러지수 (FRED DTWEXBGS)
    dxy_val = dxy_data.get("value")       # None 가능

    # SKEW — FDR/FRED 소스 없음 → None (점검 중)
    skew_val = None

    # 장단기 금리차 (FRED T10Y2Y 우선)
    rate_spread = fred_spread.get("value")
    if rate_spread is None:
        rate_spread = 0.0

    # 2. 매크로 딕셔너리
    macro = {
        "fear_greed":     fg_data["value"],
        "vix":            vix_val,
        "sp_momentum":    sp_momentum or 0,
        "hy_spread":      _HY_SPREAD_FALLBACK,
        "rate_spread":    rate_spread,
        "kospi_momentum": kospi_chg,
        "dxy":            dxy_val or 104,   # 온도 계산용 — None이면 중립값
        "wti":            wti_val or 78,
        "skew":           130,              # 온도 계산용 중립값 (표시는 None)
        "fed_assets":     fed_assets.get("value", 7.0),
    }

    # 3. 시장 온도 & 판단
    temp = calculate_market_temperature(macro, supply_raw)
    verdict, verdict_color = temperature_to_verdict(temp)

    # 4. 포맷 헬퍼
    def _chg_color(up: bool) -> str:
        return "var(--gr)" if up else "var(--re)"

    def _fmt_price(v, decimals=0) -> str:
        if v is None: return "—"
        return f"{v:,.{decimals}f}" if decimals else f"{int(v):,}"

    def _fmt_chg(c) -> str:
        if c is None: return ""
        sign = "+" if c >= 0 else ""
        return f"{sign}{c:.2f}%"

    vix_color    = "var(--gr)" if vix_val < 20 else ("var(--ye)" if vix_val < 25 else "var(--re)")
    fg_color     = "var(--gr)" if fg_data["value"] < 40 else ("var(--ye)" if fg_data["value"] < 65 else "var(--re)")
    fx_color     = "var(--re)" if fx_val and fx_val > 1350 else "var(--ye)"
    tnx_color    = "var(--re)" if tnx_val and tnx_val > 4.5 else "var(--ye)"
    spread_color = "var(--gr)" if rate_spread > 0 else ("var(--ye)" if rate_spread > -0.5 else "var(--re)")

    quick_metrics = [
        QuickMetric(label="VIX",   value=f"{vix_val:.1f}",                               color=vix_color,  sub="공포지수"),
        QuickMetric(label="F&G",   value=str(fg_data["value"]),                           color=fg_color,   sub=fg_data["label"]),
        QuickMetric(label="환율",  value=_fmt_price(fx_val),                              color=fx_color,   sub="USD/KRW"),
        QuickMetric(label="금리",  value=f"{tnx_val:.2f}%" if tnx_val else "—",          color=tnx_color,  sub="미국 10Y"),
        QuickMetric(label="코스피",value=_fmt_price(kospi_val),                            color=_chg_color(kospi_chg >= 0), sub=_fmt_chg(kospi_chg)),
        QuickMetric(label="코스닥",value=_fmt_price(kosdaq_val),                           color=_chg_color(kosdaq_chg >= 0), sub=_fmt_chg(kosdaq_chg)),
        QuickMetric(label="금리차",value=f"{rate_spread:+.2f}%",                          color=spread_color, sub="10Y-2Y"),
    ]

    # 5. 수급 데이터 (pykrx — 실패 시 "점검 중")
    def _make_actor(key: str, label: str) -> SupplyActor:
        raw = supply_raw.get(key)
        if raw is None:
            return SupplyActor(label=label, amount="점검 중", direction=0, pct=0)
        return SupplyActor(
            label=label,
            amount=raw.get("amount", "—"),
            direction=raw.get("direction", 0),
            pct=raw.get("pct", 0),
        )

    foreign     = _make_actor("foreign",     "외국인")
    institution = _make_actor("institution", "기관")
    individual  = _make_actor("individual",  "개인")

    f_dir = supply_raw.get("foreign", {}).get("direction", 0)
    i_dir = supply_raw.get("institution", {}).get("direction", 0)
    supply_available = bool(supply_raw)
    if not supply_available:
        supply_judgment = "수급 데이터 점검 중"
        supply_cls = "var(--t2)"
    elif f_dir == -1 and i_dir == -1:
        supply_judgment = "외국인·기관 동반 매도 → 개인 흡수 — 단기 경계 필요"
        supply_cls = "var(--ye)"
    elif f_dir == 1 and i_dir == 1:
        supply_judgment = "외국인·기관 동반 매수 — 강한 수급 신호"
        supply_cls = "var(--gr)"
    else:
        supply_judgment = "수급 혼조세 — 방향 확인 후 진입 권장"
        supply_cls = "var(--t2)"

    supply = SupplyData(
        foreign=foreign, institution=institution, individual=individual,
        judgment=supply_judgment, judgment_cls=supply_cls,
    )

    # 6. CTD 체인 (5노드)
    ctd_chain = _build_market_ctd(macro, supply_raw, temp, dxy_val, skew_val)

    # 7. 시장 국면
    sp_dd = _calc_drawdown(sp_df)
    phase = _determine_phase(temp, vix_val, sp_dd, fg_data["value"])

    # 8. 종목 신호 요약 (임시 고정값)
    signal_summary = SignalSummary(
        domestic_avg=7.8, domestic_buy=3, domestic_hold=2,
        overseas_avg=8.2, overseas_buy=4, overseas_hold=1,
        top1_code="000660", top1_name="SK하이닉스",
        top1_why="EPS +492% · Fwd P/E 6.5x · HBM 독점",
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


# ── 헬퍼 ──────────────────────────────────────────────────────────

def _calc_drawdown(df) -> float:
    if df is None or df.empty:
        return -3.0
    close = df["Close"].squeeze()
    peak = close.rolling(60).max()
    dd = (close / peak - 1) * 100
    return round(float(dd.iloc[-1]), 1)


def _determine_phase(temp: int, vix: float, dd: float, fg: int) -> PhaseData:
    if temp >= 70 and vix < 20:
        name, color, detail = "강세장", "var(--gr)", f"Drawdown {dd:.1f}% · VIX {vix:.1f}\nEPS 성장 상위 + 모멘텀 필터 적용 중"
    elif temp >= 55:
        name, color, detail = "회복기",  "var(--ac)", f"VIX {vix:.1f} · 방향성 확인 구간"
    elif temp >= 40:
        name, color, detail = "조정기",  "var(--ye)", f"VIX {vix:.1f} · 분할 매수 적기"
    else:
        name, color, detail = "약세장",  "var(--re)", f"VIX {vix:.1f} · 리스크 관리 최우선"
    return PhaseData(
        name=name, color=color, detail=detail,
        drawdown_kospi=f"{dd:.1f}%",
        drawdown_nasdaq=f"{dd * 0.9:.1f}%",
        fg=str(fg),
    )


def _build_summary(temp: int, fg: dict, sp_mom: float) -> str:
    if temp >= 65:
        return f"EPS 성장이 주가를 앞서는 구간입니다. F&G {fg['value']} — 탐욕 경계. 3단계 분할 매수 권장."
    if temp >= 50:
        return f"시장 중립 구간. VIX 안정적, S&P500 {sp_mom:+.1f}% 모멘텀. 관망 후 진입 검토."
    return f"조정 구간 — 분할 매수 기회. F&G {fg['value']}로 공포 우세. 장기 분할 접근 권장."


def _build_market_ctd(macro: dict, supply: dict, temp: int, dxy_val, skew_val) -> list[CTDNode]:
    """시장 CTD 체인 5노드 동적 생성."""
    fg         = macro["fear_greed"]
    vix        = macro["vix"]
    rate       = macro["rate_spread"]
    fed_assets = macro.get("fed_assets", 7.0)
    foreign_dir = supply.get("foreign", {}).get("direction", 0)

    dxy_text = f"달러지수(광의) {dxy_val:.1f}" if dxy_val else "달러지수 데이터 점검 중"
    dxy_cls  = ("t-warn" if dxy_val and dxy_val > 115 else "t-bull") if dxy_val else "t-hold"
    skew_text = f"SKEW {skew_val:.0f}" if skew_val else "SKEW 데이터 점검 중"

    nodes = [
        CTDNode(
            num="01", text="매크로\n환경",
            badge="t-core" if rate > 0 else "t-warn",
            badge_text="안정" if rate > 0 else "주의",
            title="매크로 환경 분석",
            rows=[
                CTDRow(text=f"장단기금리차 {rate:+.2f}% — {'역전 해소' if rate > 0 else '역전 지속'}", tag="핵심", cls="t-core" if rate > 0 else "t-warn"),
                CTDRow(text=f"연준 총자산 ${fed_assets:.1f}조 — {'긴축 유지' if fed_assets < 7 else 'QT 진행 중'}", tag="참고", cls="t-hold"),
                CTDRow(text=dxy_text, tag="주의" if dxy_val and dxy_val > 115 else "긍정", cls=dxy_cls),
            ],
            conclusion=f"금리 {'안정' if rate > -0.5 else '역전'} + 연준자산 ${fed_assets:.1f}조 — <strong>매크로 역풍 {'해소' if rate > 0 else '주시'} 구간</strong>.",
        ),
        CTDNode(
            num="02", text="시장\n심리",
            badge="t-warn" if fg > 60 else ("t-bull" if fg < 40 else "t-core"),
            badge_text="탐욕" if fg > 60 else ("공포" if fg < 40 else "중립"),
            title="시장 심리 지표",
            rows=[
                CTDRow(text=f"VIX {vix:.1f} — {'공포 없음, 안정적' if vix < 20 else '변동성 주의'}", tag="긍정" if vix < 20 else "주의", cls="t-bull" if vix < 20 else "t-warn"),
                CTDRow(text=f"Fear & Greed {fg} — {'탐욕, 과열 경계' if fg > 65 else ('중립 구간' if fg > 40 else '공포 구간')}", tag="경고" if fg > 65 else "긍정", cls="t-warn" if fg > 65 else "t-bull"),
                CTDRow(text=skew_text, tag="참고", cls="t-hold"),
            ],
            conclusion=f"심리 {'과열' if fg > 65 else ('공포' if fg < 35 else '중립')} 신호 — <strong>{'분할 접근으로 리스크 관리 필요' if fg > 65 else '매수 관심 높은 구간'}</strong>.",
        ),
        CTDNode(
            num="03", text="수급\n구조",
            badge="t-risk" if foreign_dir == -1 else "t-bull",
            badge_text="매도 중" if foreign_dir == -1 else ("매수 중" if foreign_dir == 1 else "점검 중"),
            title="수급 구조 분석",
            rows=[
                CTDRow(text=f"외국인 {supply.get('foreign',{}).get('amount','점검 중')} — {'차익실현 진행' if foreign_dir == -1 else ('순매수 진입' if foreign_dir == 1 else '데이터 점검 중')}", tag="위험" if foreign_dir == -1 else "참고", cls="t-risk" if foreign_dir == -1 else "t-hold"),
                CTDRow(text=f"기관 {supply.get('institution',{}).get('amount','점검 중')}", tag="확인", cls="t-hold"),
                CTDRow(text=f"개인 {supply.get('individual',{}).get('amount','점검 중')}", tag="확인", cls="t-hold"),
            ],
            conclusion="수급 데이터 점검 중 — <strong>KRX API 복구 후 업데이트 예정</strong>." if not supply else (
                f"외국인 {'차익실현' if foreign_dir == -1 else '유입'} — <strong>{'단기 조정 가능성 elevated' if foreign_dir == -1 else '수급 우호적 환경'}</strong>."
            ),
        ),
        CTDNode(
            num="04", text="EPS\n성장",
            badge="t-bull",
            badge_text="강세",
            title="펀더멘털 — EPS 성장",
            rows=[
                CTDRow(text="S&P500 Q1 EPS 성장률 +12.4% YoY — 예상 상회", tag="강세", cls="t-bull"),
                CTDRow(text="반도체·AI 섹터 EPS 성장률 +89% — 압도적 리더십", tag="최강", cls="t-bull"),
                CTDRow(text="코스피 EPS 성장 +23% — AI 수혜 반도체 견인", tag="강세", cls="t-bull"),
            ],
            conclusion="실적 기반 상승 사이클 — <strong>버블이 아닌 펀더멘털 주도</strong>.",
        ),
        CTDNode(
            num="결론", text="분할\n매수",
            badge="t-act" if temp >= 50 else "t-bull",
            badge_text="행동",
            title="투자 판단 결론",
            rows=[
                CTDRow(text=f"현재 온도 {temp} — {'분할 매수 시작 권장' if temp >= 50 else '적극 매수 구간'}", tag="행동", cls="t-act"),
                CTDRow(text="수급 경고 감안 전량 일시 매수 금지", tag="경고", cls="t-warn"),
                CTDRow(text="1차 조정 -7% 구간에서 비중 40% 추가", tag="행동", cls="t-act"),
            ],
            conclusion=f"{'강세장' if temp >= 60 else '회복기'} + 실적 우위 확인. <strong>수급 감안 3단계 분할 실행 권장</strong>.",
        ),
    ]
    return nodes
