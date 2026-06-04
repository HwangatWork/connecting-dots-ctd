# 커넥팅닷 모바일 웹앱 — 시스템 아키텍처 & Claude Code 실행 가이드
**버전:** v1.0  
**작성일:** 2026년 6월 4일  
**실행 환경:** Claude Code (VSCode)  
**목적:** connecting_dots_mobile.html 구현

---

## 1. 구현 목표

데스크톱 `investiq_web_v3.html`의 디자인 시스템을 유지하면서  
**375px 기준 모바일 웹앱** `connecting_dots_mobile.html`을 단일 파일로 구현한다.

---

## 2. 파일 구조

```
단일 파일: connecting_dots_mobile.html
├── <head>
│   ├── Google Fonts (Inter, JetBrains Mono, Noto Sans KR)
│   ├── <style> CSS 전체
│   │   ├── CSS 변수 (디자인 토큰)
│   │   ├── Reset & Base
│   │   ├── 레이아웃 (Topbar, Ticker, Content, BottomNav)
│   │   ├── 컴포넌트별 스타일
│   │   └── 탭별 스타일
│   └── </style>
│
└── <body>
    ├── #topbar
    ├── #ticker
    ├── #content
    │   ├── #tab-market  (시장 탭)
    │   ├── #tab-stocks  (종목 탭)
    │   ├── #tab-invest  (투자 탭)
    │   └── #tab-more    (더보기 탭)
    ├── #bottom-nav
    └── <script> JS 전체
        ├── DATA (하드코딩 목업 데이터)
        ├── STATE (현재 탭, 선택 종목 등)
        ├── RENDER 함수들
        └── EVENT LISTENERS
```

---

## 3. CSS 아키텍처

### 3.1 디자인 토큰 (`:root`)

```css
:root {
  /* 배경 레이어 */
  --bg: #000000;
  --l1: #0a0a0a;
  --l2: #111113;
  --l3: #1a1a1c;

  /* 글래스 표면 */
  --g1: rgba(255,255,255,.04);
  --g2: rgba(255,255,255,.07);
  --g3: rgba(255,255,255,.12);
  --gb: rgba(255,255,255,.08);
  --gb2: rgba(255,255,255,.15);

  /* 텍스트 */
  --t1: rgba(255,255,255,1.00);
  --t2: rgba(255,255,255,0.62);
  --t3: rgba(255,255,255,0.36);
  --t4: rgba(255,255,255,0.18);

  /* 강조색 */
  --ac: #0a84ff;
  --acd: rgba(10,132,255,.12);
  --acb: rgba(10,132,255,.25);

  /* 시맨틱 */
  --gr: #30d158;  --grd: rgba(48,209,88,.10);   --grb: rgba(48,209,88,.22);
  --ye: #ffd60a;  --yed: rgba(255,214,10,.08);   --yeb: rgba(255,214,10,.20);
  --re: #ff453a;  --red: rgba(255,69,58,.08);    --reb: rgba(255,69,58,.20);
  --or: #ff9f0a;  --ord: rgba(255,159,10,.10);
  --pu: #bf5af2;  --pud: rgba(191,90,242,.12);   --pub: rgba(191,90,242,.25);

  /* 폰트 */
  --font-ui: 'Inter', 'Noto Sans KR', -apple-system, sans-serif;
  --font-mono: 'JetBrains Mono', monospace;

  /* 타이포 스케일 (모바일) */
  --f-xs: 11px;
  --f-sm: 12px;
  --f-base: 13px;
  --f-md: 14px;
  --f-lg: 16px;
  --f-xl: 28px;
  --f-hero: 72px;

  /* 스페이싱 */
  --sp-xs: 6px;
  --sp-sm: 10px;
  --sp-md: 16px;
  --sp-lg: 24px;

  /* 반경 */
  --r-sm: 8px;
  --r-md: 12px;
  --r-lg: 16px;
  --r-pill: 9999px;

  /* 레이아웃 고정값 */
  --topbar-h: 44px;
  --ticker-h: 26px;
  --bottomnav-h: 56px;
  --content-top: calc(var(--topbar-h) + var(--ticker-h));
}
```

### 3.2 레이아웃 고정 구조

