from motifmaker.parsing import parse_natural_prompt


def test_parse_prompt_fields():
    prompt = "城市夜景，温暖而克制，现代古典加电子，钢琴弦乐合成"
    meta = parse_natural_prompt(prompt)
    assert meta["key"] in {"C", "G", "E"}
    assert meta["mode"] in {"major", "minor"}
    assert isinstance(meta["tempo_bpm"], int)
    assert isinstance(meta["instrumentation"], list)
    assert "synth-pad" in meta["instrumentation"]
    assert meta["form_template"] in {"ABA", "AABA", "ABAB"}
