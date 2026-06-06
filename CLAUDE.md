# CTD — 커넥팅닷 프로젝트 헌법

> 새 세션 시작 시 이 파일을 **반드시 먼저** 읽는다.
> 위반 패턴은 AGENTS.md 참조.

## 프로젝트 개요

**커넥팅닷(CTD)** — 한국 개인 투자자용 실시간 투자 판단 모바일 웹앱.
64개 지표를 수집·가공해 시장 온도(0-100), 종목 IQ 스코어(8축), CTD 체인(5노드)을 제공한다.

- **백엔드**: https://connecting-dots-ctd.onrender.com
- **프론트엔드**: https://connecting-dots-ctd.netlify.app
- **관리 페이지**: https://connecting-dots-ctd.netlify.app/status (패스코드: adminjy)
- **GitHub**: https://github.com/HwangatWork/connecting-dots-ctd

---

## 기술 스택

| 레이어 | 기술 |
|--------|------|
| 백엔드 | Python 3.11 + FastAPI + uvicorn |
| 데이터 | yfinance, pykrx, Alternative.me, FRED |
| 프론트 | Vanilla JS 단일 HTML (빌드 없음) |
| 배포 | Render.com (백엔드) + Netlify CLI (프론트) |
| MCP | Render MCP (API key 등록됨, 다음 세션부터 툴 사용 가능) |

---

## 폴더 구조

```
AI Investment/
├── frontend/
│   ├── index.html          # 단일 HTML 모바일 웹앱 (v1.1)
│   └── status.html         # 데이터 상태 관리 페이지 (패스코드 보호)
├── backend/
│   ├── main.py             # FastAPI 진입점 + 라우터 등록
│   ├── config.py           # 종목 마스터, 가중치, TTL 상수
│   ├── schemas.py          # Pydantic 응답 모델
│   ├── cache.py            # TTL 인메모리 캐시
│   ├── data_registry.py    # 지표별 실데이터/폴백 추적 레지스트리
│   ├── requirements.txt    # Python 의존성 (Render 빌드 시 사용)
│   ├── tests/              # pytest 테스트 (test_imports, test_encoding, test_health)
│   ├── routers/            # market, stocks, ticker, status
│   ├── services/           # market_service, stock_service, score_engine, technical
│   └── providers/          # yahoo_finance, krx, fear_greed, fred
├── .claude/
│   └── commands/           # 슬래시 커맨드 (deploy, status-check, new-feature)
├── .github/
│   └── workflows/          # render-deploy.yml (backend/** 변경 시 자동 배포)
├── doc/                    # 설계 문서 (ARCHITECTURE.md, render.yaml.reference 등)
├── old/                    # 레거시 및 불필요 파일 보관
├── AGENTS.md               # DO NOT 패턴 (실제 사고 기반)
├── CLAUDE.md               # 이 파일
├── ROADMAP.md              # 기능 로드맵
└── netlify.toml            # Netlify 배포 설정
```

---

## 배포 설정 (중요)

### Render 백엔드
- **서비스 ID**: `srv-d8gv8l0jo6nc73e299e0`
- **rootDir**: `backend` (빌드/실행 기준 디렉토리)
- **buildCommand**: `pip install -r requirements.txt` → `backend/requirements.txt` 사용
- **startCommand**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- **region**: ohio / **plan**: free (15분 비활성 시 슬립)
- ⚠️ **auto-deploy**: GitHub Actions (`.github/workflows/render-deploy.yml`) 으로 복구.
  `RENDER_API_KEY` secret이 GitHub에 등록되어 있어야 `backend/**` push 시 자동 배포.

### Netlify 프론트엔드
- **배포 방식**: GitHub 자동 배포 ❌ → **CLI 수동 배포** 필요
- **배포 명령어**: `npx netlify-cli deploy --prod --dir=frontend`
- **Pretty URL**: Netlify가 `href="/status.html"` → `href="/status"` 자동 변환됨.

---

## DEV 사이클 — Define → Execute → Verify → Checkpoint

모든 작업은 이 4단계를 순서대로 거친다.

```
D  Define     완료 기준을 먼저 정의한다.
               "무엇이 true이면 이 작업이 완료인가?"를 코드 작성 전에 명시한다.

E  Execute    구현한다. Plan-First 승인 후에만 시작.

V  Verify     실제 URL/실행 출력으로 증거를 수집한다. (Evidence-First)
               증거 없는 완료 선언은 금지.

C  Checkpoint 다음 작업 시작 전 현재 상태를 기록한다.
               컨텍스트 임계값 도달 시 반드시 실행.
```

---

## Evidence-First 규칙

Verify 단계는 반드시 **실제 출력값**을 응답에 포함한다.

| 검증 대상 | 증거 형식 |
|-----------|-----------|
| Netlify 배포 | `curl` 결과의 tab IDs, version 값 |
| Render 서버 | `{"status":"ok","timestamp":"..."}` 전체 |
| pytest | `X passed, Y failed` 숫자 포함 출력 |
| API 응답 | 실제 JSON 일부 |

**금지:**
- "정상 작동 중입니다" (서술형 완료 선언)
- "배포가 완료되었습니다" (URL 검증 없이)
- "테스트가 통과했습니다" (pytest 출력 없이)

