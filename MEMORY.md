# MEMORY.md — CTD 프로젝트 진행 상태

> 세션 간 컨텍스트 브릿지. 새 세션 시작 시 CLAUDE.md → AGENTS.md → 이 파일 순서로 읽는다.
> 최종 업데이트: 2026-06-06

---

## 현재 진행 상태

**버전**: v1.1
**백엔드 live 커밋**: `5d15dbb` (2026-06-06 — GitHub Actions 자동 배포 완성)
**프론트 live 버전**: CTD v1.1 — auto-deploy enabled (Netlify Actions 자동 배포, 2026-06-06)

---

## 오늘(2026-06-06) 완료된 작업

| 작업 | 커밋 | 상태 |
|------|------|------|
| Agentic Engineering 환경 구축 (CLAUDE.md, ROADMAP, commands/) | `cfdaa07` | ✅ |
| 루트 폴더 정리 (doc/, old/ 이동) | `e4dab46` | ✅ |
| Render rootDir=backend 확인, 불필요 파일 이동 | `c77574d` | ✅ |
| CLAUDE.md 오늘 작업 내용 반영 | `0a7814c` | ✅ |
| Render auto-deploy 복구 (GitHub Actions) | `d793535` | ✅ |
| AGENTS.md 작성 (DO NOT 패턴 5개) | 미push | ✅ |
| CLAUDE.md 강화 (DEV 사이클, Evidence-First, TCR) | 미push | ✅ |
| MEMORY.md 작성 | 미push | ✅ |
| backend/tests/ 테스트 하네스 | 미push | 🔄 진행 중 |

---

## 주요 결정

### 배포 아키텍처
- **Render rootDir = `backend`**: `backend/requirements.txt`가 실제 빌드에 사용됨.
  루트 `requirements.txt`, `Procfile`, `runtime.txt`는 `old/`로 이동.
- **Netlify = CLI 수동 배포**: `npx netlify-cli deploy --prod --dir=frontend`.
  GitHub 자동 배포 미연결 상태.
- **render.yaml** 실제 서비스와 불일치 → `doc/render.yaml.reference`로 이동.
  Render 설정은 대시보드가 정본.

### Agentic Engineering 원칙
- Plan-First → Evidence-First → DEV 사이클(D→E→V→C) 정립
- 완료 기준: 실제 URL fetch 결과로만 판단
- AGENTS.md에 실제 사고 5건 기록

---

## 미해결 이슈

### 🟡 MEDIUM — Yahoo Finance 장 외 시간 fallback
- `fast_info.last_price` / `previous_close` 장 외 시간 None 반환
- `/api/v1/status` real_ratio 장 외 ~20%, 장중 기대치 60%+
- 해결 방안: `ticker.info` fallback 또는 장중 여부 체크 로직 추가

### 🟢 LOW — Render free tier 콜드 스타트
- 15분 비활성 시 슬립, wake-up 최대 2분 소요
- 해결: Render 유료 플랜 전환 또는 cron ping

---

## 다음 세션 우선순위

1. **Yahoo Finance 장중 실데이터** — real_ratio 60%+ 달성
2. **현황 탭 마지막 갱신 시각** — 지표 카드에 timestamp 표시
3. **에러 상태 UI** — API 실패 시 사용자 메시지
4. **종목 탭 검색 기능**

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
