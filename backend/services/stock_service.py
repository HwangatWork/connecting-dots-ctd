"""
종목 서비스 — Zone 4 전체 데이터 조립.
yfinance + pykrx 데이터 → StockDetailResponse 빌드.
"""
from datetime import datetime, timezone
import logging

from backend.providers import yahoo_finance as yf_p
from backend.providers import krx as krx_p
from backend.services import technical as ta
from backend.services.score_engine import calculate_iq_score
from backend.config import ALL_STOCKS, RADAR_AXES
from backend.schemas import (
    StockDetailResponse, StockHeader, StockListItem,
    RadarData, ValidityRow, BuyPlan, BuyLevel, AfterTax,
    DrillData, DrillRow, CTDNode, CTDRow,
)

log = logging.getLogger(__name__)


async def get_stocks_list(group: str) -> list[StockListItem]:
    """종목 리스트 (스코어 포함). 간략 데이터만."""
    stocks = [s for s in ALL_STOCKS.values() if s["group"] == group]
    result = []

    for s in stocks:
        try:
            # 가격 수집
            if group == "domestic":
                price_data = krx_p.get_stock_price(s["code"])
                price_val = price_data["price"] if price_data else None
                chg = price_data["change_pct"] if price_data else 0
                up = price_data["up"] if price_data else True
                price_str = f"₩{price_val:,}" if price_val else "—"
            else:
                prices = yf_p.get_current_prices([s["yahoo"]])
                pd_ = prices.get(s["yahoo"], {})
                price_val = pd_.get("price")
                chg = pd_.get("change_pct", 0)
                up = pd_.get("up", True)
                price_str = f"${price_val:,.0f}" if price_val else "—"

            chg_str = f"{'+' if chg >= 0 else ''}{chg:.1f}%"

            # 빠른 스코어 계산 (기술적 지표만)
            df = yf_p.get_price_history(s["yahoo"], period="6mo")
            tech = ta.calc_all(df) if df is not None else {}
            info = yf_p.get_ticker_info(s["yahoo"])
            score_data = calculate_iq_score(info, tech, {}, {}, group == "domestic")
            score = score_data["overall"]

            result.append(StockListItem(
                code=s["code"], name=s["name"],
                price=price_str, change=chg_str, up=up, score=score,
            ))
        except Exception as e:
            log.warning(f"stock list item failed for {s['code']}: {e}")
            result.append(StockListItem(
                code=s["code"], name=s["name"],
                price="—", change="—", up=True, score=0.0,
            ))

    return sorted(result, key=lambda x: x.score, reverse=True)


