from pathlib import Path

from motifmaker.parsing import parse_natural_prompt
from motifmaker.render import render_project
from motifmaker.schema import default_from_prompt_meta


def test_harmony_levels_affect_chords(tmp_path: Path) -> None:
    prompt = "温暖的夜景"
    meta = parse_natural_prompt(prompt)
    spec_basic = default_from_prompt_meta(meta)
    result_basic = render_project(spec_basic, tmp_path / "basic", emit_midi=False)

    spec_colorful = spec_basic.model_copy(update={"harmony_level": "colorful"})
    result_colorful = render_project(
        spec_colorful, tmp_path / "colorful", emit_midi=False
    )

    chords_basic = result_basic["sections"]["A"]["chords"]
    chords_colorful = result_colorful["sections"]["A"]["chords"]

    assert not any(chord.endswith("7") for chord in chords_basic)
    assert any(chord.endswith("7") for chord in chords_colorful)