```css
/* Topbar */
#topbar {
  position: fixed;
  top: 0; left: 0; right: 0;
  height: var(--topbar-h);
  z-index: 200;
  background: rgba(0,0,0,.85);
  backdrop-filter: blur(20px) saturate(180%);
  border-bottom: .5px solid var(--gb);
}

/* Ticker */
#ticker {
  position: fixed;
  top: var(--topbar-h); left: 0; right: 0;
  height: var(--ticker-h);
  z-index: 190;
  background: var(--l1);
  border-bottom: .5px solid var(--gb);
  overflow: hidden;
}

/* Content */
#content {
  margin-top: var(--content-top);
  padding-bottom: var(--bottomnav-h);
  min-height: 100dvh;
}

/* Bottom Nav */
#bottom-nav {
  position: fixed;
  bottom: 0; left: 0; right: 0;
  height: var(--bottomnav-h);
  z-index: 200;
  background: rgba(10,10,10,.92);
  backdrop-filter: blur(20px);
  border-top: .5px solid var(--gb);
  display: grid;
  grid-template-columns: repeat(4, 1fr);
}
```

---

## 4. 컴포넌트 구현 명세

### 4.1 Ticker 띠

```javascript
// 데이터 구조
const TICKER_DATA = [
  { label: 'S&P', value: '5,612', change: '+0.43%', up: true },
  { label: '코스피', value: '2,847', change: '-0.21%', up: false },
  { label: 'VIX', value: '18.2', change: '-1.2', up: false },
  { label: 'USD/KRW', value: '1,384', change: '+2.1', up: false },
  { label: '나스닥', value: '19,823', change: '+0.61%', up: true },
  { label: '코스닥', value: '812', change: '+0.15%', up: true },
];

// CSS 애니메이션: 좌→우 마르키 스크롤
// @keyframes ticker-scroll { from { transform: translateX(0) } to { transform: translateX(-50%) } }
// 속도: animation: ticker-scroll 30s linear infinite
// 데이터 2배 복제로 끊김 없는 루프
```

### 4.2 시장 온도 게이지 (반원형 아크)

```javascript
// SVG 기반
// viewBox: "0 0 280 160"
// 반원 아크: cx=140, cy=140, r=110
// stroke-dasharray 계산:
//   circumference = Math.PI * r  (반원)
//   filled = circumference * (score / 100)
//   dasharray = `${filled} ${circumference}`

// 온도별 색상:
//   0~30:  var(--re)  위험
//  30~50:  var(--ye)  주의
//  50~70:  var(--ac)  중립
//  70~100: var(--gr)  강세

// 텍스트: 숫자 72px mono + 상태 텍스트 16px
```

### 4.3 CTD 수평 스크롤 체인

```html
<!-- HTML 구조 -->
<div class="ctd-chain-wrap">
  <div class="ctd-chain">
    <div class="ctd-node" data-index="0">
      <div class="node-label">01</div>
      <div class="node-title">매크로 환경</div>
      <div class="node-summary">금리 4.45%</div>
    </div>
    <div class="ctd-arrow">→</div>
    <!-- 반복 × 5 -->
  </div>
</div>
```

```css
.ctd-chain-wrap {
  overflow-x: scroll;
  scroll-snap-type: x mandatory;
  -webkit-overflow-scrolling: touch;
  /* 우측 페이드아웃 힌트 */
  -webkit-mask-image: linear-gradient(to right, black 80%, transparent 100%);
  mask-image: linear-gradient(to right, black 80%, transparent 100%);
}

.ctd-chain {
  display: flex;
  align-items: center;
  gap: 0;
  width: max-content;
  padding: 0 var(--sp-md);
}

.ctd-node {
  width: 120px;
  flex-shrink: 0;
  scroll-snap-align: start;
  padding: 12px;
  border-radius: var(--r-md);
  background: var(--g1);
  border: .5px solid var(--gb);
  cursor: pointer;
  transition: background 150ms ease;
}

.ctd-node.active {
  background: var(--acd);
  border-color: var(--acb);
}

.ctd-arrow {
  color: var(--t4);
  font-size: 16px;
  padding: 0 8px;
  flex-shrink: 0;
}
```