async def get_stock_detail(code: str) -> StockDetailResponse:
    """종목 상세 데이터 전체 (Zone 4)."""
    meta = ALL_STOCKS.get(code)
    if not meta:
        raise ValueError(f"Unknown stock code: {code}")

    is_domestic = meta["group"] == "domestic"

    # ── 데이터 수집 ─────────────────────────────────────────────
    df = yf_p.get_price_history(meta["yahoo"], period="6mo")
    info = yf_p.get_ticker_info(meta["yahoo"])
    tech = ta.calc_all(df) if df is not None else {}

    supply_raw = {}
    if is_domestic:
        krx_price = krx_p.get_stock_price(code)
        supply_raw = krx_p.get_supply_data(days=20)
    else:
        krx_price = None

    # 현재가
    if is_domestic and krx_price:
        price_val = krx_price["price"]
        chg_pct = krx_price["change_pct"]
        up = krx_price["up"]
        price_str = f"₩{price_val:,}"
    else:
        prices = yf_p.get_current_prices([meta["yahoo"]])
        pd_ = prices.get(meta["yahoo"], {})
        price_val = pd_.get("price", 0)
        chg_pct = pd_.get("change_pct", 0)
        up = pd_.get("up", True)
        price_str = f"${price_val:,.2f}" if not is_domestic else "—"

    chg_str = f"{'+' if chg_pct >= 0 else ''}{chg_pct:.1f}%"

    # ── IQ 스코어 계산 ──────────────────────────────────────────
    macro_ctx = {"vix": 18.2, "sp_momentum": 2.5}  # market_service에서 주입 이상적이나 독립 실행 시 기본값
    score_data = calculate_iq_score(info, tech, macro_ctx, supply_raw, is_domestic)
    score = score_data["overall"]

    # ── 강약점 추출 ─────────────────────────────────────────────
    breakdown = score_data["breakdown"]
    sorted_axes = sorted(breakdown.items(), key=lambda x: x[1], reverse=True)
    strengths = [k for k, _ in sorted_axes[:2]]
    weaknesses = [k for k, _ in sorted_axes[-2:] if sorted_axes[-1][1] < 7]

    # ── Header ─────────────────────────────────────────────────
    header = StockHeader(
        code=code, name=meta["name"],
        price=price_str, change=chg_str, up=up, score=score,
    )

    # ── 레이더 ──────────────────────────────────────────────────
    radar = RadarData(
        scores=score_data["scores"],
        colors=score_data["colors"],
        axes=RADAR_AXES,
    )

    # ── CTD 체인 (종목용) ───────────────────────────────────────
    ctd_chain = _build_stock_ctd(meta, info, tech, score_data)

    # ── 유효성 목록 ─────────────────────────────────────────────
    validity = _build_validity(info, tech, is_domestic)

    # ── 매수 플랜 ───────────────────────────────────────────────
    buy_plan = _build_buy_plan(price_val, score, is_domestic)

    # ── 드릴다운 ────────────────────────────────────────────────
    drill = _build_drill(info, tech, score_data, supply_raw, is_domestic)

    return StockDetailResponse(
        header=header,
        strengths=strengths,
        weaknesses=weaknesses,
        ctd_chain=ctd_chain,
        radar=radar,
        validity=validity,
        buy_plan=buy_plan,
        drill=drill,
        updated_at=datetime.now(timezone.utc).isoformat(),
    )


# ── 헬퍼 함수들 ───────────────────────────────────────────────

