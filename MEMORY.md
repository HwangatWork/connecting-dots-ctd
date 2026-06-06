# MEMORY.md — CTD 프로젝트 진행 상태

> 세션 간 컨텍스트 브릿지. 새 세션 시작 시 CLAUDE.md → AGENTS.md → 이 파일 순서로 읽는다.
> 최종 업데이트: 2026-06-06 (P0 완료, Range Check 구현)

---

## 현재 진행 상태

**버전**: v1.1
**백엔드 live 커밋**: `ecf27e0` (2026-06-06 — Range Check + CNN F&G + 5지표)
**프론트 live 버전**: CTD v1.1 — auto-deploy enabled (Netlify, 2026-06-06)

---

## 오늘(2026-06-06) 완료된 작업

| 작업 | 커밋 | 상태 |
|------|------|------|
| Agentic Engineering 환경 구축 (CLAUDE.md, ROADMAP, commands/) | `cfdaa07` | ✅ |
| 루트 폴더 정리 (doc/, old/ 이동) | `e4dab46` | ✅ |
| Render auto-deploy 복구 (GitHub Actions) | `d793535` | ✅ |
| 보안 처리 (API 키 rotate, .env.example, .gitignore) | `d2dcf18` | ✅ |
| Netlify GitHub Actions 자동 배포 구축 | `d2dcf18` | ✅ |
| AGENTS.md DO NOT 6 추가 + F&G CNN 소스 교체 | `329caa8` | ✅ |
| 현황 탭 5개 지표 추가 + ticker/market API 확장 | `18ec9c6` | ✅ |
| Range Check + Staleness Check + status.html 경고 컬럼 | `ecf27e0` | ✅ |

---

## 주요 결정

### 배포 아키텍처
- **Render rootDir = `backend`**: `backend/requirements.txt`가 실제 빌드에 사용됨.
- **Netlify = GitHub Actions 자동 배포**: `frontend/**` push 시 자동 배포.
  커밋 후 2-3분 내 https://connecting-dots-ctd.netlify.app 에 반영.
- **Render = GitHub Actions 자동 배포**: `backend/**` push 시 자동 배포.
  빌드 시간 3-5분 + 콜드 스타트 최대 2분.

### 데이터 방법론 수정 (P0 완료)
- **F&G 소스**: Alternative.me (크립토 기반) → CNN `production.dataviz.cnn.io` (주식시장 기반)
  - 로컬 직접 호출 테스트: score=42.06, rating="fear"
  - Render live 확인: fg_index.value_hint="42", provider="CNN", status="정상"
- **현황 탭 추가 지표**: DOW (ic-dow), DXY (ic-dxy), 장단기금리차 (ic-spread),
  SKEW (ic-skew), 수급금액 (ic-fflow)

### Range Check 구현
- VIX: 10-80 / CNN F&G: 0-100 / KOSPI: 1500-3500 / 10Y금리: 0.3-7.0%
- DXY: 80-130 / SKEW: 100-180 / T10Y2Y: -3~5%
- /api/v1/status 응답에 `range_check`, `is_stale` 필드 추가
- summary에 `validation_warnings`, `stale_count` 추가
- status.html에 ✅/⚠️/🔴 검증 컬럼 추가

### Agentic Engineering 원칙
- Plan-First → Evidence-First → DEV 사이클(D→E→V→C) 정립
- 완료 기준: 실제 URL fetch 결과로만 판단
- AGENTS.md DO NOT 6개 (commit 후 push까지 완료해야 작업 완료)

---

## 미해결 이슈

### 🟡 MEDIUM — Yahoo Finance 장 외 시간 fallback
- `fast_info.last_price` 장 외 시간 None 반환
- `/api/v1/status` real_ratio 장 외 ~22%, 장중 기대치 60%+
- 해결 방안: `ticker.info` fallback 또는 장중 여부 체크 로직

### 🟡 MEDIUM — ticker 레이블 불일치
- JS `_applyTickerToStatus` 에서 `'S&P'` → ticker는 `'S&P 500'` (불일치)
- `'나스닥'` → ticker는 `'NASDAQ'` (불일치)
- DOW, DXY, SKEW는 정상 매핑

### 🟢 LOW — Render free tier 콜드 스타트
- 15분 비활성 시 슬립, wake-up 최대 2분 소요
- 해결: Render 유료 플랜 전환 또는 cron ping

---

## 다음 세션 우선순위

1. **ticker 레이블 불일치 수정** — S&P 500, NASDAQ 현황 탭 업데이트 안 됨
2. **Yahoo Finance 장중 실데이터** — real_ratio 60%+ 달성
3. **지표 카드 갱신 시각 표시** — 현황 탭 각 카드 하단에 `출처 | 갱신: HH:MM`
4. **/status 비교 테이블** — raw 값 vs CTD 계산값 오차 컬럼
5. **에러 상태 UI** — API 실패 시 사용자 메시지

---

## 핵심 환경 정보

```
Render 서비스 ID : srv-d8gv8l0jo6nc73e299e0
Render API key  : <GitHub Secrets: RENDER_API_KEY>  ← Render 대시보드에서 발급
Netlify site ID : 0f762967-47e8-4fab-9528-0a4fa0fbeb98
Netlify token   : <GitHub Secrets: NETLIFY_AUTH_TOKEN>  ← Netlify User Settings에서 발급
GitHub repo     : HwangatWork/connecting-dots-ctd
branch          : master
```
