# /deploy

CTD 전체 배포 파이프라인을 실행한다.

## 실행 순서

1. **로컬 import 테스트**
   ```bash
   cd backend && python -c "import main; print('ALL IMPORTS OK')"
   ```

2. **git 상태 확인**
   ```bash
   git status && git diff --stat HEAD
   ```

3. **GitHub push**
   ```bash
   git add -A
   git commit -m "deploy: <변경 내용 요약>"
   git push origin master
   ```

4. **Render 재배포 대기 + health check**
   - Render는 push 후 자동 배포 (약 1-3분 소요)
   - health check: `curl https://connecting-dots-ctd.onrender.com/api/v1/health`
   - 응답 없으면 30초 간격으로 최대 5회 재시도

5. **Netlify 배포 확인**
   - `curl https://connecting-dots-ctd.netlify.app` fetch 후 탭 구조 파싱
   - 기대값: tab IDs = ['market', 'stocks', 'invest', 'status']

6. **UI 레벨 검증 (체크리스트)**
   - [ ] 하단 탭 4개 (시장/현황/종목/투자)
   - [ ] 현황 탭 ⚙️ 버튼 존재
   - [ ] /api/v1/status 응답 정상 (total=64)
   - [ ] Render health check 200 OK

## 실패 시 대응
- Render 서버 다운: `git log --oneline -3`으로 최근 커밋 확인, import 오류 수정 후 재push
- Netlify 구버전 서빙: `frontend/index.html` 주석 라인 1개 수정 후 재push로 강제 재배포
