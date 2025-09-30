"""命令行工具：支持 Prompt 生成、分轨渲染、局部再生与工程持久化。"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import typer

from .parsing import parse_natural_prompt
from .persistence import load_project_json, save_project_json
from .render import RenderResult, regenerate_section, render_project
from .schema import ProjectSpec, default_from_prompt_meta
from .utils import configure_logging, ensure_directory

app = typer.Typer(help="分层音乐生成原型 CLI")

_LOGGER = logging.getLogger(__name__)

_VALID_STYLES = {"ascending_arc", "wavering", "zigzag"}
_VALID_DENSITIES = {"low", "medium", "high"}
_VALID_HARMONIES = {"basic", "colorful"}


def _validate_choice(
    value: Optional[str], valid: set[str], option_name: str, label: str
) -> Optional[str]:
    """校验 CLI 选项取值是否合法。"""

    if value is None:
        return None
    normalised = value.lower()
    if normalised not in valid:
        raise typer.BadParameter(
            f"Unsupported {label}: {value} / 不支持的{label}: {value}",
            param_hint=option_name,
        )
    return normalised


def _spec_from_prompt(
    prompt: str,
    motif_style: Optional[str],
    rhythm_density: Optional[str],
    harmony_level: Optional[str],
) -> ProjectSpec:
    """结合 Prompt 解析结果与 CLI 覆盖项生成 ProjectSpec。"""

    meta = parse_natural_prompt(prompt)
    if motif_style:
        meta["motif_style"] = motif_style
        meta["primary_contour"] = motif_style
    if rhythm_density:
        meta["rhythm_density"] = rhythm_density
        meta["primary_rhythm"] = rhythm_density
    if harmony_level:
        meta["harmony_level"] = harmony_level
    spec = default_from_prompt_meta(meta)
    _LOGGER.debug("Constructed ProjectSpec: %s", spec.model_dump())
    return spec


def _echo_render_result(result: RenderResult) -> None:
    """在控制台打印渲染成果，附带分轨统计。"""

    typer.echo(f"Specification saved to: {result['spec']}")
    typer.echo(f"Section summary saved to: {result['summary']}")
    if result["midi"]:
        typer.echo(f"MIDI file saved to: {result['midi']}")
    else:
        typer.echo("MIDI rendering skipped (use --emit-midi to enable).")
    for track in result.get("track_stats", []):
        typer.echo(
            f"Track {track['name']}: {track['notes']} notes / {track['duration_sec']}s"
        )


@app.callback()
def main(
    ctx: typer.Context,
    verbose: bool = typer.Option(False, "--verbose", "-v", help="启用 INFO 日志"),
    debug: bool = typer.Option(False, "--debug", help="启用 DEBUG 日志"),
) -> None:
    """配置 CLI 全局日志等级。"""

    level = logging.DEBUG if debug else logging.INFO if verbose else logging.WARNING
    configure_logging(level)
    ctx.ensure_object(dict)
    ctx.obj["log_level"] = level


@app.command("init-from-prompt")
def init_from_prompt(
    prompt: str = typer.Argument(..., help="自然语言描述"),
    out: Path = typer.Option(..., help="输出目录"),
    motif_style: Optional[str] = typer.Option(
        None,
        help="动机风格模板 (ascending_arc|wavering|zigzag)",
    ),
    rhythm_density: Optional[str] = typer.Option(
        None,
        help="节奏密度 (low|medium|high)",
    ),
    harmony_level: Optional[str] = typer.Option(
        None,
        help="和声复杂度 (basic|colorful)",
    ),
    emit_midi: bool = typer.Option(
        False,
        "--emit-midi/--no-emit-midi",
        help="是否生成 MIDI 文件",
    ),
) -> None:
    """从 Prompt 初始化工程规格并渲染。"""

    try:
        motif_style = _validate_choice(
            motif_style, _VALID_STYLES, "--motif-style", "motif style"
        )
        rhythm_density = _validate_choice(
            rhythm_density, _VALID_DENSITIES, "--rhythm-density", "rhythm density"
        )
        harmony_level = _validate_choice(
            harmony_level, _VALID_HARMONIES, "--harmony-level", "harmony level"
        )
        spec = _spec_from_prompt(prompt, motif_style, rhythm_density, harmony_level)
        output_dir = ensure_directory(out)
        result = render_project(spec, output_dir, emit_midi=emit_midi)
        _echo_render_result(result)
    except Exception as exc:  # pragma: no cover - 错误路径
        typer.echo(f"错误: {exc}")
        raise typer.Exit(code=1)


@app.command("render")
def render_from_spec(
    spec_path: Path = typer.Option(
        ..., exists=True, readable=True, help="ProjectSpec JSON 路径"
    ),
    out: Path = typer.Option(..., help="输出目录"),
    emit_midi: bool = typer.Option(
        False,
        "--emit-midi/--no-emit-midi",
        help="是否生成 MIDI 文件",
    ),
) -> None:
    """从现有规格 JSON 渲染文本与 MIDI。"""

    try:
        spec_data = ProjectSpec.model_validate_json(
            spec_path.read_text(encoding="utf-8")
        )
        output_dir = ensure_directory(out)
        result = render_project(spec_data, output_dir, emit_midi=emit_midi)
        _echo_render_result(result)
    except Exception as exc:  # pragma: no cover - 错误路径
        typer.echo(f"错误: {exc}")
        raise typer.Exit(code=1)


@app.command("regen-section")
def regen_section_cli(
    spec_path: Path = typer.Option(
        ..., exists=True, readable=True, help="原始 ProjectSpec JSON"
    ),
    section_index: int = typer.Option(..., help="需要再生的段落索引 (0 开始)"),
    keep_motif: bool = typer.Option(
        True,
        "--keep-motif/--switch-motif",
        help="是否保留当前段落的动机标签",
    ),
    out: Path = typer.Option(..., help="渲染输出目录"),
    emit_midi: bool = typer.Option(
        True,
        "--emit-midi/--no-emit-midi",
        help="局部再生时是否生成 MIDI",
    ),
) -> None:
    """仅再生指定段落并渲染，示例: motifmaker regen-section --spec spec.json --section-index 2."""

    try:
        spec_data = ProjectSpec.model_validate_json(
            spec_path.read_text(encoding="utf-8")
        )
        if section_index < 0 or section_index >= len(spec_data.form):
            raise typer.BadParameter("段落索引越界", param_hint="--section-index")
        section_name = spec_data.form[section_index].section
        updated_spec, _ = regenerate_section(
            spec_data, section_name, keep_motif=keep_motif
        )
        output_dir = ensure_directory(out)
        result = render_project(updated_spec, output_dir, emit_midi=emit_midi)
        _echo_render_result(result)
    except typer.BadParameter:
        raise
    except Exception as exc:  # pragma: no cover - 错误路径
        typer.echo(f"局部再生失败: {exc}")
        raise typer.Exit(code=1)


@app.command("save-project")
def save_project_cli(
    spec_path: Path = typer.Option(
        ..., exists=True, readable=True, help="ProjectSpec JSON 路径"
    ),
    name: str = typer.Option(..., help="保存的工程名称"),
) -> None:
    """保存当前工程规格，示例: motifmaker save-project --spec spec.json --name city_night_v1."""

    try:
        spec_data = ProjectSpec.model_validate_json(
            spec_path.read_text(encoding="utf-8")
        )
        path = save_project_json(spec_data, name)
        typer.echo(f"Project saved to: {path}")
    except Exception as exc:  # pragma: no cover - 错误路径
        typer.echo(f"保存失败: {exc}")
        raise typer.Exit(code=1)


@app.command("load-project")
def load_project_cli(
    name: str = typer.Option(..., help="保存时使用的工程名称"),
    out: Path = typer.Option(..., help="渲染输出目录"),
    emit_midi: bool = typer.Option(
        False,
        "--emit-midi/--no-emit-midi",
        help="载入后是否生成 MIDI",
    ),
) -> None:
    """载入已保存的工程并渲染，示例: motifmaker load-project --name city_night_v1 --out outputs/from_saved."""

    try:
        spec = load_project_json(name)
        output_dir = ensure_directory(out)
        result = render_project(spec, output_dir, emit_midi=emit_midi)
        _echo_render_result(result)
    except FileNotFoundError as exc:
        typer.echo(f"未找到工程: {exc}")
        raise typer.Exit(code=1)
    except Exception as exc:  # pragma: no cover - 错误路径
        typer.echo(f"载入失败: {exc}")
        raise typer.Exit(code=1)


__all__ = ["app"]
