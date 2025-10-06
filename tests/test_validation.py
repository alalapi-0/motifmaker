"""验证 ProjectSpec 校验规则与 API 错误响应。"""

import pytest
from fastapi.testclient import TestClient

from motifmaker.api import app
from motifmaker.errors import ValidationError
from motifmaker.schema import FormSection, ProjectSpec

client = TestClient(app)


def _base_spec_kwargs() -> dict:
    """构造通过校验所需的基础字段集合。"""

    return {
        "form": [FormSection(section="A", bars=8, tension=50, motif_label="primary")],
        "key": "C",
        "mode": "major",
        "tempo_bpm": 100,
        "meter": "4/4",
        "style": "test",
        "instrumentation": ["piano"],
        "motif_specs": {"primary": {"contour": "ascending"}},
    }


def test_project_spec_invalid_tempo() -> None:
    """当 BPM 超界时应抛出统一的 ValidationError。"""

    data = _base_spec_kwargs()
    data["tempo_bpm"] = 10
    with pytest.raises(ValidationError):
        ProjectSpec(**data)


def test_project_spec_invalid_meter() -> None:
    """非法拍号需触发 ValidationError。"""

    data = _base_spec_kwargs()
    data["meter"] = "6/8"
    with pytest.raises(ValidationError):
        ProjectSpec(**data)


def test_project_spec_empty_form() -> None:
    """空 form 列表应直接拒绝。"""

    data = _base_spec_kwargs()
    data["form"] = []
    with pytest.raises(ValidationError):
        ProjectSpec(**data)


def test_project_spec_missing_motif() -> None:
    """引用不存在的动机标签时需要抛错。"""

    data = _base_spec_kwargs()
    data["form"] = [FormSection(section="A", bars=8, tension=50, motif_label="missing")]
    with pytest.raises(ValidationError):
        ProjectSpec(**data)


def test_generate_endpoint_empty_prompt() -> None:
    """空字符串 Prompt 会返回 E_VALIDATION 错误码。"""

    response = client.post("/generate", json={"prompt": "   "})
    assert response.status_code == 400
    body = response.json()
    assert body["ok"] is False
    assert body["error"]["code"] == "E_VALIDATION"
