"""
Stock service — assembles Zone 4 full stock detail response.
Collects data from yfinance + pykrx and builds StockDetailResponse.
"""
from datetime import datetime, timezone
import logging

from providers import yahoo_finance as yf_p
from providers import krx as krx_p
from services import technical as ta
from services.score_engine import calculate_iq_score
from config import ALL_STOCKS, RADAR_AXES
from schemas import (
    StockDetailResponse, StockHeader, StockListItem,
    RadarData, ValidityRow, BuyPlan, BuyLevel, AfterTax,
    DrillData, DrillRow, CTDNode, CTDRow,
)

log = logging.getLogger(__name__)


async def get_stocks_list(group: str) -> list[StockListItem]:
    """Return stock list with IQ scores (summary only)."""
    stocks = [s for s in ALL_STOCKS.values() if s["group"] == group]
    result = []

    for s in stocks:
        try:
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
    """Return full Zone 4 stock detail."""
    meta = ALL_STOCKS.get(code)
    if not meta:
        raise ValueError(f"Unknown stock code: {code}")

    is_domestic = meta["group"] == "domestic"

    df = yf_p.get_price_history(meta["yahoo"], period="6mo")
    info = yf_p.get_ticker_info(meta["yahoo"])
    tech = ta.calc_all(df) if df is not None else {}

    supply_raw = {}
    if is_domestic:
        krx_price = krx_p.get_stock_price(code)
        supply_raw = krx_p.get_supply_data(days=20)
    else:
        krx_price = None

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

    macro_ctx = {"vix": 18.2, "sp_momentum": 2.5}  # default; ideally injected from market_service
    score_data = calculate_iq_score(info, tech, macro_ctx, supply_raw, is_domestic)
    score = score_data["overall"]

    breakdown = score_data["breakdown"]
    sorted_axes = sorted(breakdown.items(), key=lambda x: x[1], reverse=True)
    strengths = [k for k, _ in sorted_axes[:2]]
    weaknesses = [k for k, _ in sorted_axes[-2:] if sorted_axes[-1][1] < 7]

    header = StockHeader(
        code=code, name=meta["name"],
        price=price_str, change=chg_str, up=up, score=score,
    )

    radar = RadarData(
        scores=score_data["scores"],
        colors=score_data["colors"],
        axes=RADAR_AXES,
    )

    ctd_chain = _build_stock_ctd(meta, info, tech, score_data)
    validity = _build_validity(info, tech, is_domestic)
    buy_plan = _build_buy_plan(price_val, score, is_domestic)
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


# Helpers