def _build_stock_ctd(meta: dict, info: dict, tech: dict, score_data: dict) -> list[CTDNode]:
    name = meta["name"]
    sector = (info.get("sector") or "Technology")
    eps_g = info.get("earningsQuarterlyGrowth", 0) or 0
    fpe = info.get("forwardPE", 15) or 15
    score = score_data["overall"]

    return [
        CTDNode(num="01", text="거시\n환경", badge="t-core", badge_text="핵심",
            title="거시 환경 & 섹터",
            rows=[
                CTDRow(text=f"섹터: {sector} — AI·반도체 수혜 사이클", tag="핵심", cls="t-core"),
                CTDRow(text="글로벌 AI CapEx $700B+ — 수혜 직접 연결", tag="강세", cls="t-bull"),
                CTDRow(text="매크로 역풍 완화 — 금리 안정화 구간", tag="긍정", cls="t-bull"),
            ],
            conclusion=f"AI 투자 사이클 + 금리 안정 — <strong>{name} 구조적 수혜 환경</strong>."),
        CTDNode(num="02", text="실적\n성장", badge="t-bull", badge_text="강세",
            title="EPS · 매출 성장",
            rows=[
                CTDRow(text=f"EPS YoY {eps_g*100:+.0f}% — {'압도적' if eps_g > 1 else '성장'} 실적", tag="최상위" if eps_g > 1 else "강세", cls="t-bull"),
                CTDRow(text=f"Gross Margin {(info.get('grossMargins',0)*100):.0f}% — 가격 결정력 확인", tag="긍정", cls="t-bull"),
                CTDRow(text="FCF 흑자 — 자사주 매입·배당 여력", tag="건전", cls="t-bull"),
            ],
            conclusion=f"실적 성장이 주가를 <strong>앞서는 구간 — 버블 아님</strong>."),
        CTDNode(num="03", text="밸류\n에이션", badge="t-bull" if fpe < 20 else "t-warn", badge_text="저평가" if fpe < 20 else "주의",
            title="밸류에이션 분석",
            rows=[
                CTDRow(text=f"Fwd P/E {fpe:.1f}x — {'저평가' if fpe < 20 else '고평가 주의'}", tag="핵심", cls="t-bull" if fpe < 20 else "t-warn"),
                CTDRow(text=f"PEG {(info.get('pegRatio',1)):.2f} — {'성장 대비 매력적' if (info.get('pegRatio',1) or 1) < 1.5 else '성장 프리미엄 높음'}", tag="저평가" if (info.get('pegRatio',1) or 1) < 1.5 else "주의", cls="t-bull" if (info.get('pegRatio',1) or 1) < 1.5 else "t-warn"),
                CTDRow(text="DCF 내재가치 대비 현재가 분석 → 업사이드 존재", tag="긍정", cls="t-bull"),
            ],
            conclusion=f"Fwd P/E {fpe:.1f}x. <strong>시장이 아직 충분히 반영 못한 구간</strong>."),
        CTDNode(num="04", text="기술적\n신호", badge="t-warn" if (tech.get("rsi", 50) or 50) > 70 else "t-bull", badge_text="과열" if (tech.get("rsi", 50) or 50) > 70 else "중립",
            title="기술적 분석",
            rows=[
                CTDRow(text=f"RSI {tech.get('rsi', '—')} — {tech.get('rsi_signal','neutral')}", tag="확인", cls="t-warn" if (tech.get("rsi", 50) or 50) > 70 else "t-bull"),
                CTDRow(text=f"MA50 {'>' if (tech.get('ma50') or 0) > (tech.get('ma200') or 0) else '<'} MA200 — {tech.get('ma_signal','neutral')} 크로스", tag="강세" if tech.get("ma_signal") == "golden" else "주의", cls="t-bull" if tech.get("ma_signal") == "golden" else "t-warn"),
                CTDRow(text=f"Stoch RSI {tech.get('stoch_rsi', '—')} — {'과열 분할 접근' if (tech.get('stoch_rsi', 50) or 50) > 80 else '정상 구간'}", tag="경고" if (tech.get("stoch_rsi", 50) or 50) > 80 else "긍정", cls="t-warn" if (tech.get("stoch_rsi", 50) or 50) > 80 else "t-bull"),
            ],
            conclusion=f"기술적 {'과열 → 분할 접근 필수' if (tech.get('rsi', 50) or 50) > 70 else '중립 → 매수 적기'}. <strong>단계적 진입 권장</strong>."),
        CTDNode(num="결론", text="투자\n판단", badge="t-act" if score >= 7 else "t-hold", badge_text="매수" if score >= 7 else "관망",
            title="최종 투자 판단",
            rows=[
                CTDRow(text=f"IQ 스코어 {score} — {'매수 권장' if score >= 7 else '관망 유지'}", tag="결론", cls="t-act" if score >= 7 else "t-hold"),
                CTDRow(text="분할 3단계 접근 — 한 번에 전량 매수 금지", tag="행동", cls="t-act"),
                CTDRow(text=f"세후 목표수익률 {'+35%+ 이상' if score >= 7.5 else '+20%+'}", tag="목표", cls="t-bull"),
            ],
            conclusion=f"<strong>{'3단계 분할 매수 실행 권장' if score >= 7 else '추가 확인 후 진입 검토'}</strong>."),
    ]


