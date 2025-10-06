"""轻量级 API 测试，确保关键路由返回结构完整。"""

from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from motifmaker.api import app

client = TestClient(app)


def _generate_once() -> dict:
    response = client.post("/generate", json={"prompt": "城市夜景 Lo-Fi 学习"})
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    result = data["result"]
    for key in ("output_dir", "spec", "summary", "project", "sections", "track_stats"):
        assert key in result
    assert isinstance(result["track_stats"], list)
    assert result["project"]["form"]
    return result


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
    data = response.json()["result"]
    assert "project" in data
    assert "sections" in data
    assert len(data["track_stats"]) >= 1
    # sections 字典应包含至少一个段落条目，这里抽取任意键并确认再生次数字段存在。
    assert isinstance(data["sections"], dict) and data["sections"]
    first_section = next(iter(data["sections"].values()))
    assert "regeneration_count" in first_section


def test_freeze_motif_marks_tags() -> None:
    """验证 /freeze-motif 会为目标动机添加冻结标记。"""

    generated = _generate_once()
    spec = generated["project"]
    first_tag = next(iter(spec["motif_specs"].keys()))

    response = client.post(
        "/freeze-motif",
        json={"spec": spec, "motif_tags": [first_tag]},
    )
    assert response.status_code == 200
    payload = response.json()["result"]
    motif_specs = payload["project"]["motif_specs"]
    assert motif_specs[first_tag]["_frozen"] is True


def test_save_and_load_project_roundtrip() -> None:
    """验证保存与载入工程后的字段保持一致。"""

    generated = _generate_once()
    spec = generated["project"]
    name = f"pytest_{uuid4().hex}"

    save_response = client.post(
        "/save-project",
        json={"spec": spec, "name": name},
    )
    assert save_response.status_code == 200
    save_data = save_response.json()["result"]
    saved_path = Path(save_data["path"])
    assert saved_path.exists()

    load_response = client.post("/load-project", json={"name": name})
    assert load_response.status_code == 200
    loaded = load_response.json()["result"]
    assert loaded["project"]["form"] == spec["form"]
    assert loaded["project"]["motif_specs"] == spec["motif_specs"]

    try:
        saved_path.unlink()
    except FileNotFoundError:
        pass
