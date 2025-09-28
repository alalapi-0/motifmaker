from motifmaker.parsing import parse_natural_prompt
from motifmaker.schema import ProjectSpec, default_from_prompt_meta


def test_project_spec_validation():
    prompt = "温暖的夜景，电子钢琴与弦乐"
    meta = parse_natural_prompt(prompt)
    spec = default_from_prompt_meta(meta)
    assert isinstance(spec, ProjectSpec)
    assert spec.form
    assert spec.instrumentation
    assert spec.tempo_bpm > 0
