"""测试工程持久化功能，确保保存与载入一致。"""

from pathlib import Path

from motifmaker.config import settings
from motifmaker.parsing import parse_natural_prompt
from motifmaker.persistence import load_project_json, save_project_json
from motifmaker.schema import default_from_prompt_meta


def test_save_and_load_roundtrip(tmp_path, monkeypatch) -> None:
    """保存后立即载入，字段应保持一致。"""

    # 使用临时目录避免污染真实 projects/ 文件夹。
    monkeypatch.setattr(settings, "projects_dir", str(tmp_path), raising=False)
    meta = parse_natural_prompt("清新原声的早晨")
    spec = default_from_prompt_meta(meta)
    path = save_project_json(spec, "unit_test_project")
    assert Path(path).exists()

    loaded = load_project_json("unit_test_project")
    assert loaded.key == spec.key
    assert loaded.mode == spec.mode
    assert len(loaded.form) == len(spec.form)
