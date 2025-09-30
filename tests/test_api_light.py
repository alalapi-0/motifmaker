"""轻量级 API 测试，确保关键路由返回结构完整。"""

from fastapi.testclient import TestClient

from motifmaker.api import app

client = TestClient(app)


def _generate_once() -> dict:
    response = client.post("/generate", json={"prompt": "城市夜景 Lo-Fi 学习"})
    assert response.status_code == 200
    data = response.json()
    for key in ("output_dir", "spec", "summary", "project", "sections", "track_stats"):
        assert key in data
    assert isinstance(data["track_stats"], list)
    assert data["project"]["form"]
    return data


def test_generate_endpoint_returns_summary() -> None:
    """验证 /generate 基本结构与字段。"""

    _generate_once()


def test_regenerate_section_structure() -> None:
    """验证 /regenerate-section 返回 JSON 含关键字段。"""

    first = _generate_once()
    spec = first["project"]
    response = client.post(
        "/regenerate-section",
        json={
            "spec": spec,
            "section_index": 0,
            "keep_motif": True,
            "emit_midi": False,
            "tracks": ["melody"],
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "project" in data
    assert "sections" in data
    assert len(data["track_stats"]) >= 1
    assert "A" in data["sections"] or data["sections"]