```javascript
// 노드 클릭 → 상세 패널 토글
// 상세 패널: ctd-chain-wrap 아래 별도 div
// 클릭한 노드의 index에 맞는 데이터 렌더
```

### 4.4 레이더 차트

```javascript
// SVG viewBox: "0 0 260 240"
// 웹 v3와 동일 로직 그대로 재사용
// 8축, 5링 그리드, 데이터 폴리곤

function renderRadar(scores) {
  const CX = 130, CY = 120, R = 92, N = 8;
  const angles = Array.from({length: N}, (_, i) => 
    (i * 2 * Math.PI / N) - Math.PI / 2
  );
  // 폴리곤 포인트 계산
  const points = scores.map((s, i) => {
    const r = (s / 10) * R;
    return [
      CX + r * Math.cos(angles[i]),
      CY + r * Math.sin(angles[i])
    ];
  });
  // SVG polygon 업데이트
}
```

### 4.5 종목 칩 가로 스크롤

```html
<div class="stock-chips-wrap">
  <div class="stock-chips">
    <button class="chip active" data-stock="000660">
      <span class="chip-name">SK하이닉스</span>
      <span class="chip-score">8.5</span>
    </button>
    <!-- 반복 -->
  </div>
</div>
```

```css
.stock-chips-wrap {
  overflow-x: auto;
  scrollbar-width: none;
}
.stock-chips {
  display: flex;
  gap: 8px;
  padding: 0 var(--sp-md);
  width: max-content;
}
.chip {
  height: 44px;            /* 터치 타겟 */
  padding: 0 14px;
  border-radius: var(--r-pill);
  background: var(--g1);
  border: .5px solid var(--gb);
  white-space: nowrap;
}
.chip.active {
  background: var(--acd);
  border-color: var(--acb);
  color: var(--ac);
}
```

### 4.6 배지 시스템

```css
.badge {
  display: inline-flex;
  align-items: center;
  font-size: 10px;
  font-weight: 500;
  padding: 1px 7px;
  border-radius: 4px;
  border: .5px solid;
  white-space: nowrap;
  font-family: var(--font-ui);
}

.t-core { background: var(--acd); color: var(--ac);  border-color: var(--acb); }
.t-bull { background: var(--grd); color: var(--gr);  border-color: var(--grb); }
.t-warn { background: var(--yed); color: var(--ye);  border-color: var(--yeb); }
.t-risk { background: var(--red); color: var(--re);  border-color: var(--reb); }
.t-act  { background: var(--ord); color: var(--or);  border-color: var(--or);  }
.t-hold { background: var(--g2);  color: var(--t3);  border-color: var(--gb);  }
```

---

## 5. JavaScript 아키텍처

### 5.1 상태 관리

```javascript
const STATE = {
  activeTab: 'market',        // 'market' | 'stocks' | 'invest' | 'more'
  activeStock: '000660',      // 선택된 종목 코드
  stockGroup: 'domestic',     // 'domestic' | 'overseas'
  activeCTDNode: null,        // 활성 CTD 노드 index
  activeRadarAxis: null,      // 드릴다운 중인 레이더 축
};
```

### 5.2 탭 전환 로직

```javascript
function switchTab(tabId) {
  STATE.activeTab = tabId;
  
  // 모든 탭 패널 숨김
  document.querySelectorAll('.tab-pane').forEach(p => p.hidden = true);
  
  // 선택 탭 표시
  document.getElementById(`tab-${tabId}`).hidden = false;
  
  // Bottom Nav 활성 상태
  document.querySelectorAll('.nav-item').forEach(item => {
    item.classList.toggle('active', item.dataset.tab === tabId);
  });
}
```

### 5.3 종목 선택 → Zone 4 업데이트

```javascript
function selectStock(code) {
  STATE.activeStock = code;
  
  // 칩 활성 상태 업데이트
  document.querySelectorAll('.chip').forEach(chip => {
    chip.classList.toggle('active', chip.dataset.stock === code);
  });
  
  // Zone 4 데이터 교체 (즉각, 0ms)
  const stock = STOCK_DATA[code];
  renderZone4(stock);
  
  // Zone 4가 보이도록 스크롤
  document.getElementById('zone4').scrollIntoView({ behavior: 'smooth', block: 'start' });
}
```

