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


def test_parse_explicit_overrides_and_humanization() -> None:
    prompt = "来一段 C 小调 120 BPM 的华丽乐段，3/4拍并加入humanization"
    meta = parse_natural_prompt(prompt)
    assert meta["tempo_bpm"] == 120
    assert meta["meter"] == "3/4"
    assert meta["mode"] == "minor"
    assert meta["key"] == "C"
    assert meta["humanization"] is True
    assert len(meta["available_motifs"]) >= 10


def test_style_template_enrichment_and_borrowed_flag() -> None:
    prompt = "lofi 学习氛围，加入借用和弦 bVII bVI"
    meta = parse_natural_prompt(prompt)
    template = meta.get("style_template")
    assert template and template["name"] == "lofi"
    assert any(inst for inst in meta["instrumentation"] if "vinyl" in inst)
    assert meta.get("use_borrowed_chords") is True
