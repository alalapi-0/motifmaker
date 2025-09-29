import json
from pathlib import Path

from motifmaker.parsing import parse_natural_prompt
from motifmaker.render import regenerate_section, render_project
from motifmaker.schema import ProjectSpec, default_from_prompt_meta


def test_regenerate_section_updates_only_target(tmp_path: Path) -> None:
    prompt = "温暖的夜景，电子氛围"
    meta = parse_natural_prompt(prompt)
    spec = default_from_prompt_meta(meta)

    out_dir = tmp_path / "demo"
    result = render_project(spec, out_dir, emit_midi=False)
    spec_path = Path(result["spec"])
    spec_data = ProjectSpec.model_validate_json(spec_path.read_text(encoding="utf-8"))
    original_sections = json.loads(spec_path.read_text(encoding="utf-8"))[
        "generated_sections"
    ]

    updated_spec, summaries = regenerate_section(spec_data, "B")
    assert "B" in summaries
    assert updated_spec.generated_sections is not None

    for name, summary in updated_spec.generated_sections.items():
        if name == "B":
            assert (
                summary["regeneration_count"]
                == original_sections[name]["regeneration_count"] + 1
            )
        else:
            assert summary == original_sections[name]