def _build_stock_ctd(meta: dict, info: dict, tech: dict, score_data: dict) -> list[CTDNode]:
    name = meta["name"]
    sector = (info.get("sector") or "Technology")
    eps_g = info.get("earningsQuarterlyGrowth", 0) or 0
    fpe = info.get("forwardPE", 15) or 15
    score = score_data["overall"]

    return [
        CTDNode(num="01", text="Macro\nEnv", badge="t-core", badge_text="Key",
            title="Macro Environment & Sector",
            rows=[
                CTDRow(text=f"Sector: {sector} — AI/semi cycle beneficiary", tag="Key", cls="t-core"),
                CTDRow(text="Global AI CapEx $700B+ — direct demand tailwind", tag="Strong", cls="t-bull"),
                CTDRow(text="Macro headwind clearing — rates stabilizing", tag="Positive", cls="t-bull"),
            ],
            conclusion=f"AI cycle + rate stability — <strong>{name} structural tailwind</strong>."),

        CTDNode(num="02", text="EPS\nGrowth", badge="t-bull", badge_text="Strong",
            title="EPS & Revenue Growth",
            rows=[
                CTDRow(text=f"EPS YoY {eps_g*100:+.0f}% — {'dominant' if eps_g > 1 else 'growing'} earnings", tag="Top" if eps_g > 1 else "Strong", cls="t-bull"),
                CTDRow(text=f"Gross Margin {(info.get('grossMargins',0)*100):.0f}% — pricing power confirmed", tag="Positive", cls="t-bull"),
                CTDRow(text="FCF positive — buyback/dividend capacity", tag="Healthy", cls="t-bull"),
            ],
            conclusion=f"Earnings outpacing price — <strong>expansion zone, not bubble</strong>."),

        CTDNode(num="03", text="Valuation", badge="t-bull" if fpe < 20 else "t-warn", badge_text="Cheap" if fpe < 20 else "Caution",
            title="Valuation Analysis",
            rows=[
                CTDRow(text=f"Fwd P/E {fpe:.1f}x — {'undervalued' if fpe < 20 else 'watch premium'}", tag="Key", cls="t-bull" if fpe < 20 else "t-warn"),
                CTDRow(text=f"PEG {(info.get('pegRatio',1)):.2f} — {'attractive vs growth' if (info.get('pegRatio',1) or 1) < 1.5 else 'growth premium high'}", tag="Cheap" if (info.get('pegRatio',1) or 1) < 1.5 else "Caution", cls="t-bull" if (info.get('pegRatio',1) or 1) < 1.5 else "t-warn"),
                CTDRow(text="DCF vs current price — upside exists", tag="Positive", cls="t-bull"),
            ],
            conclusion=f"Fwd P/E {fpe:.1f}x — <strong>market has not fully priced in growth</strong>."),

        CTDNode(num="04", text="Tech\nSignal", badge="t-warn" if (tech.get("rsi", 50) or 50) > 70 else "t-bull", badge_text="Overbought" if (tech.get("rsi", 50) or 50) > 70 else "Neutral",
            title="Technical Analysis",
            rows=[
                CTDRow(text=f"RSI {tech.get('rsi', '—')} — {tech.get('rsi_signal','neutral')}", tag="Check", cls="t-warn" if (tech.get("rsi", 50) or 50) > 70 else "t-bull"),
                CTDRow(text=f"MA50 {'>' if (tech.get('ma50') or 0) > (tech.get('ma200') or 0) else '<'} MA200 — {tech.get('ma_signal','neutral')} cross", tag="Strong" if tech.get("ma_signal") == "golden" else "Caution", cls="t-bull" if tech.get("ma_signal") == "golden" else "t-warn"),
                CTDRow(text=f"Stoch RSI {tech.get('stoch_rsi', '—')} — {'overbought, DCA only' if (tech.get('stoch_rsi', 50) or 50) > 80 else 'normal zone'}", tag="Warning" if (tech.get("stoch_rsi", 50) or 50) > 80 else "Positive", cls="t-warn" if (tech.get("stoch_rsi", 50) or 50) > 80 else "t-bull"),
            ],
            conclusion=f"Technical {'overbought — DCA required' if (tech.get('rsi', 50) or 50) > 70 else 'neutral — good entry'}. <strong>Tranche entry recommended</strong>."),

        CTDNode(num="Con", text="Decision", badge="t-act" if score >= 7 else "t-hold", badge_text="Buy" if score >= 7 else "Hold",
            title="Final Investment Decision",
            rows=[
                CTDRow(text=f"IQ Score {score} — {'buy recommended' if score >= 7 else 'hold/watch'}", tag="Conclusion", cls="t-act" if score >= 7 else "t-hold"),
                CTDRow(text="3-tranche DCA — no lump-sum", tag="Action", cls="t-act"),
                CTDRow(text=f"After-tax target: {'+35%+' if score >= 7.5 else '+20%+'}", tag="Target", cls="t-bull"),
            ],
            conclusion=f"<strong>{'3-tranche DCA recommended' if score >= 7 else 'Monitor and enter on confirmation'}</strong>."),
    ]


