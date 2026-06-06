#!/usr/bin/env bash
# .claude/hooks/roadmap_runner.sh — ROADMAP 자동 실행 Stop Hook
#
# 재개 절차: ROADMAP.md에서 [?] → [ ] or [x] 수정 후 "계속" 입력
set -euo pipefail

HOOKS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$HOOKS_DIR/../.." && pwd)"

# 테스트 시 환경변수로 경로 오버라이드 가능
ROADMAP="${ROADMAP_OVERRIDE:-$PROJECT_DIR/ROADMAP.md}"
STATE_FILE="${STATE_FILE_OVERRIDE:-$HOOKS_DIR/../.hook_state}"
EVIDENCE_FILE="${EVIDENCE_FILE_OVERRIDE:-$HOOKS_DIR/../.last_evidence}"
MAX_FAIL=3

# ── 파일 수정 시각 (GNU + BSD 호환) ─────────────────────────────────────────
file_mtime() {
  stat -c %Y "$1" 2>/dev/null || stat -f %m "$1" 2>/dev/null || echo 0
}

# ── 상태 파일 읽기 (Bug1: set +e로 grep 실패 완전 격리) ─────────────────────
LAST_TASK=""; START_TS=0; FAIL_COUNT=0; Q_TASK=""; Q_COUNT=0
if [ -f "$STATE_FILE" ]; then
  set +e
  LAST_TASK=$( grep '^TASK:'       "$STATE_FILE" | cut -d: -f2-)
  START_TS=$(  grep '^START_TS:'   "$STATE_FILE" | cut -d: -f2)
  FAIL_COUNT=$(grep '^FAIL_COUNT:' "$STATE_FILE" | cut -d: -f2)
  Q_TASK=$(    grep '^Q_TASK:'     "$STATE_FILE" | cut -d: -f2-)
  Q_COUNT=$(   grep '^Q_COUNT:'    "$STATE_FILE" | cut -d: -f2)
  set -e
  LAST_TASK=${LAST_TASK:-""}
  START_TS=${START_TS:-0}
  FAIL_COUNT=${FAIL_COUNT:-0}
  Q_TASK=${Q_TASK:-""}
  Q_COUNT=${Q_COUNT:-0}
fi

# ── 첫 번째 미완료 항목 탐색 ─────────────────────────────────────────────────
NEXT_LINE=$(grep -n '^\- \[[ ?]\]' "$ROADMAP" 2>/dev/null | head -1 || true)

# ── 전체 완료 ────────────────────────────────────────────────────────────────
if [ -z "$NEXT_LINE" ]; then
  rm -f "$STATE_FILE"
  echo "✅ ROADMAP: P0/P1 모든 항목 완료"
  exit 2
fi

ITEM=$(echo "$NEXT_LINE" | sed 's/^[0-9]*:- //')

# ── [?] 판단 필요 (Bug3: 반복 카운트) ──────────────────────────────────────
if echo "$ITEM" | grep -q '^\[?\]'; then
  TEXT=$(echo "$ITEM" | sed 's/^\[?\] //')

  if [ "$TEXT" = "$Q_TASK" ]; then
    Q_COUNT=$((Q_COUNT + 1))
  else
    Q_COUNT=1
  fi
  printf 'Q_TASK:%s\nQ_COUNT:%d\n' "$TEXT" "$Q_COUNT" > "$STATE_FILE"

  REPEAT_WARN=""
  if [ "$Q_COUNT" -ge 3 ]; then
    REPEAT_WARN=" ⚠️ ${Q_COUNT}회 반복 — ROADMAP.md 수정이 반드시 필요합니다."
  fi

  cat <<MSG
⏸ [ROADMAP 판단 필요]${REPEAT_WARN}

태스크: $TEXT

재개 방법:
  1. ROADMAP.md 해당 줄 수정
       진행 결정   → [?] 를 [ ] 로
       건너뜀 결정 → [?] 를 [x] 로
  2. Claude에게 "계속" 입력
MSG
  exit 2
fi

