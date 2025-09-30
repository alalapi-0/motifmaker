"""Pydantic models that describe the project skeleton."""

from __future__ import annotations

"""项目规格模型，定义从动机到渲染的层级化参数结构。

该模块基于 Pydantic 构建 ``ProjectSpec``，用于串联提示解析、动机派生、
曲式展开、和声生成与渲染等阶段。为便于中文读者理解，文档字符串补充了
中文描述，说明每个字段在音乐生成流程中的作用。
"""

from typing import Any, Dict, List, Sequence

from pydantic import BaseModel, Field, confloat, conint


class FormSection(BaseModel):
    """描述曲式中的单个段落，同时提供中文解释。"""

    # 段落名称，例如 A、B、Bridge，用于在 UI 中定位。
    section: str = Field(..., description="Section label such as A, B, or Bridge")
    # 段落小节数，限制为正整数，驱动节拍总量计算。
    bars: conint(gt=0) = Field(..., description="Number of bars for the section")
    # 归一化的张力值，指导和声层与动态发展的强弱。
    tension: confloat(ge=0, le=1) = Field(
        ..., description="Normalized tension target for this section"
    )
    # 对应的动机标签，可结合“冻结动机”功能进行锁定。
    motif_label: str = Field(
        "primary",
        description="Which motif variant should be referenced when generating the section",
    )


class ProjectSpec(BaseModel):
    """完整的工程规格，串联提示解析到渲染的所有关键参数。"""

    # 曲式段落列表，来自默认模板或用户编辑。
    form: List[FormSection]
    # 主调与调式，影响动机根音及和声库选择。
    key: str
    mode: str
    # 速度、拍号与风格等基础参数。
    tempo_bpm: conint(gt=20, lt=320)
    meter: str
    style: str
    # 配器列表，用于渲染阶段挑选音色。
    instrumentation: List[str]
    # 动机规格字典，允许按标签配置 contour / rhythm 等细节。
    motif_specs: Dict[str, Dict[str, Any]]
    rhythm_density: str = Field(
        "medium", description="Global rhythm density hint (low/medium/high)"
    )
    motif_style: str = Field(
        "ascending-return",
        description="High-level motif style template (ascending_arc/wavering/zigzag)",
    )
    harmony_level: str = Field(
        "basic", description="Harmony complexity level (basic/colorful)"
    )
    # 是否在终止前引入二级属功能，用于教学演示的可选参数。
    use_secondary_dominant: bool = Field(
        False,
        description="Insert a secondary dominant before cadences when enabled",
    )
    generated_sections: Dict[str, Dict[str, Any]] | None = Field(
        default=None, description="Cached summaries produced during rendering"
    )


DEFAULT_FORM_TEMPLATE: Dict[str, Sequence[tuple[str, int, float]]] = {
    "ABA": (("A", 8, 0.3), ("B", 8, 0.8), ("A'", 8, 0.4)),
    "AABA": (
        ("A", 8, 0.3),
        ("A", 8, 0.35),
        ("B", 8, 0.8),
        ("A'", 8, 0.4),
    ),
    "ABAB": (("A", 8, 0.3), ("B", 8, 0.7), ("A", 8, 0.4), ("B", 8, 0.75)),
}

# 自定义曲式默认值，用于解析 Prompt 中显式列出的段落序列。
CUSTOM_SECTION_DEFAULTS: Dict[str, tuple[int, float]] = {
    "INTRO": (4, 0.15),
    "A": (8, 0.3),
    "A'": (8, 0.35),
    "B": (8, 0.75),
    "BRIDGE": (8, 0.85),
    "C": (8, 0.6),
    "OUTRO": (4, 0.2),
}


def default_from_prompt_meta(meta: Dict[str, Any]) -> ProjectSpec:
    """依据提示解析结果构造 :class:`ProjectSpec`，附带中英文说明。"""

    # 提取解析层提供的基础乐理参数，若缺失则使用默认值以保持稳健。
    key = meta.get("key", "C")
    mode = meta.get("mode", "major")
    tempo_bpm = int(meta.get("tempo_bpm", 100))
    meter = meta.get("meter", "4/4")
    style = meta.get("style", "contemporary")
    instrumentation = list(meta.get("instrumentation", ["piano"]))

    tension_curve = meta.get("tension_curve")
    form_sections: List[FormSection] = []
    custom_sequence = meta.get("custom_form_sequence")
    if custom_sequence:
        # 当 Prompt 显式列出段落顺序时，按自定义表构造 FormSection。
        for idx, raw_label in enumerate(custom_sequence):
            canonical = raw_label.upper()
            defaults = CUSTOM_SECTION_DEFAULTS.get(canonical, (8, 0.5))
            bars, default_tension = defaults
            tension = default_tension
            if tension_curve and idx < len(tension_curve):
                tension = float(tension_curve[idx])
            motif_label = (
                "primary"
                if canonical.startswith("A") or canonical in {"INTRO", "OUTRO"}
                else "contrast"
            )
            form_sections.append(
                FormSection(
                    section=raw_label,
                    bars=bars,
                    tension=max(0.0, min(1.0, tension)),
                    motif_label=motif_label,
                )
            )
    else:
        form_name = meta.get("form_template", "ABA")
        sections: Sequence[tuple[str, int, float]] = DEFAULT_FORM_TEMPLATE.get(
            form_name,
            DEFAULT_FORM_TEMPLATE["ABA"],
        )
        for idx, (label, bars, default_tension) in enumerate(sections):
            tension = default_tension
            if tension_curve and idx < len(tension_curve):
                tension = float(tension_curve[idx])
            form_sections.append(
                FormSection(
                    section=label,
                    bars=bars,
                    tension=max(0.0, min(1.0, tension)),
                    motif_label="primary" if label.startswith("A") else "contrast",
                )
            )

    motif_specs = {
        "primary": {
            "contour": meta.get("primary_contour", "ascending-return"),
            "rhythm_density": meta.get(
                "primary_rhythm", meta.get("rhythm_density", "medium")
            ),
            "motif_style": meta.get(
                "motif_style", meta.get("primary_contour", "ascending-return")
            ),
        },
        "contrast": {
            "contour": meta.get("contrast_contour", "wave"),
            "rhythm_density": meta.get("contrast_rhythm", "syncopated"),
        },
    }

    rhythm_density = (
        meta.get("rhythm_density") or meta.get("primary_rhythm") or "medium"
    )
    motif_style = (
        meta.get("motif_style") or meta.get("primary_contour") or "ascending-return"
    )
    harmony_level = meta.get("harmony_level") or "basic"
    # 布尔标记控制是否在终止前加入二级属，默认为 False。
    use_secondary_dominant = bool(meta.get("use_secondary_dominant", False))

    return ProjectSpec(
        form=form_sections,
        key=key,
        mode=mode,
        tempo_bpm=tempo_bpm,
        meter=meter,
        style=style,
        instrumentation=instrumentation,
        motif_specs=motif_specs,
        rhythm_density=str(rhythm_density),
        motif_style=str(motif_style),
        harmony_level=str(harmony_level),
        use_secondary_dominant=use_secondary_dominant,
    )


__all__ = ["FormSection", "ProjectSpec", "default_from_prompt_meta"]