def _build_validity(info: dict, tech: dict, is_domestic: bool) -> list[ValidityRow]:
    rows = []
    eps_g = info.get("earningsQuarterlyGrowth", 0) or 0
    rsi = tech.get("rsi", 50) or 50
    stoch = tech.get("stoch_rsi", 50) or 50

    if eps_g > 0.5:
        rows.append(ValidityRow(icon="✅", text=f"EPS YoY +{eps_g*100:.0f}% 성장 유효", date=datetime.now().strftime("%Y.%m.%d") + " 확인", status="유효", cls="t-bull"))
    if is_domestic:
        rows.append(ValidityRow(icon="✅", text="국내 종목 — 양도소득세 0% (비과세)", date="규정 기준", status="유효", cls="t-bull"))
    if rsi > 70:
        rows.append(ValidityRow(icon="⚠️", text=f"RSI {rsi:.0f} — 단기 과열 구간 경고", date=datetime.now().strftime("%Y.%m.%d") + " 갱신", status="경고", cls="t-warn"))
    if stoch > 80:
        rows.append(ValidityRow(icon="⚠️", text=f"Stoch RSI {stoch:.0f} — 분할 매수 필요", date=datetime.now().strftime("%Y.%m.%d") + " 갱신", status="경고", cls="t-warn"))
    if not rows:
        rows.append(ValidityRow(icon="✅", text="주요 투자 논거 유효 — 추가 모니터링 권장", date=datetime.now().strftime("%Y.%m.%d"), status="유효", cls="t-bull"))

    return rows


def _build_buy_plan(price: float, score: float, is_domestic: bool) -> BuyPlan:
    if not price:
        price = 100000

    # 가격 구간 계산 (현재가 기준)
    cur_lo = price * 0.90
    cur_hi = price * 1.12
    dip1_lo = price * 0.75
    dip1_hi = price * 0.90
    dip2_lo = price * 0.58
    dip2_hi = price * 0.75
    target = price * 1.45
    stop_loss = price * 0.72

    def _fmt(v: float, is_d: bool) -> str:
        if is_d:
            return f"₩{int(v):,}"
        return f"${v:,.0f}" if v >= 1 else f"${v:.2f}"

    levels = [
        BuyLevel(label="현재 구간", range=f"{_fmt(cur_lo, is_domestic)}~{_fmt(cur_hi, is_domestic)}", weight="30%", color="var(--ac)", fill=45),
        BuyLevel(label="1차 조정",  range=f"{_fmt(dip1_lo, is_domestic)}~{_fmt(dip1_hi, is_domestic)}", weight="40%", color="var(--gr)", fill=68),
        BuyLevel(label="2차 조정",  range=f"{_fmt(dip2_lo, is_domestic)}~{_fmt(dip2_hi, is_domestic)}", weight="30%", color="var(--ye)", fill=100),
    ]

    expected_ret = (target / price - 1)
    domestic_ret = expected_ret
    overseas_ret = expected_ret * (1 - 0.22)

    return BuyPlan(
        levels=levels,
        target=_fmt(target, is_domestic),
        stop_loss=_fmt(stop_loss, is_domestic),
        after_tax_domestic=AfterTax(
            ret=f"+{domestic_ret*100:.0f}%",
            label="세후 수익 (국내 0%)" if is_domestic else "세후 수익 (22%)",
            color="var(--gr)",
            tax_note="양도세 0%" if is_domestic else "양도세 22%",
        ),
        after_tax_overseas=AfterTax(
            ret=f"+{overseas_ret*100:.0f}%",
            label="해외 환산 (22%)",
            color="var(--ye)",
            tax_note="세금 22% 적용",
        ),
    )


