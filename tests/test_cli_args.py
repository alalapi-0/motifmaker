import json
from pathlib import Path

from typer.testing import CliRunner

from motifmaker.cli import app


def test_cli_init_with_overrides(tmp_path: Path) -> None:
    runner = CliRunner()
    out_dir = tmp_path / "demo"
    result = runner.invoke(
        app,
        [
            "init-from-prompt",
            "城市夜景、温暖而克制",
            "--out",
            str(out_dir),
            "--motif-style",
            "wavering",
            "--rhythm-density",
            "high",
            "--harmony-level",
            "colorful",
        ],
    )
    assert result.exit_code == 0, result.stdout
    spec_path = out_dir / "spec.json"
    midi_path = out_dir / "track.mid"
    assert spec_path.exists()
    assert not midi_path.exists()
    data = json.loads(spec_path.read_text(encoding="utf-8"))
    assert data["harmony_level"] == "colorful"


def test_cli_invalid_style(tmp_path: Path) -> None:
    runner = CliRunner()
    out_dir = tmp_path / "demo"
    result = runner.invoke(
        app,
        [
            "init-from-prompt",
            "测试提示",
            "--out",
            str(out_dir),
            "--motif-style",
            "invalid",
        ],
    )
    assert result.exit_code != 0
    assert "Unsupported motif style" in result.stdout
