# AGENTS.md — CTD 에이전트 행동 규칙

> 이 파일은 실제 발생한 사고에서 추출한 DO NOT 패턴이다.
> 규칙 위반 시 작업을 즉시 중단하고 사용자에게 보고한다.

---

## DO NOT 1 — 한글 문자열을 영문으로 치환하지 않는다

**What happened:**
`replace_all`로 import prefix를 수정하는 과정에서 한글 문자열이 깨졌다.
깨진 채로 "영문으로 교체"하는 작업을 진행해 `score_engine.py`의 `비즈니스 품질` 등
Korean axis 이름이 모두 영문으로 바뀌었다.

**Rule:**
한글 문자열은 기능적 의미를 가진다(API 응답값, 프론트 렌더링 키).
수정 도구 사용 전 한글 포함 파일을 반드시 `Read`로 확인하고,
한글 → 영문 변환은 사용자가 명시적으로 요청한 경우에만 수행한다.

**Instead:**
```
# 잘못된 접근
replace_all("비즈니스 품질", "business_quality")  # 절대 금지

# 올바른 접근
# 1. Read로 파일 확인
# 2. 한글이 있으면 그대로 유지
# 3. 변경이 필요하면 사용자에게 명시적 승인 요청
```

---

## DO NOT 2 — `from backend.` prefix를 코드에 추가하지 않는다

**What happened:**
Render rootDir이 `backend`로 설정되어 있어 `main.py`의 import는
`from config import ...` 형식이어야 한다.
`replace_all`로 `from ` → `from backend.`를 적용해 모든 import가 깨졌다.
배포 후 서버가 즉시 크래시됐다.

**Rule:**
Render rootDir = `backend` → Python 실행 기준 디렉토리가 `backend/`.
`backend/` 내부 파일은 항상 상대 import (`from config`, `from cache` 등).
`from backend.` prefix는 절대 사용하지 않는다.

**Instead:**
```python
# 잘못됨
from backend.config import settings

# 올바름
from config import settings
```

---

## DO NOT 3 — 배포 URL 검증 없이 "완료" 선언하지 않는다

**What happened:**
로컬 `frontend/index.html`이 4탭 구조로 수정됐지만
Netlify에는 구버전(더보기 탭)이 서빙 중이었다.
코드 파일만 읽고 "현황 탭 구현 완료"라고 보고했다.

**Rule:**
완료 기준은 반드시 **실제 배포 URL fetch**로 검증한다.
- 프론트: `curl https://connecting-dots-ctd.netlify.app`
- 백엔드: `curl https://connecting-dots-ctd.onrender.com/api/v1/health`

로컬 파일 상태 = 배포 상태가 아니다. git 커밋 = 배포가 아니다.

**Instead:**
```bash
# 완료 선언 전 반드시 실행
curl -s https://connecting-dots-ctd.netlify.app | python -c "
import sys, re
html = sys.stdin.read()
tabs = re.findall(r'id=\"tab-(\w+)\"', html)
print('live tabs:', tabs)
assert set(tabs) == {'market','status','stocks','invest'}, 'FAIL'
print('PASS')
"
```

---

## DO NOT 4 — git/로컬 상태를 배포 상태와 동일시하지 않는다

**What happened:**
Render auto-deploy 웹훅이 끊겨서 Jun 5 이후 커밋 6개가
실제 서버에 반영되지 않았다.
`git log`만 보고 "최신 코드가 서버에 올라가 있다"고 가정했다.

**Rule:**
배포 상태는 Render API로 직접 확인한다:
```bash
curl https://api.render.com/v1/services/srv-d8gv8l0jo6nc73e299e0/deploys?limit=1 \
  -H "Authorization: Bearer $RENDER_API_KEY"
```
live 배포의 commit ID가 `git log HEAD`와 일치할 때만 "반영됨"이다.

---

## DO NOT 5 — Python 파일을 UTF-8 BOM으로 저장하지 않는다

**What happened:**
`Set-Content`(PowerShell 기본값 UTF-16 LE)으로 파일을 저장했다.
한글 문자열이 전부 깨졌고, 이를 수정하는 과정에서
한글을 영문으로 바꾸는 2차 사고가 발생했다.

**Rule:**
모든 Python 파일은 **UTF-8 NoBOM** 인코딩으로 저장한다.
PowerShell `Set-Content` 사용 금지. `Write` 도구 또는 아래 방법 사용.

**Instead:**
```python
# 올바른 저장 방법
import pathlib
pathlib.Path("file.py").write_text(content, encoding="utf-8")

# PowerShell에서 필요 시
[System.IO.File]::WriteAllText($path, $content, [System.Text.UTF8Encoding]::new($false))
```

---

## 점검 체크리스트 (작업 완료 전)

```
[ ] 한글 문자열 변경 여부 확인 (의도치 않은 영문 치환 없음)
[ ] import 경로 확인 (from backend. prefix 없음)
[ ] 실제 배포 URL fetch로 기능 확인
[ ] Render 최신 live deploy commit = git HEAD
[ ] Python 파일 인코딩 UTF-8 NoBOM 확인
```
