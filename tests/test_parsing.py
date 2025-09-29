from motifmaker.parsing import parse_natural_prompt


def test_parse_prompt_fields() -> None:
    prompt = "城市夜景，温暖而克制，现代古典加电子，钢琴弦乐合成"
    meta = parse_natural_prompt(prompt)
    assert meta["key"] in {"C", "G", "E"}
    assert meta["mode"] in {"major", "minor"}
    assert isinstance(meta["tempo_bpm"], int)
    assert isinstance(meta["instrumentation"], list)
    assert "synth-pad" in meta["instrumentation"]
    assert meta["form_template"] in {"ABA", "AABA", "ABAB"}
    assert meta.get("primary_rhythm") in {"low", "medium", "high", None}
    if "克制" in prompt:
        assert meta.get("primary_rhythm") == "low"