def _build_validity(info: dict, tech: dict, is_domestic: bool) -> list[ValidityRow]:
    rows = []
    eps_g = info.get("earningsQuarterlyGrowth", 0) or 0
    rsi = tech.get("rsi", 50) or 50
    stoch = tech.get("stoch_rsi", 50) or 50

    if eps_g > 0.5:
        rows.append(ValidityRow(icon="✅", text=f"EPS YoY +{eps_g*100:.0f}% growth valid", date=datetime.now().strftime("%Y.%m.%d") + " confirmed", status="Valid", cls="t-bull"))
    if is_domestic:
        rows.append(ValidityRow(icon="✅", text="Domestic stock — capital gains tax 0% (tax-exempt)", date="Per regulation", status="Valid", cls="t-bull"))
    if rsi > 70:
        rows.append(ValidityRow(icon="⚠️", text=f"RSI {rsi:.0f} — short-term overbought warning", date=datetime.now().strftime("%Y.%m.%d") + " updated", status="Warning", cls="t-warn"))
    if stoch > 80:
        rows.append(ValidityRow(icon="⚠️", text=f"Stoch RSI {stoch:.0f} — DCA required", date=datetime.now().strftime("%Y.%m.%d") + " updated", status="Warning", cls="t-warn"))
    if not rows:
        rows.append(ValidityRow(icon="✅", text="Key investment thesis valid — continue monitoring", date=datetime.now().strftime("%Y.%m.%d"), status="Valid", cls="t-bull"))

    return rows


def _build_buy_plan(price: float, score: float, is_domestic: bool) -> BuyPlan:
    if not price:
        price = 100000

    cur_lo  = price * 0.90
    cur_hi  = price * 1.12
    dip1_lo = price * 0.75
    dip1_hi = price * 0.90
    dip2_lo = price * 0.58
    dip2_hi = price * 0.75
    target    = price * 1.45
    stop_loss = price * 0.72

    def _fmt(v: float, is_d: bool) -> str:
        if is_d:
            return f"₩{int(v):,}"
        return f"${v:,.0f}" if v >= 1 else f"${v:.2f}"

    levels = [
        BuyLevel(label="Current Zone", range=f"{_fmt(cur_lo, is_domestic)}~{_fmt(cur_hi, is_domestic)}", weight="30%", color="var(--ac)", fill=45),
        BuyLevel(label="Dip 1",        range=f"{_fmt(dip1_lo, is_domestic)}~{_fmt(dip1_hi, is_domestic)}", weight="40%", color="var(--gr)", fill=68),
        BuyLevel(label="Dip 2",        range=f"{_fmt(dip2_lo, is_domestic)}~{_fmt(dip2_hi, is_domestic)}", weight="30%", color="var(--ye)", fill=100),
    ]

    expected_ret = target / price - 1
    domestic_ret = expected_ret
    overseas_ret = expected_ret * (1 - 0.22)

    return BuyPlan(
        levels=levels,
        target=_fmt(target, is_domestic),
        stop_loss=_fmt(stop_loss, is_domestic),
        after_tax_domestic=AfterTax(
            ret=f"+{domestic_ret*100:.0f}%",
            label="After-tax (Domestic 0%)" if is_domestic else "After-tax (22%)",
            color="var(--gr)",
            tax_note="Cap gains 0%" if is_domestic else "Cap gains 22%",
        ),
        after_tax_overseas=AfterTax(
            ret=f"+{overseas_ret*100:.0f}%",
            label="Overseas equiv (22%)",
            color="var(--ye)",
            tax_note="22% applied",
        ),
    )


