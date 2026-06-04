from pydantic import BaseModel
from typing import Optional

# ── Ticker ────────────────────────────────────────────────────
class TickerItem(BaseModel):
    label: str
    value: str
    change: str
    up: bool

class TickerResponse(BaseModel):
    items: list[TickerItem]
    updated_at: str

# ── Market ────────────────────────────────────────────────────
class QuickMetric(BaseModel):
    label: str
    value: str
    color: str       # CSS var name e.g. "var(--gr)"
    sub: str

class CTDRow(BaseModel):
    text: str
    tag: str
    cls: str         # t-core | t-bull | t-warn | t-risk | t-act

class CTDNode(BaseModel):
    num: str
    text: str        # 2줄 표시용 \n 구분
    badge: str       # CSS class
    badge_text: str
    title: str
    rows: list[CTDRow]
    conclusion: str

class SupplyActor(BaseModel):
    label: str
    amount: str
    direction: int   # 1=매수, -1=매도
    pct: int         # 바 너비 0-100

class SupplyData(BaseModel):
    foreign: SupplyActor
    institution: SupplyActor
    individual: SupplyActor
    judgment: str
    judgment_cls: str

class PhaseData(BaseModel):
    name: str
    color: str
    detail: str
    drawdown_kospi: str
    drawdown_nasdaq: str
    fg: str

class SignalSummary(BaseModel):
    domestic_avg: float
    domestic_buy: int
    domestic_hold: int
    overseas_avg: float
    overseas_buy: int
    overseas_hold: int
    top1_code: str
    top1_name: str
    top1_why: str
    top1_score: float

class MarketResponse(BaseModel):
    temperature: int
    verdict: str
    verdict_color: str
    summary: str
    quick_metrics: list[QuickMetric]
    ctd_chain: list[CTDNode]
    supply: SupplyData
    phase: PhaseData
    signal_summary: SignalSummary
    updated_at: str

# ── Stocks List ───────────────────────────────────────────────
class StockListItem(BaseModel):
    code: str
    name: str
    price: str
    change: str
    up: bool
    score: float

class StocksResponse(BaseModel):
    group: str
    items: list[StockListItem]
    updated_at: str

# ── Stock Detail ──────────────────────────────────────────────
class StockHeader(BaseModel):
    code: str
    name: str
    price: str
    change: str
    up: bool
    score: float

class RadarData(BaseModel):
    scores: list[float]      # 8개 0~10
    colors: list[str]        # 8개 hex
    axes: list[str]          # 8개 축 이름

class ValidityRow(BaseModel):
    icon: str
    text: str
    date: str
    status: str
    cls: str

class BuyLevel(BaseModel):
    label: str
    range: str
    weight: str
    color: str
    fill: int    # 0~100 bar width

class AfterTax(BaseModel):
    ret: str
    label: str
    color: str
    tax_note: str

class BuyPlan(BaseModel):
    levels: list[BuyLevel]
    target: str
    stop_loss: str
    after_tax_domestic: AfterTax
    after_tax_overseas: AfterTax

class DrillRow(BaseModel):
    n: str
    v: str
    c: str   # hex color
    s: str   # signal label

class DrillData(BaseModel):
    title: str
    rows: list[DrillRow]
    insight: str

class StockDetailResponse(BaseModel):
    header: StockHeader
    strengths: list[str]
    weaknesses: list[str]
    ctd_chain: list[CTDNode]
    radar: RadarData
    validity: list[ValidityRow]
    buy_plan: BuyPlan
    drill: dict[str, DrillData]
    updated_at: str

# ── Health ────────────────────────────────────────────────────
class HealthResponse(BaseModel):
    status: str
    timestamp: str
    cache_stats: Optional[dict] = None
