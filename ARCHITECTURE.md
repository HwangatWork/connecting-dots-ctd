# 커넥팅닷 (CTD) — 시스템 아키텍처 설계

**버전:** v1.0  
**작성일:** 2026-06-04  
**스택:** Python FastAPI + 단일 HTML + 무료 공개 API + Vercel/Netlify

---

## 1. 전체 구조 (Bird's Eye View)

```
┌─────────────────────────────────────────────────────────────────┐
│                         사용자 브라우저                           │
│                    frontend/index.html                           │
│              (Netlify — 정적 CDN 배포)                           │
└─────────────────┬───────────────────────────────────────────────┘
                  │  HTTP fetch() — /api/v1/*
                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FastAPI 서버                                   │
│            backend/main.py (Render.com 무료 호스팅)               │
│                                                                   │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────┐           │
│  │  /market    │  │  /stocks     │  │  /ticker      │           │
│  │  Router     │  │  Router      │  │  Router       │           │
│  └──────┬──────┘  └──────┬───────┘  └───────┬───────┘           │
│         │                │                   │                   │
│  ┌──────▼────────────────▼───────────────────▼───────────────┐  │
│  │                   Service Layer                            │  │
│  │  MarketService │ StockService │ ScoreEngine │ Technical    │  │
│  └──────────────────────────────────────────────────────────┘   │
│                  │                   │                           │
│         ┌────────▼──────┐   ┌───────▼───────┐                  │
│         │  TTL Cache    │   │  Providers    │                   │
│         │  (in-memory)  │   │  yfinance     │                   │
│         │  market: 5분  │   │  pykrx        │                   │
│         │  stocks: 15분 │   │  fear&greed   │                   │
│         └───────────────┘   └───────────────┘                   │
└─────────────────────────────────────────────────────────────────┘
                  │
                  ▼
     ┌────────────────────────┐
     │   외부 무료 데이터 소스   │
     │  Yahoo Finance (무료)   │
     │  pykrx (KRX 공식 무료)  │
     │  Alternative.me (무료)  │
     └────────────────────────┘
```

---

## 2. 프로젝트 폴더 구조

```
CTD/                                 ← 프로젝트 루트
│
├── frontend/
│   └── index.html                   ← 단일 HTML 앱 (정적 배포)
│
├── backend/
│   ├── main.py                      ← FastAPI 앱 진입점, CORS, 라우터 등록
│   │
│   ├── routers/                     ← HTTP 레이어 (요청/응답만)
│   │   ├── __init__.py
│   │   ├── market.py                ← GET /api/v1/market
│   │   ├── stocks.py                ← GET /api/v1/stocks, /stocks/{code}
│   │   └── ticker.py                ← GET /api/v1/ticker
│   │
│   ├── services/                    ← 비즈니스 로직 레이어
│   │   ├── __init__.py
│   │   ├── market_service.py        ← 시장 온도 계산, CTD 체인 생성
│   │   ├── stock_service.py         ← 종목 Zone 4 데이터 조립
│   │   ├── score_engine.py          ← IQ 스코어 8축 계산 엔진
│   │   └── technical.py             ← RSI, MA50/200, Bollinger, Stoch RSI
│   │
│   ├── providers/                   ← 외부 API 연동 레이어
│   │   ├── __init__.py
│   │   ├── yahoo_finance.py         ← yfinance wrapper (주가, 지수, 재무)
│   │   ├── krx.py                   ← pykrx wrapper (수급, 코스피/코스닥)
│   │   └── fear_greed.py            ← Alternative.me Fear & Greed Index
│   │
│   ├── cache.py                     ← TTL 인메모리 캐시
│   ├── schemas.py                   ← Pydantic 응답 모델 (API 계약)
│   ├── config.py                    ← 환경변수, 종목 마스터, 가중치 상수
│   └── requirements.txt
│
├── doc/                             ← 기존 설계 문서 (변경 없음)
│   ├── CTD_Mobile_UXUI_Brief.md
│   ├── CTD_Mobile_System_Architecture.md
│   └── 64개 지표.txt
│
├── old/                             ← 레거시 (읽기 전용)
│   └── investiq_web_v3.html
│
├── vercel.json                      ← Vercel 배포 설정 (프론트)
├── render.yaml                      ← Render.com 배포 설정 (백엔드)
├── .env.example                     ← 환경변수 템플릿
└── ARCHITECTURE.md                  ← 이 문서
```

---

## 3. API 엔드포인트 계약

```
Base URL (개발): http://localhost:8000
Base URL (운영): https://ctd-api.onrender.com

GET /api/v1/health
  → { status: "ok", timestamp: "..." }

GET /api/v1/ticker
  → TickerResponse: [{ label, value, change, up }]
  캐시: 1분

GET /api/v1/market
  → MarketResponse
    .temperature: int (0-100)
    .verdict: str
    .summary: str
    .quick_metrics: [{ label, value, color, sub }]
    .ctd_chain: [{ num, title, rows, conclusion }]
    .supply: { foreign, institution, individual, judgment }
    .phase: { name, drawdown_kospi, drawdown_nasdaq, fg }
    .signal_summary: { domestic_avg, overseas_avg, top1 }
  캐시: 5분

GET /api/v1/stocks?group=domestic|overseas
  → StocksResponse: [{ code, name, price, change, up, score }]
  캐시: 15분

GET /api/v1/stocks/{code}
  → StockDetailResponse
    .header: { code, name, price, change, up, score }
    .badges: { strengths, weaknesses }
    .ctd_chain: [...]
    .radar: { scores: [8 floats], colors: [8 hex], axes: [8 labels] }
    .validity: [{ icon, text, date, status }]
    .buy_plan: { levels: [...], target, stop_loss, after_tax }
    .drill: { axis_name: { title, rows, insight } }
  캐시: 15분
```