### 5.4 목업 데이터 구조

```javascript
const MARKET_DATA = {
  temperature: 62,
  status: '분할 매수 구간',
  summary: 'EPS 성장 > 주가 상승 — 지금이 기회',
  quickMetrics: [
    { label: 'VIX', value: '18.2', status: 'bull' },
    { label: 'F&G', value: '62', status: 'warn' },
    { label: '환율', value: '1,384', status: 'warn' },
    { label: '금리', value: '4.45%', status: 'warn' },
    { label: '코스피', value: '2,847', status: 'hold' },
    { label: 'S&P', value: '5,612', status: 'bull' },
  ],
  supplyData: {
    foreign: { direction: -1, amount: '-4,200억', label: '외국인' },
    institution: { direction: 1, amount: '+1,800억', label: '기관' },
    individual: { direction: 1, amount: '+2,400억', label: '개인' },
    judgment: '기관 소폭 매수 · 외국인 차익실현 — 단기 경계'
  }
};

const STOCK_DATA = {
  '000660': {
    name: 'SK하이닉스',
    code: '000660',
    price: 2134000,
    change: +2.3,
    score: 8.5,
    radarScores: [8.2, 9.1, 7.8, 6.5, 8.8, 8.0, 7.2, 8.5],
    // 레이더 8축: 비즈니스품질·성장모멘텀·밸류에이션·시장타이밍·재무건전성·매크로연계·리스크관리·세후수익률
    strengths: ['성장 모멘텀', '재무 건전성'],
    weaknesses: ['시장 타이밍'],
    ctdChain: [/* 5노드 데이터 */],
    validity: [/* 유효성 행 데이터 */],
    buyPlan: {
      current: { range: [2000000, 2400000], weight: 30 },
      dip1: { range: [1700000, 2000000], weight: 40 },
      dip2: { range: [1300000, 1700000], weight: 30 },
      target: 3800000,
      stopLoss: 1600000,
    }
  },
  // 나머지 9개 종목...
};
```

---

## 6. 구현 순서 (Claude Code 실행 순서)

```
Step 1: HTML 쉘 + CSS 변수 + Reset
Step 2: 레이아웃 (Topbar + Ticker + Content + BottomNav)
Step 3: 탭 전환 JS 로직
Step 4: 시장 탭 — 온도 게이지 SVG
Step 5: 시장 탭 — CTD 수평 스크롤 체인
Step 6: 시장 탭 — 수급 바 + 종목 신호
Step 7: 종목 탭 — 종목 칩 가로 스크롤
Step 8: 종목 탭 — Zone 4 전체 (레이더 + 매수 플랜)
Step 9: 투자 탭
Step 10: 더보기 탭
Step 11: Ticker 마르키 애니메이션
Step 12: 전체 데이터 목업 완성 + 폴리싱
```

---

## 7. Claude Code 프롬프트 (복사해서 사용)

```
다음 스펙에 따라 connecting_dots_mobile.html을 구현해줘.

참고 파일:
- investiq_web_v3.html (디자인 시스템 참고)
- CTD_Mobile_System_Architecture.md (이 문서)
- CTD_Mobile_UXUI_Brief.md (UI 브리핑)

구현 조건:
1. 단일 HTML 파일 (CSS/JS 인라인)
2. 375px 기준, 430px까지 자연 확장
3. 디자인 토큰은 CSS 변수로 전체 정의
4. 하드코딩 목업 데이터 사용 (API 연동 없음)
5. 위 문서의 Step 1부터 순서대로 구현

시작: Step 1 (HTML 쉘 + CSS 변수 + Reset)
```

---

## 8. 웹 v3 보존 원칙

```
investiq_web_v3.html  →  절대 수정하지 않음
connecting_dots_mobile.html  →  신규 파일로 분리 구현

공유 요소 (복사해서 사용):
  - CSS 변수 토큰 (동일)
  - 레이더 SVG 렌더링 함수
  - 배지 CSS 클래스
  - 종목 데이터 구조
```

---

*커넥팅닷 모바일 시스템 아키텍처 v1.0 — 2026.06.04*
