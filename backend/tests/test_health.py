"""
FastAPI 앱 헬스체크 — TestClient로 로컬 엔드포인트 검증.
외부 네트워크 없이 앱 기동 가능 여부와 라우터 등록 상태를 확인한다.
"""
import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    from main import app
    return TestClient(app, raise_server_exceptions=True)


def test_health_returns_ok(client):
    """/api/v1/health가 200 + status:ok를 반환해야 한다."""
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert "timestamp" in body


def test_status_endpoint_returns_64_indicators(client):
    """/api/v1/status가 total=64인 지표 목록을 반환해야 한다."""
    r = client.get("/api/v1/status")
    assert r.status_code == 200
    body = r.json()
    assert body["summary"]["total"] == 64


def test_routers_registered(client):
    """핵심 API 경로가 404 없이 응답해야 한다 (캐시 미스여도 500 아님)."""
    for path in ["/api/v1/health", "/api/v1/status"]:
        r = client.get(path)
        assert r.status_code not in (404, 500), \
            f"{path} → {r.status_code}: 라우터 미등록 또는 앱 크래시"
