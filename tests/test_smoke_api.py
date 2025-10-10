"""中文注释：最小化的 API 冒烟测试，确认健康探针与版本接口在 CI 中可用。"""

from fastapi.testclient import TestClient

from motifmaker.api import app

client = TestClient(app)


def test_healthz_endpoint_returns_ok() -> None:
    """中文注释：/healthz 应始终返回 200，代表后端应用正常加载。"""

    response = client.get("/healthz")
    assert response.status_code == 200


def test_version_endpoint_contains_version_field() -> None:
    """中文注释：/version 返回 JSON 且包含 version 字段，方便桌面端与前端校验。"""

    response = client.get("/version")
    assert response.status_code == 200
    payload = response.json()
    assert "version" in payload