---

## 4. 64개 지표 → 데이터 소스 매핑

| 카테고리 | 지표 | 데이터 소스 | 수집 방법 |
|---|---|---|---|
| 시장 지수 6개 | S&P500, NASDAQ, DOW, 코스피, 코스닥, 닛케이 | Yahoo Finance / pykrx | `yfinance.download()` / `pykrx.stock.get_market_ohlcv()` |
| 매크로 6개 | 미10Y금리, DXY, WTI, 연준자산, 장단기스프레드, HY스프레드 | Yahoo Finance (^TNX, DX-Y.NYB, CL=F) | `yfinance.Ticker().info` |
| 심리 6개 | CNN F&G, VIX, SKEW, Put/Call, 모멘텀, 강도 | Alternative.me / Yahoo (^VIX, ^SKEW) | REST API + yfinance |
| 펀더멘털 9개 | Revenue, EPS GAAP/NonGAAP, 영업이익률, Gross Margin, CapEx, FCF, AI CapEx수혜 | Yahoo Finance | `ticker.financials`, `ticker.info` |
| 밸류에이션 8개 | P/E Trailing/Forward, PEG, EV/Rev, EV/EBITDA, P/Book, DCF, 시가총액 | Yahoo Finance | `ticker.info` |
| 기술적 8개 | RSI(14), RSI신호, MA50, MA200, MA신호, Beta, 볼린저, Stoch RSI | Yahoo Finance + pandas_ta | `yfinance.download()` + 계산 |
| 세금·절세 10개 | 양도세, 배당세, 환율손익, ISA, 연금저축, IRP 등 | 계산 로직 | 규칙 기반 계산 |
| 수급 3개 | 외국인, 기관, 개인 | pykrx | `pykrx.stock.get_market_trading_value_by_date()` |
| 종목 평가 8개 | 8축 IQ 스코어 | 위 데이터 종합 | score_engine.py |

---

## 5. 시장 온도 계산 알고리즘

```python
# 가중 합산 (0~100점)
TEMPERATURE_WEIGHTS = {
    "fear_greed":    0.20,   # CNN Fear & Greed
    "vix_score":     0.20,   # VIX 역산 점수
    "sp_momentum":   0.20,   # S&P500 1개월 모멘텀
    "hy_spread":     0.15,   # High Yield 스프레드 역산
    "rate_spread":   0.15,   # 장단기 금리차
    "kospi_momentum":0.10,   # 코스피 모멘텀
}
```

---

## 6. 종목 IQ 스코어 계산 (8축)

```python
# 각 축 0~10점 → 레이더 차트
AXES = {
    "business_quality":  { 실적기반 → gross_margin, moat_proxy },
    "growth_momentum":   { yoy_eps_growth, yoy_revenue_growth },
    "valuation":         { forward_pe_vs_sector, peg, ev_ebitda },
    "market_timing":     { rsi14, stoch_rsi, ma_signal },
    "financial_health":  { debt_equity, current_ratio, fcf_yield },
    "macro_linkage":     { sector_beta_to_rates, fx_sensitivity },
    "risk_management":   { beta, 52w_volatility, foreign_flow },
    "after_tax_return":  { domestic_tax_rate, expected_return_net },
}
```

---

## 7. 캐시 전략

```
TTL 정책:
  ticker:     60초   (빠른 갱신)
  market:    300초   (5분, 장중)
  stocks:    900초   (15분)
  stock/{code}: 900초

캐시 무효화:
  - 장 마감 후 (KST 15:30 / EST 16:00) TTL 연장 → 3600초
  - 수동 강제 갱신: GET /api/v1/cache/invalidate (내부 전용)
```

---

## 8. 배포 전략

```
Frontend  →  Netlify
  - 정적 HTML 파일 1개
  - Build: 없음 (순수 HTML)
  - 환경변수: VITE_API_BASE_URL → API_BASE_URL 인라인 치환

Backend  →  Render.com (Free Tier)
  - Python 3.11
  - Start Command: uvicorn backend.main:app --host 0.0.0.0 --port $PORT
  - 무료 한계: 750시간/월, 15분 비활성 시 슬립
  - 대안: Railway.app (무료 $5 크레딧/월)

로컬 개발:
  cd backend && uvicorn main:app --reload --port 8000
  HTML 파일에서 localhost:8000 직접 호출
```

---

## 9. 데이터 흐름 시퀀스

```
브라우저 로드
  │
  ├─ fetch /api/v1/ticker    → 1초 후 티커 띠 업데이트
  ├─ fetch /api/v1/market    → 시장 탭 렌더링
  └─ 탭 전환 시
       ├─ 종목 탭: fetch /api/v1/stocks?group=domestic
       │           fetch /api/v1/stocks/{code}  (종목 선택 시)
       └─ 투자 탭: 로컬 포트폴리오 데이터 (localStorage)

갱신 주기:
  - 티커: 60초마다 자동 갱신
  - 시장: 5분마다 자동 갱신
  - 종목: 탭 진입 시 1회 + 15분마다
```

---

*CTD Architecture v1.0 — 2026.06.04*
