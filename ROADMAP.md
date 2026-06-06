# CTD 로드맵

최종 업데이트: 2026-06-06

---

## ✅ 완료

### 인프라
- [x] FastAPI 백엔드 구조 (routers / services / providers / cache)
- [x] Render.com 배포 (https://connecting-dots-ctd.onrender.com)
- [x] Netlify 배포 (https://connecting-dots-ctd.netlify.app)
- [x] render.yaml + netlify.toml 설정
- [x] Render MCP 연결 (claude mcp add render)

### 데이터 수집 (64개 지표)
- [x] Yahoo Finance: 시장지수 9개 (S&P500, NASDAQ, DOW, 닛케이, VIX, WTI, 금, KRW, SKEWe)
- [x] pykrx: 코스피, 코스닥, 수급(외국인/기관/개인)
- [x] FRED: 연준 총자산(WALCL), 장단기금리차(T10Y2Y)
- [x] Alternative.me: Fear & Greed Index
- [x] data_registry: 지표별 실데이터/폴백 상태 추적
- [x] 429 재시도 로직 (yfinance 0.5s delay + 지수 백오프)

### 백엔드 API
- [x] GET /api/v1/ticker
- [x] GET /api/v1/market (시장 온도, CTD 체인, 수급, 국면)
- [x] GET /api/v1/stocks, /stocks/{code}
- [x] GET /api/v1/status (64개 지표 수집 상태)
- [x] DELETE /api/v1/cache

### 프론트엔드
- [x] 단일 HTML 모바일 웹앱 (375px 기준)
- [x] 하단 4탭: 시장 / 현황 / 종목 / 투자
- [x] 시장 탭: 온도계, CTD 체인, 수급 바, 시장 국면
- [x] 현황 탭: 글로벌/국내/매크로/유동성/수급 지표 카드 + API 연동
- [x] 현황 탭 ⚙️ → /status.html 링크
- [x] 종목 탭: 국내/해외 리스트, Zone 4 상세 (레이더, 매수 플랜, 드릴다운)
- [x] 투자 탭: 포트폴리오 통계, 세금 계산기, 알림 설정, footer
- [x] 스켈레톤 로딩 애니메이션
- [x] 티커 띠 (자동 갱신 60s)

### Agentic Engineering 환경
- [x] CLAUDE.md (프로젝트 헌법)
- [x] .claude/commands/ (deploy, status-check, new-feature)
- [x] ROADMAP.md (이 파일)
- [x] /status.html 관리 페이지 (패스코드 adminjy, 64개 지표 상태 테이블)

---

## 🔄 진행 중

- [ ] Netlify 라이브 배포 최신화 (현황 탭 포함 버전 반영)

---

## 📋 예정 (우선순위별)

### P1 — 데이터 품질
- [ ] Yahoo Finance fast_info 장중 실데이터 개선 (현재 장 외 시간 fallback)
- [ ] pykrx 수급 데이터 현황 탭 실시간 연동 확인
- [ ] FRED HY spread 실시간 수집 (현재 하드코딩 3.8%)

### P1 — UX
- [ ] 현황 탭 마지막 갱신 시각 표시
- [ ] 종목 탭 검색 기능
- [ ] 에러 상태 UI (API 실패 시 사용자 메시지)

### P2 — 기능 확장
- [ ] 종목 즐겨찾기 (localStorage)
- [ ] 포트폴리오 실제 입력 기능 (현재 목업 데이터)
- [ ] 푸시 알림 (시장 온도 임계값)
- [ ] 한국 주요 ETF 추가 (KODEX 반도체 등)

### P3 — 인프라
- [ ] Render 유료 플랜 전환 (슬립 제거, 응답 속도 개선)
- [ ] 백엔드 테스트 추가 (pytest, import 검증 자동화)
- [ ] CI/CD (GitHub Actions: push → 자동 import 테스트)

---

## 알려진 이슈

| 이슈 | 원인 | 상태 |
|------|------|------|
| Render 콜드 스타트 30-60초 | Free tier 15분 슬립 | 방치 (유료 전환 시 해결) |
| Yahoo Finance 장 외 fallback | fast_info.last_price=None | 방치 (장중 자동 해결) |
| pykrx 일부 종목 데이터 누락 | KRX API 비정기 변경 | 모니터링 중 |
