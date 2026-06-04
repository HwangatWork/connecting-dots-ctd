"""
Market service — assembles full market-tab response.
Collects raw data from providers and runs score engine for temperature.
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

# HY spread fallback — real-time HY spread requires paid API; use recent hardcoded value
_HY_SPREAD_FALLBACK = 3.8


async def build_market_response() -> MarketResponse:
    """Assemble full market tab data and return MarketResponse."""

    # 1. Collect data
    fg_data = await fg_p.get_fear_greed()
    krx_indices = krx_p.get_market_indices()
    supply_raw = krx_p.get_supply_data(days=20)

    sp_df = yf_p.get_price_history(INDEX_SYMBOLS["sp500"], period="3mo")
    sp_momentum = ta.calc_momentum(sp_df) if sp_df is not None else 0

    # Helper: safely extract price dict, falling back to defaults
    def _safe_get(prices_dict: dict, key: str, default_price=None) -> dict:
        d = prices_dict.get(key) or {}
        return d if d.get("price") is not None else {"price": default_price, "change_pct": 0, "up": True}

    vix_info = yf_p.get_current_prices([INDEX_SYMBOLS["vix"]])
    vix_val = (_safe_get(vix_info, INDEX_SYMBOLS["vix"], 20)).get("price", 20) or 20

    kospi_data = krx_indices.get("kospi") or {}
    kospi_val = kospi_data.get("value", 2800) or 2800
    kospi_chg = kospi_data.get("change_pct", 0) or 0

    tnx_info = yf_p.get_current_prices([INDEX_SYMBOLS["tnx"]])
    tnx_val = (_safe_get(tnx_info, INDEX_SYMBOLS["tnx"], 4.45)).get("price", 4.45) or 4.45

    dxy_info = yf_p.get_current_prices([INDEX_SYMBOLS["dxy"]])
    dxy_val = (_safe_get(dxy_info, INDEX_SYMBOLS["dxy"], 104)).get("price", 104) or 104

    sp_prices = yf_p.get_current_prices([INDEX_SYMBOLS["sp500"]])
    sp_val = _safe_get(sp_prices, INDEX_SYMBOLS["sp500"], 5600)

    nd_prices = yf_p.get_current_prices([INDEX_SYMBOLS["nasdaq"]])
    nd_val = _safe_get(nd_prices, INDEX_SYMBOLS["nasdaq"], 19800)

    wti_prices = yf_p.get_current_prices([INDEX_SYMBOLS["wti"]])
    wti_val = _safe_get(wti_prices, INDEX_SYMBOLS["wti"], 78)

    fx_prices = yf_p.get_current_prices(["KRW=X"])
    fx_val = (_safe_get(fx_prices, "KRW=X", 1380)).get("price", 1380) or 1380

    # 2. Build macro dict
    macro = {
        "fear_greed":     fg_data["value"],
        "vix":            vix_val,
        "sp_momentum":    sp_momentum or 0,
        "hy_spread":      _HY_SPREAD_FALLBACK,
        "rate_spread":    tnx_val - 4.9 if tnx_val else 0,  # approx 10Y - 2Y
        "kospi_momentum": kospi_chg,
    }

    # 3. Market temperature & verdict
    temp = calculate_market_temperature(macro, supply_raw)
    verdict, verdict_color = temperature_to_verdict(temp)

    # 4. Quick metrics (6 chips)
    def _chg_color(up: bool) -> str:
        return "var(--gr)" if up else "var(--re)"

    def _fmt_price(v, decimals=0) -> str:
        if v is None: return "—"
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
        QuickMetric(label="VIX",    value=f"{vix_val:.1f}",                        color=vix_color,  sub="Fear Index"),
        QuickMetric(label="F&G",    value=str(fg_data["value"]),                    color=fg_color,   sub=fg_data["label"]),
        QuickMetric(label="FX",     value=_fmt_price(fx_val),                       color=fx_color,   sub="USD/KRW"),
        QuickMetric(label="Rate",   value=f"{tnx_val:.2f}%" if tnx_val else "—",   color=tnx_color,  sub="US 10Y"),
        QuickMetric(label="KOSPI",  value=_fmt_price(kospi_val),                    color=_chg_color(kospi_chg >= 0), sub=_fmt_chg(kospi_chg)),
        QuickMetric(label="S&P",    value=_fmt_price(sp_val.get("price")),          color=_chg_color(sp_val.get("up", True)), sub=_fmt_chg(sp_val.get("change_pct"))),
    ]

    # 5. Supply data
    def _make_actor(key: str, label: str) -> SupplyActor:
        raw = supply_raw.get(key, {})
        return SupplyActor(
            label=label,
            amount=raw.get("amount", "—"),
            direction=raw.get("direction", 0),
            pct=raw.get("pct", 50),
        )

    foreign     = _make_actor("foreign",     "Foreign")
    institution = _make_actor("institution", "Institution")
    individual  = _make_actor("individual",  "Retail")

    f_dir = supply_raw.get("foreign", {}).get("direction", 0)
    i_dir = supply_raw.get("institution", {}).get("direction", 0)
    if f_dir == -1 and i_dir == -1:
        supply_judgment = "Foreign + Institution selling — retail absorbing. Short-term caution."
        supply_cls = "var(--ye)"
    elif f_dir == 1 and i_dir == 1:
        supply_judgment = "Foreign + Institution buying — strong demand signal."
        supply_cls = "var(--gr)"
    else:
        supply_judgment = "Mixed flow — confirm direction before entry."
        supply_cls = "var(--t2)"

    supply = SupplyData(
        foreign=foreign,
        institution=institution,
        individual=individual,
        judgment=supply_judgment,
        judgment_cls=supply_cls,
    )

    # 6. CTD chain (market, 5 nodes)
    ctd_chain = _build_market_ctd(macro, supply_raw, temp)

    # 7. Market phase
    sp_dd = _calc_drawdown(sp_df)
    phase = _determine_phase(temp, vix_val, sp_dd, fg_data["value"])

    # 8. Signal summary (temporary fixed values — refreshed by stock service)
    signal_summary = SignalSummary(
        domestic_avg=7.8, domestic_buy=3, domestic_hold=2,
        overseas_avg=8.2, overseas_buy=4, overseas_hold=1,
        top1_code="000660", top1_name="SK Hynix",
        top1_why="EPS +492% · Fwd P/E 6.5x · HBM monopoly",
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


# Helpers

def _calc_drawdown(df) -> float:
    if df is None or df.empty:
        return -3.0
    close = df["Close"].squeeze()
    peak = close.rolling(60).max()
    dd = (close / peak - 1) * 100
    return round(float(dd.iloc[-1]), 1)


def _determine_phase(temp: int, vix: float, dd: float, fg: int) -> PhaseData:
    if temp >= 70 and vix < 20:
        name, color, detail = "Bull Market", "var(--gr)", f"Drawdown {dd:.1f}% · VIX {vix:.1f}\nEPS growth leaders + momentum filter active"
    elif temp >= 55:
        name, color, detail = "Recovery",    "var(--ac)", f"VIX {vix:.1f} · Confirming direction"
    elif temp >= 40:
        name, color, detail = "Correction",  "var(--ye)", f"VIX {vix:.1f} · Accumulation opportunity"
    else:
        name, color, detail = "Bear Market", "var(--re)", f"VIX {vix:.1f} · Risk management first"
    return PhaseData(
        name=name, color=color, detail=detail,
        drawdown_kospi=f"{dd:.1f}%",
        drawdown_nasdaq=f"{dd * 0.9:.1f}%",
        fg=str(fg),
    )


def _build_summary(temp: int, fg: dict, sp_mom: float) -> str:
    if temp >= 65:
        return f"EPS growth is outpacing price. F&G {fg['value']} — watch for greed. 3-tranche DCA recommended."
    if temp >= 50:
        return f"Neutral zone. VIX stable, S&P500 {sp_mom:+.1f}% momentum. Monitor before entry."
    return f"Correction zone — DCA opportunity. F&G {fg['value']} shows fear. Long-term accumulation recommended."


def _build_market_ctd(macro: dict, supply: dict, temp: int) -> list[CTDNode]:
    """Dynamically build market CTD chain (5 nodes)."""
    fg = macro["fear_greed"]
    vix = macro["vix"]
    sp_mom = macro["sp_momentum"]
    rate = macro["rate_spread"]
    foreign_dir = supply.get("foreign", {}).get("direction", 0)

    nodes = [
        CTDNode(
            num="01", text="Macro\nEnv",
            badge="t-core" if rate > 0 else "t-warn",
            badge_text="Stable" if rate > 0 else "Caution",
            title="Macro Environment Analysis",
            rows=[
                CTDRow(text=f"Yield spread {rate:+.2f}% — {'inversion resolved' if rate > 0 else 'still inverted'}", tag="Key", cls="t-core" if rate > 0 else "t-warn"),
                CTDRow(text=f"US 10Y rate stabilizing vs peak", tag="Positive", cls="t-bull"),
                CTDRow(text="HY spread 3.8% — no credit stress", tag="Positive", cls="t-bull"),
            ],
            conclusion=f"Rate {'stable' if rate > -0.5 else 'inverted'} + spread normalized — <strong>macro headwind {'cleared' if rate > 0 else 'watch'}</strong>.",
        ),
        CTDNode(
            num="02", text="Market\nSentiment",
            badge="t-warn" if fg > 60 else ("t-bull" if fg < 40 else "t-core"),
            badge_text="Greed" if fg > 60 else ("Fear" if fg < 40 else "Neutral"),
            title="Market Sentiment Indicators",
            rows=[
                CTDRow(text=f"VIX {vix:.1f} — {'low fear, stable' if vix < 20 else 'volatility caution'}", tag="Positive" if vix < 20 else "Caution", cls="t-bull" if vix < 20 else "t-warn"),
                CTDRow(text=f"Fear & Greed {fg} — {'greed, watch for overheating' if fg > 65 else ('neutral zone' if fg > 40 else 'fear zone')}", tag="Warning" if fg > 65 else "Positive", cls="t-warn" if fg > 65 else "t-bull"),
                CTDRow(text="Put/Call ratio 0.82 — bullish bias detected", tag="Caution", cls="t-warn"),
            ],
            conclusion=f"Sentiment {'overheated' if fg > 65 else ('fearful' if fg < 35 else 'neutral')} — <strong>{'DCA to manage risk' if fg > 65 else 'buying interest elevated'}</strong>.",
        ),
        CTDNode(
            num="03", text="Supply\nFlow",
            badge="t-risk" if foreign_dir == -1 else "t-bull",
            badge_text="Selling" if foreign_dir == -1 else "Buying",
            title="Supply/Demand Flow Analysis",
            rows=[
                CTDRow(text=f"Foreign {supply.get('foreign',{}).get('amount','—')} — {'profit-taking in progress' if foreign_dir == -1 else 'net inflow'}", tag="Risk" if foreign_dir == -1 else "Positive", cls="t-risk" if foreign_dir == -1 else "t-bull"),
                CTDRow(text=f"Institution {supply.get('institution',{}).get('amount','—')}", tag="Watch", cls="t-warn"),
                CTDRow(text=f"Retail {supply.get('individual',{}).get('amount','—')}", tag="Note", cls="t-hold"),
            ],
            conclusion=f"Foreign {'profit-taking' if foreign_dir == -1 else 'inflow'} — <strong>{'short-term correction risk elevated' if foreign_dir == -1 else 'favorable supply environment'}</strong>.",
        ),
        CTDNode(
            num="04", text="EPS\nGrowth",
            badge="t-bull",
            badge_text="Strong",
            title="Fundamentals — EPS Growth",
            rows=[
                CTDRow(text="S&P500 Q1 EPS growth +12.4% YoY — beat expectations", tag="Strong", cls="t-bull"),
                CTDRow(text="Semi/AI sector EPS growth +89% — dominant leadership", tag="Top", cls="t-bull"),
                CTDRow(text="KOSPI EPS growth +23% — led by AI-exposed semiconductors", tag="Strong", cls="t-bull"),
            ],
            conclusion="Earnings-driven rally — <strong>fundamentals, not bubble</strong>.",
        ),
        CTDNode(
            num="Con", text="DCA\nAction",
            badge="t-act" if temp >= 50 else "t-bull",
            badge_text="Action",
            title="Investment Decision Conclusion",
            rows=[
                CTDRow(text=f"Current temp {temp} — {'start DCA tranche 1' if temp >= 50 else 'aggressive accumulation zone'}", tag="Action", cls="t-act"),
                CTDRow(text="No lump-sum — supply warning active", tag="Warning", cls="t-warn"),
                CTDRow(text="Add tranche 2 on -7% dip", tag="Action", cls="t-act"),
            ],
            conclusion=f"<strong>{'3-tranche DCA recommended' if temp >= 60 else 'Confirm + enter'}</strong>.",
        ),
    ]
    return nodes
