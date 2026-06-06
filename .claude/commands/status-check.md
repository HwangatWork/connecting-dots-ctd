# /status-check

Render 서비스 상태와 데이터 수집 상태를 확인한다.

## 실행 순서

1. **Render 서버 health check**
   ```bash
   curl -s --max-time 30 https://connecting-dots-ctd.onrender.com/api/v1/health
   ```
   - 응답 없음 → 슬립 상태 (free tier 15분 비활성 시 슬립)
   - `status: ok` → 정상

2. **캐시 상태 확인**
   - health 응답의 `cache_stats.alive_keys` 확인
   - 0이면 콜드 스타트 상태 (첫 요청이 느림)

3. **데이터 수집 상태 확인**
   ```bash
   curl -s https://connecting-dots-ctd.onrender.com/api/v1/status
   ```
   - `real_ratio` 확인 (장중 기대치: 60%+, 장 외 기대치: 20%+)
   - `fallback` 높으면 Yahoo Finance 429 또는 장 외 시간

4. **Render MCP로 배포 로그 확인** (다음 세션에서 Render MCP 툴 사용)
   - `render.listServices` → connecting-dots-ctd 서비스 ID 확인
   - `render.getDeployLogs` → 최신 배포 로그

5. **Netlify 프론트 상태 확인**
   ```bash
   curl -s https://connecting-dots-ctd.netlify.app | grep -o 'id="tab-[^"]*"'
   ```
   - 기대값: tab-market, tab-status, tab-stocks, tab-invest

## 이상 징후별 대응

| 증상 | 원인 | 조치 |
|------|------|------|
| Render 타임아웃 | 슬립 상태 | 재시도 (wake-up에 30-60초) |
| 5xx 에러 | 앱 크래시 | 로그 확인 → import 오류 수정 |
| real_ratio 0% | 콜드 스타트 | /api/v1/market 한 번 호출 |
| Netlify 구버전 | 자동 배포 미트리거 | index.html 주석 수정 후 push |