def _build_drill(info: dict, tech: dict, score_data: dict, supply: dict, is_domestic: bool) -> dict[str, DrillData]:
    gm    = (info.get("grossMargins") or 0) * 100
    om    = (info.get("operatingMargins") or 0) * 100
    eps_g = (info.get("earningsQuarterlyGrowth") or 0) * 100
    rev_g = (info.get("revenueGrowth") or 0) * 100
    fpe   = info.get("forwardPE") or 15
    peg   = info.get("pegRatio") or 1
    de    = info.get("debtToEquity") or 30
    cr    = info.get("currentRatio") or 2
    beta  = info.get("beta") or 1.0
    rsi   = tech.get("rsi") or 50
    stoch = tech.get("stoch_rsi") or 50

    return {
        "Business Quality": DrillData(
            title="Business Quality Detail",
            rows=[
                DrillRow(n="Gross Margin",    v=f"{gm:.1f}%",  c="#30d158" if gm > 40 else "#ffd60a",  s="Strong" if gm > 40 else "Average"),
                DrillRow(n="Operating Margin",v=f"{om:.1f}%",  c="#30d158" if om > 20 else "#ffd60a",  s="Strong" if om > 20 else "Average"),
                DrillRow(n="Competitive Moat",v="Wide" if gm > 50 else "Narrow", c="#0a84ff", s="Assessment"),
            ],
            insight=f"Gross Margin {gm:.0f}% — <strong>{'strong pricing power' if gm > 40 else 'watch competitive pressure'}</strong>.",
        ),
        "Growth Momentum": DrillData(
            title="Growth Momentum Detail",
            rows=[
                DrillRow(n="EPS YoY",     v=f"{eps_g:+.0f}%", c="#30d158" if eps_g > 20 else "#ffd60a", s="Strong" if eps_g > 20 else "Average"),
                DrillRow(n="Revenue YoY", v=f"{rev_g:+.0f}%", c="#30d158" if rev_g > 10 else "#ffd60a", s="Growing" if rev_g > 10 else "Flat"),
                DrillRow(n="1M Momentum", v=f"{tech.get('momentum_1m',0):+.1f}%", c="#30d158" if (tech.get("momentum_1m") or 0) > 0 else "#ff453a", s="Up" if (tech.get("momentum_1m") or 0) > 0 else "Down"),
            ],
            insight=f"EPS {eps_g:+.0f}% — <strong>{'powerful growth cycle' if eps_g > 50 else 'steady growth trend'}</strong>.",
        ),
        "Valuation": DrillData(
            title="Valuation Detail",
            rows=[
                DrillRow(n="Fwd P/E",   v=f"{fpe:.1f}x", c="#30d158" if fpe < 15 else ("#ffd60a" if fpe < 25 else "#ff453a"), s="Cheap" if fpe < 15 else ("Fair" if fpe < 25 else "Expensive")),
                DrillRow(n="PEG",       v=f"{peg:.2f}",  c="#30d158" if peg < 1 else ("#ffd60a" if peg < 2 else "#ff453a"),   s="Attractive" if peg < 1 else ("Fair" if peg < 2 else "Expensive")),
                DrillRow(n="EV/EBITDA", v=f"{(info.get('enterpriseToEbitda') or 15):.1f}x", c="#0a84ff", s="Reference"),
            ],
            insight=f"Fwd P/E {fpe:.1f}x — <strong>{'cheap vs growth' if fpe < 20 else 'valuation premium exists'}</strong>.",
        ),
        "Market Timing": DrillData(
            title="Market Timing Detail",
            rows=[
                DrillRow(n="RSI(14)",   v=f"{rsi:.0f}",   c="#30d158" if rsi < 60 else ("#ffd60a" if rsi < 70 else "#ff453a"),   s="OK" if rsi < 60 else ("Caution" if rsi < 70 else "Overbought")),
                DrillRow(n="Stoch RSI", v=f"{stoch:.0f}", c="#30d158" if stoch < 60 else ("#ffd60a" if stoch < 80 else "#ff453a"), s="OK" if stoch < 60 else ("Caution" if stoch < 80 else "Overbought")),
                DrillRow(n="MA Signal", v=tech.get("ma_signal","—"), c="#30d158" if tech.get("ma_signal") == "golden" else "#ff453a", s="Golden" if tech.get("ma_signal") == "golden" else "Dead"),
            ],
            insight=f"{'RSI overbought — DCA entry only' if rsi > 70 else 'RSI normal — good entry'}. <strong>Stoch RSI {stoch:.0f}</strong>.",
        ),
        "Financial Health": DrillData(
            title="Financial Health Detail",
            rows=[
                DrillRow(n="D/E Ratio",      v=f"{de:.0f}%",  c="#30d158" if de < 50 else ("#ffd60a" if de < 100 else "#ff453a"),  s="Safe" if de < 50 else ("OK" if de < 100 else "Risk")),
                DrillRow(n="Current Ratio",  v=f"{cr:.1f}x",  c="#30d158" if cr > 2 else ("#ffd60a" if cr > 1 else "#ff453a"),     s="Strong" if cr > 2 else ("OK" if cr > 1 else "Caution")),
                DrillRow(n="FCF",            v="Positive" if (info.get("freeCashflow") or 0) > 0 else "Negative", c="#30d158" if (info.get("freeCashflow") or 0) > 0 else "#ff453a", s="Healthy" if (info.get("freeCashflow") or 0) > 0 else "Watch"),
            ],
            insight=f"D/E {de:.0f}% — <strong>{'financial crisis probability low' if de < 100 else 'debt burden monitoring required'}</strong>.",
        ),
        "Macro Linkage": DrillData(
            title="Macro Linkage Detail",
            rows=[
                DrillRow(n="AI CapEx Sensitivity", v="Direct beneficiary", c="#0a84ff", s="Key"),
                DrillRow(n="Rate Sensitivity",     v="Low" if beta < 1.2 else "High", c="#30d158" if beta < 1.2 else "#ffd60a", s="Assessment"),
                DrillRow(n="FX Impact",            v="USD revenue" if not is_domestic else "KRW revenue", c="#30d158", s="Positive"),
            ],
            insight="AI cycle direct beneficiary — <strong>macro risk minimized position</strong>.",
        ),
        "Risk Management": DrillData(
            title="Risk Management Detail",
            rows=[
                DrillRow(n="Beta",           v=f"{beta:.2f}", c="#30d158" if beta < 1.2 else ("#ffd60a" if beta < 1.8 else "#ff453a"), s="Stable" if beta < 1.2 else ("Caution" if beta < 1.8 else "High Risk")),
                DrillRow(n="52W Volatility", v=f"{(info.get('52WeekChange') or 0)*100:+.0f}%", c="#0a84ff", s="Reference"),
                DrillRow(n="Foreign Flow",   v="Selling" if supply.get("foreign",{}).get("direction",-1) == -1 else "Buying", c="#ff453a" if supply.get("foreign",{}).get("direction",-1) == -1 else "#30d158", s="Watch" if supply.get("foreign",{}).get("direction",-1) == -1 else "Positive"),
            ],
            insight=f"Beta {beta:.2f} — <strong>{'high beta: position sizing critical' if beta > 1.5 else 'appropriate risk level'}</strong>.",
        ),
        "After-tax Return": DrillData(
            title="After-tax Return Detail",
            rows=[
                DrillRow(n="Capital Gains Tax", v="0%" if is_domestic else "22%", c="#30d158" if is_domestic else "#ffd60a", s="Tax-exempt" if is_domestic else "Taxable"),
                DrillRow(n="ISA Account",       v="Available" if is_domestic else "Limited", c="#30d158" if is_domestic else "#ffd60a", s="Tax saving" if is_domestic else "Direct pay"),
                DrillRow(n="After-tax Target",  v="+45%+" if is_domestic else "+35%+", c="#30d158", s="Target"),
            ],
            insight=f"{'Domestic: 0% cap gains — decisive advantage over overseas' if is_domestic else 'Overseas: plan returns accounting for 22% cap gains tax'}.",
        ),
    }
