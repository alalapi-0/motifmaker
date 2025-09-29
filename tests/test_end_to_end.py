import json
from pathlib import Path

from motifmaker.parsing import parse_natural_prompt
from motifmaker.render import render_project
from motifmaker.schema import default_from_prompt_meta


def test_end_to_end_generation(tmp_path: Path) -> None:
    prompt = "温暖的城市夜景，带电子氛围"
    meta = parse_natural_prompt(prompt)
    spec = default_from_prompt_meta(meta)
    out_dir = tmp_path / "demo"
    result = render_project(spec, out_dir, emit_midi=False)

    spec_file = Path(result["spec"])
    summary_file = Path(result["summary"])

    assert result["midi"] is None
    assert spec_file.exists()
    assert summary_file.exists()

    data = json.loads(spec_file.read_text(encoding="utf-8"))
    assert "generated_sections" in data
    summary_text = summary_file.read_text(encoding="utf-8")
    assert "Section" in summary_text