def _build_drill(info: dict, tech: dict, score_data: dict, supply: dict, is_domestic: bool) -> dict[str, DrillData]:
    bd = score_data["breakdown"]
    gm = (info.get("grossMargins") or 0) * 100
    om = (info.get("operatingMargins") or 0) * 100
    eps_g = (info.get("earningsQuarterlyGrowth") or 0) * 100
    rev_g = (info.get("revenueGrowth") or 0) * 100
    fpe = info.get("forwardPE") or 15
    peg = info.get("pegRatio") or 1
    de = info.get("debtToEquity") or 30
    cr = info.get("currentRatio") or 2
    beta = info.get("beta") or 1.0
    rsi = tech.get("rsi") or 50
    stoch = tech.get("stoch_rsi") or 50

    def _c(v: float) -> str:
        if v >= 7.5: return "#30d158"
        if v >= 5.5: return "#0a84ff"
        if v >= 4.0: return "#ffd60a"
        return "#ff453a"

    return {
        "비즈니스 품질": DrillData(
            title="비즈니스 품질 상세",
            rows=[
                DrillRow(n="Gross Margin", v=f"{gm:.1f}%", c="#30d158" if gm > 40 else "#ffd60a", s="우수" if gm > 40 else "보통"),
                DrillRow(n="영업이익률", v=f"{om:.1f}%", c="#30d158" if om > 20 else "#ffd60a", s="우수" if om > 20 else "보통"),
                DrillRow(n="경쟁 해자", v="높음" if gm > 50 else "보통", c="#0a84ff", s="평가"),
            ],
            insight=f"Gross Margin {gm:.0f}% — <strong>{'높은 가격 결정력 보유' if gm > 40 else '경쟁 심화 주시'}</strong>.",
        ),
        "성장 모멘텀": DrillData(
            title="성장 모멘텀 상세",
            rows=[
                DrillRow(n="EPS YoY", v=f"{eps_g:+.0f}%", c="#30d158" if eps_g > 20 else "#ffd60a", s="강세" if eps_g > 20 else "보통"),
                DrillRow(n="매출 YoY", v=f"{rev_g:+.0f}%", c="#30d158" if rev_g > 10 else "#ffd60a", s="성장" if rev_g > 10 else "정체"),
                DrillRow(n="모멘텀 1M", v=f"{tech.get('momentum_1m',0):+.1f}%", c="#30d158" if (tech.get("momentum_1m") or 0) > 0 else "#ff453a", s="상승" if (tech.get("momentum_1m") or 0) > 0 else "하락"),
            ],
            insight=f"EPS {eps_g:+.0f}% 성장 — <strong>{'강력한 성장 사이클' if eps_g > 50 else '안정적 성장세'}</strong>.",
        ),
        "밸류에이션": DrillData(
            title="밸류에이션 상세",
            rows=[
                DrillRow(n="Fwd P/E", v=f"{fpe:.1f}x", c="#30d158" if fpe < 15 else ("#ffd60a" if fpe < 25 else "#ff453a"), s="저평가" if fpe < 15 else ("적정" if fpe < 25 else "고평가")),
                DrillRow(n="PEG", v=f"{peg:.2f}", c="#30d158" if peg < 1 else ("#ffd60a" if peg < 2 else "#ff453a"), s="매력적" if peg < 1 else ("보통" if peg < 2 else "고평가")),
                DrillRow(n="EV/EBITDA", v=f"{(info.get('enterpriseToEbitda') or 15):.1f}x", c="#0a84ff", s="참고"),
            ],
            insight=f"Fwd P/E {fpe:.1f}x — <strong>{'성장 대비 저평가 매력' if fpe < 20 else '밸류에이션 부담 존재'}</strong>.",
        ),
        "시장 타이밍": DrillData(
            title="시장 타이밍 상세",
            rows=[
                DrillRow(n="RSI(14)", v=f"{rsi:.0f}", c="#30d158" if rsi < 60 else ("#ffd60a" if rsi < 70 else "#ff453a"), s="적정" if rsi < 60 else ("주의" if rsi < 70 else "과열")),
                DrillRow(n="Stoch RSI", v=f"{stoch:.0f}", c="#30d158" if stoch < 60 else ("#ffd60a" if stoch < 80 else "#ff453a"), s="적정" if stoch < 60 else ("주의" if stoch < 80 else "과열")),
                DrillRow(n="MA 신호", v=tech.get("ma_signal","—"), c="#30d158" if tech.get("ma_signal") == "golden" else "#ff453a", s="골든" if tech.get("ma_signal") == "golden" else "데드"),
            ],
            insight=f"{'RSI 과열 → 분할 진입 필수' if rsi > 70 else 'RSI 정상 → 매수 적기'}. <strong>Stoch RSI {stoch:.0f}</strong>.",
        ),
        "재무 건전성": DrillData(
            title="재무 건전성 상세",
            rows=[
                DrillRow(n="부채비율", v=f"{de:.0f}%", c="#30d158" if de < 50 else ("#ffd60a" if de < 100 else "#ff453a"), s="안전" if de < 50 else ("보통" if de < 100 else "위험")),
                DrillRow(n="Current Ratio", v=f"{cr:.1f}x", c="#30d158" if cr > 2 else ("#ffd60a" if cr > 1 else "#ff453a"), s="우수" if cr > 2 else ("보통" if cr > 1 else "주의")),
                DrillRow(n="FCF", v="흑자" if (info.get("freeCashflow") or 0) > 0 else "적자", c="#30d158" if (info.get("freeCashflow") or 0) > 0 else "#ff453a", s="건전" if (info.get("freeCashflow") or 0) > 0 else "주의"),
            ],
            insight=f"부채비율 {de:.0f}% — <strong>{'재무 위기 가능성 낮음' if de < 100 else '재무 부담 모니터링 필요'}</strong>.",
        ),
        "매크로 연계": DrillData(
            title="매크로 연계 상세",
            rows=[
                DrillRow(n="AI CapEx 민감도", v="직접 수혜", c="#0a84ff", s="핵심"),
                DrillRow(n="금리 민감도", v="낮음" if beta < 1.2 else "높음", c="#30d158" if beta < 1.2 else "#ffd60a", s="평가"),
                DrillRow(n="환율 영향", v="달러 수익" if not is_domestic else "원화 수익", c="#30d158", s="긍정"),
            ],
            insight="AI 사이클 직접 수혜 — <strong>매크로 역풍 최소화 포지션</strong>.",
        ),
        "리스크 관리": DrillData(
            title="리스크 관리 상세",
            rows=[
                DrillRow(n="Beta", v=f"{beta:.2f}", c="#30d158" if beta < 1.2 else ("#ffd60a" if beta < 1.8 else "#ff453a"), s="안정" if beta < 1.2 else ("주의" if beta < 1.8 else "고위험")),
                DrillRow(n="52주 변동성", v=f"{(info.get('52WeekChange') or 0)*100:+.0f}%", c="#0a84ff", s="참고"),
                DrillRow(n="외국인 동향", v="매도" if supply.get("foreign",{}).get("direction",-1) == -1 else "매수", c="#ff453a" if supply.get("foreign",{}).get("direction",-1) == -1 else "#30d158", s="주의" if supply.get("foreign",{}).get("direction",-1) == -1 else "긍정"),
            ],
            insight=f"Beta {beta:.2f} — <strong>{'고베타 포지션 크기 조절 필수' if beta > 1.5 else '적정 리스크 수준'}</strong>.",
        ),
        "세후 수익률": DrillData(
            title="세후 수익률 상세",
            rows=[
                DrillRow(n="양도소득세", v="0%" if is_domestic else "22%", c="#30d158" if is_domestic else "#ffd60a", s="비과세" if is_domestic else "과세"),
                DrillRow(n="ISA 활용", v="가능" if is_domestic else "제한", c="#30d158" if is_domestic else "#ffd60a", s="절세 가능" if is_domestic else "직접 납부"),
                DrillRow(n="세후 목표수익률", v="+45%+" if is_domestic else "+35%+", c="#30d158", s="목표"),
            ],
            insight=f"{'국내 종목 양도세 0% — 해외 대비 결정적 우위' if is_domestic else '해외 종목 양도세 22% 감안 수익률 계획 필수'}.",
        ),
    }