# ── [ ] 실행 항목 ────────────────────────────────────────────────────────────
TASK_TEXT=$(echo "$ITEM" | sed 's/^\[ \] //')

# ── 동일 태스크 재진입 (미완료 감지) ────────────────────────────────────────
if [ "$TASK_TEXT" = "$LAST_TASK" ]; then
  EVIDENCE_TS=$(file_mtime "$EVIDENCE_FILE")

  # hook-triggered 완료 턴에서만 실패 카운트 증가 ("1" 또는 "true" 모두 처리)
  if [ "${STOP_HOOK_ACTIVE:-0}" = "1" ] || [ "${STOP_HOOK_ACTIVE:-0}" = "true" ]; then
    FAIL_COUNT=$((FAIL_COUNT + 1))
    sed -i "s|^FAIL_COUNT:.*|FAIL_COUNT:$FAIL_COUNT|" "$STATE_FILE"
  fi

  if [ "$FAIL_COUNT" -ge "$MAX_FAIL" ]; then
    rm -f "$STATE_FILE"
    cat <<MSG
🚫 [ROADMAP 중단] 동일 태스크 ${MAX_FAIL}회 미완료:
  $TASK_TEXT

수동으로 처리 후 "계속" 입력하세요.
또는 ROADMAP.md에서 해당 줄을 [x]로 체크하면 다음으로 넘어갑니다.
MSG
    exit 2
  fi

  # Bug2: mtime + TASK_TEXT grep 둘 다 확인 (옛 증거 오인 방지)
  EVIDENCE_VALID=0
  if [ "$EVIDENCE_TS" -gt "$START_TS" ] && grep -qF "$TASK_TEXT" "$EVIDENCE_FILE" 2>/dev/null; then
    EVIDENCE_VALID=1
  fi

  if [ "$EVIDENCE_VALID" = "1" ]; then
    cat <<MSG
⚠️ [검증 통과, [x] 미체크] (시도 $FAIL_COUNT/$MAX_FAIL)
태스크: $TASK_TEXT

.claude/.last_evidence 가 갱신됐지만 ROADMAP.md 에 [x] 가 없습니다.
해당 줄의 [ ] 를 [x] 로 체크 후 완료 보고하세요.
MSG
  else
    cat <<MSG
❌ [증거 없음, 재실행] (시도 $FAIL_COUNT/$MAX_FAIL)
태스크: $TASK_TEXT

.claude/.last_evidence 미갱신 또는 현재 태스크 내용 없음. 아래 명령으로 증거 기록:

  printf "=== \$(date) — ${TASK_TEXT} ===\n" >> .claude/.last_evidence
  cd backend && python -m pytest tests/ -v >> ../.claude/.last_evidence 2>&1
  curl -s https://connecting-dots-ctd.onrender.com/api/v1/ticker >> .claude/.last_evidence

기록 후 ROADMAP.md [ ] → [x] 체크 + 완료 보고하세요.
MSG
  fi
  exit 2
fi

# ── 새 태스크 시작 (Bug2: evidence 파일 초기화로 옛 증거 제거) ──────────────
printf 'TASK:%s\nSTART_TS:%s\nFAIL_COUNT:0\n' \
  "$TASK_TEXT" "$(date +%s)" > "$STATE_FILE"
> "$EVIDENCE_FILE"

cat <<MSG
📋 [ROADMAP 자동 실행]

태스크: $TASK_TEXT

완료 조건 (순서 필수):
  1. 구현
  2. pytest backend/tests/ -v → 전체 통과
  3. curl 실증 → 실제 값 확인
  4. 증거 기록:
       printf "=== \$(date) — ${TASK_TEXT} ===\n" >> .claude/.last_evidence
       cd backend && python -m pytest tests/ -v >> ../.claude/.last_evidence 2>&1
       curl -s https://connecting-dots-ctd.onrender.com/api/v1/ticker >> .claude/.last_evidence
  5. ROADMAP.md 해당 줄 [ ] → [x]
  6. 완료 보고 (증거 포함)
MSG
exit 2
