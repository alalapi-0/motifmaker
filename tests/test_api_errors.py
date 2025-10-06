"""验证 API 在下游异常时返回统一错误码。"""

from fastapi.testclient import TestClient

from motifmaker.api import app
from motifmaker.errors import PersistenceError
from motifmaker.parsing import parse_natural_prompt
from motifmaker.schema import default_from_prompt_meta

client = TestClient(app)


def test_load_project_persistence_error(monkeypatch) -> None:
    """当持久化层抛错时应映射为 E_PERSIST。"""

    def _boom(name: str):  # pragma: no cover - 模拟异常
        raise PersistenceError("disk offline")

    monkeypatch.setattr("motifmaker.api.load_project_json", _boom)
    response = client.post("/load-project", json={"name": "missing"})
    assert response.status_code == 500
    payload = response.json()
    assert payload["error"]["code"] == "E_PERSIST"


def test_render_project_error(monkeypatch) -> None:
    """渲染异常需转换为 E_RENDER。"""

    meta = parse_natural_prompt("温暖的钢琴独奏")
    spec = default_from_prompt_meta(meta)

    def _render_fail(*args, **kwargs):  # pragma: no cover - 模拟异常
        raise RuntimeError("render failed")

    monkeypatch.setattr("motifmaker.api.render_project", _render_fail)
    response = client.post(
        "/render",
        json={
            "project": spec.model_dump(mode="json"),
            "emit_midi": False,
        },
    )
    assert response.status_code == 500
    payload = response.json()
    assert payload["error"]["code"] == "E_RENDER"