---

## Context 임계값

| 임계값 | 조치 |
|--------|------|
| **50%** | ROADMAP.md 진행 중 항목 업데이트 |
| **70%** | CLAUDE.md 재독하여 컨텍스트 재확인, 남은 작업 명시 |
| **90%** | 즉시 작업 중단 → 현재 상태 커밋 → 사용자에게 보고 후 세션 종료 대기 |

---

## Task Completion Report 양식

작업 완료 시 아래 형식으로 출력한다.

```
## Task Completion Report

**완료 항목**
- [항목 1]: [증거 한 줄]
- [항목 2]: [증거 한 줄]

**증거**
[실제 출력값 — curl 결과, pytest 출력, git log 등]

**미해결**
- [이슈 1]: [상태 및 원인]

**다음 세션 시작점**
1. [첫 번째 할 일]
```

---

## API 엔드포인트

```
GET  /api/v1/health          → 서버 상태 + 캐시 통계
GET  /api/v1/ticker          → 시세 티커 (캐시 60s)
GET  /api/v1/market          → 시장 탭 전체 (캐시 300s)
GET  /api/v1/stocks          → 종목 리스트 (캐시 900s)
GET  /api/v1/stocks/{code}   → 종목 상세
GET  /api/v1/status          → 64개 지표 수집 상태
DELETE /api/v1/cache         → 전체 캐시 초기화
```

---

## 현재 구현 상태 (v1.1)

### 프론트엔드
- 하단 4탭: 시장 / 현황 / 종목 / 투자
- **시장 탭**: 온도계, CTD 5노드 체인, 수급, 시장 국면, 신호 요약
- **현황 탭**: 글로벌 자산 / 국내 자산 / 매크로&심리 / 유동성 / 수급 지표 카드 + API 실데이터 연동, ⚙️ → /status
- **종목 탭**: 국내/해외 종목 리스트 + Zone 4 상세 (레이더, 매수 플랜, 드릴다운)
- **투자 탭**: 포트폴리오 통계 / 배분 / 세금계산기 / AI 분석 / 알림 설정

### 백엔드
- 64개 지표 수집 (Yahoo Finance, pykrx, FRED, Alternative.me)
- 8축 IQ 스코어 + 시장 온도 계산
- data_registry: 지표별 실데이터/폴백 상태 추적
- TTL 캐시 (ticker 60s / market 300s / stocks 900s)

### Agentic Engineering 환경
- CLAUDE.md, AGENTS.md, ROADMAP.md
- `.claude/commands/` (deploy / status-check / new-feature)
- `backend/tests/` (test_imports / test_encoding / test_health)
- `.github/workflows/render-deploy.yml`

---

## 디자인 토큰 (절대 변경 불가)

```css
--bg:  #000000       /* 배경 */
--ac:  #0a84ff       /* 액센트 (파랑) */
--gr:  #30d158       /* 상승/긍정 */
--ye:  #ffd60a       /* 주의 */
--re:  #ff453a       /* 위험/하락 */
font: Inter + Noto Sans KR (UI), JetBrains Mono (숫자)
base-width: 375px (모바일 우선)
```

---

## Ground Rules

1. **Plan-First 필수**: 코드 작성 전 반드시 계획을 보여주고 승인받는다.
2. **Evidence-First**: Verify는 실제 출력값 제시. 서술형 완료 선언 금지.
3. **완료 기준**: GitHub push + Netlify CLI 배포 + 실제 URL 검증 통과.
4. **UTF-8 NoBOM**: 한글 포함 Python 파일은 반드시 UTF-8 BOM 없이 저장.
5. **배포 실패 즉시 대응**: Render 서버 다운 시 로그 확인 후 원인 수정, 재배포까지 완료.
6. **디자인 토큰 불변**: 위 CSS 변수값 변경 금지.
7. **old/ 수정 금지**: 레거시 파일은 참고용, 절대 수정하지 않는다.
8. **커밋 단위**: 논리적 단위 1커밋. 메시지는 `type: 한글 설명` 형식.
9. **AGENTS.md 준수**: DO NOT 패턴 5개를 작업 전 확인한다.

---

## 로컬 개발 및 배포

```bash
# 백엔드 실행
cd backend && uvicorn main:app --reload --port 8000

# Import + 인코딩 테스트
cd backend && python -m pytest tests/ -v

# 프론트엔드 배포 (Netlify CLI 수동)
npx netlify-cli deploy --prod --dir=frontend

# Render 수동 배포 트리거
curl -X POST https://api.render.com/v1/services/srv-d8gv8l0jo6nc73e299e0/deploys \
  -H "Authorization: Bearer <RENDER_API_KEY>" \
  -H "Content-Type: application/json" \
  -d '{"clearCache": "do_not_clear"}'
```

---

## 새 세션 시작 루틴

1. 이 파일 읽기 (완료)
2. `AGENTS.md` 읽기 — DO NOT 패턴 재확인
3. `ROADMAP.md` 읽어 현재 우선순위 파악
4. `git log --oneline -5`로 최근 커밋 확인
5. `claude mcp list`로 Render MCP 연결 확인
6. `/status-check` 실행으로 서버 상태 점검
7. 작업 시작 전 반드시 Plan-First
