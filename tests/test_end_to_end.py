from pathlib import Path

from motifmaker.parsing import parse_natural_prompt
from motifmaker.render import render_project
from motifmaker.schema import default_from_prompt_meta


def test_end_to_end_generation(tmp_path: Path) -> None:
    prompt = "温暖的城市夜景，带电子氛围"
    meta = parse_natural_prompt(prompt)
    spec = default_from_prompt_meta(meta)
    out_dir = tmp_path / "demo"
    midi_path = out_dir / "track.mid"
    json_path = out_dir / "spec.json"
    result = render_project(spec, midi_path, json_path)
    midi_file = Path(result["midi"])
    spec_file = Path(result["spec"])
    assert midi_file.exists() and midi_file.stat().st_size > 0
    assert spec_file.exists() and spec_file.read_text()
