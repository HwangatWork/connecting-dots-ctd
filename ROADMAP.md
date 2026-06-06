# CTD 로드맵

<!-- ROADMAP Hook
마커: [x]=완료  [ ]=자동실행  [?]=판단필요(멈춤)
hook: .claude/hooks/roadmap_runner.sh (Stop hook, exit 2)
증거: .claude/.last_evidence (pytest + curl, 태스크마다 초기화 후 기록)

[?] 재개 절차:
  1. ROADMAP.md 해당 [?] 줄 → [ ] (진행) 또는 [x] (건너뜀) 으로 수정
  2. Claude에게 "계속" 입력 → hook이 다음 [ ] 자동 실행

무한루프 방지:
  - 동일 태스크 3회 미완료 시 중단 (.hook_state 삭제로 리셋)
  - [?] 동일 질문 3회 반복 시 강조 경고
  - .last_evidence: mtime + 태스크명 grep 둘 다 통과해야 증거 인정
-->

---

## ✅ 완료

### 인프라
- [x] FastAPI 백엔드 구조 (routers / services / providers / cache)
- [x] Render.com 배포 (https://connecting-dots-ctd.onrender.com)
- [x] Netlify 배포 (https://connecting-dots-ctd.netlify.app)
- [x] render.yaml + netlify.toml 설정
- [x] Render MCP 연결
- [x] GitHub Actions 자동 배포 — backend/** → Render (API 트리거)
- [x] Render Auto-Deploy OFF — GitHub Actions 단독 트리거
- [x] .claude/settings.json — bypassPermissions + mcp__render__* 전체 등록
- [x] .claude/hooks/roadmap_runner.sh — Stop hook 등록 (5/5 테스트 통과)

### 데이터 수집
- [x] FinanceDataReader: 10개 지수 현재가 (S&P500=7384, NASDAQ=25709, 금=4337 실측)
- [x] FRED: 연준 총자산(WALCL), 장단기금리차(T10Y2Y)
- [x] CNN Fear & Greed Index (Alternative.me 크립토 → CNN 주식 교체)
- [x] data_registry: 지표별 실데이터/폴백 상태 추적
- [x] Range Check: FDR 가격 범위 검증 (벗어나면 "점검 중")
- [x] HTML 플레이스홀더 제거 (5,612 등 하드코딩 → "—")

### 백엔드 API
- [x] GET /api/v1/ticker (FDR 10개 지수, 실시간)
- [x] GET /api/v1/market (시장 온도, CTD 체인, 수급, 국면)
- [x] GET /api/v1/stocks, /stocks/{code}
- [x] GET /api/v1/status (64개 지표 수집 상태)
- [x] DELETE /api/v1/cache

### 프론트엔드
- [x] 단일 HTML 모바일 웹앱 (375px 기준)
- [x] 하단 4탭: 시장 / 현황 / 종목 / 투자
- [x] 현황 탭: 글로벌/국내/매크로/유동성/수급 지표 카드 + API 연동

---

## P0 — 데이터 정확성 (즉시)

- [x] FRED 복구 방식 결정 — 옵션 A (공식 API 키, api.stlouisfed.org)
- [x] yfinance 잔재 호출 경로 완전 제거 (Render 로그 429 박멸)
- [x] 하드코딩 지표 확인 (M2/역RP/FED자산/HY스프레드) → "점검 중" 처리 (FRED API 키 발급 후 실데이터 전환)

## P1 — UX/UI

- [x] 색상 한국식 전환: 등락은 상승=빨강/하락=파랑, 상태(경고/위험)는 빨강 유지·톤 구분
- [x] 뱃지 버그 수정: 등락률 기반 계산, 값 없으면 "점검 중"
- [x] "점검 중" 카드 표기 통일 + 수급 헤더 잔재 제거

## P0 보류 — FRED API 키 대기

- [x] FRED 4개 복구 (US10Y/DXY/T10Y2Y/연준자산) — 공식 API 키 연동 완료 (api.stlouisfed.org, DGS10/DTWEXBGS/T10Y2Y/WALCL 실값 확인)

---

## P2 — 기능 확장 (이후)

- [ ] 종목 즐겨찾기 (localStorage)
- [ ] 포트폴리오 실제 입력 기능
- [ ] 푸시 알림 (시장 온도 임계값)
- [ ] 종목 탭 검색 기능

## P3 — 인프라 (이후)

- [ ] Render 유료 플랜 전환 (슬립 제거)
- [ ] 수급 데이터 복구 (pykrx 대체 또는 KRX 직접 API)
