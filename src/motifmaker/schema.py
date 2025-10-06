"""项目规格模型，定义从动机到渲染的层级化参数结构。

该模块在原有 Pydantic 模型基础上引入更严格的校验逻辑：速度、拍号、
段落数量、张力、配器数量与动机引用均会在构建时验证，若违反约束则
抛出统一的 :class:`~motifmaker.errors.ValidationError`。"""

from __future__ import annotations

from typing import Any, Dict, List, Sequence

from pydantic import BaseModel, Field, ValidationError as PydanticValidationError
from pydantic import field_validator, model_validator

from .errors import ValidationError


class FormSection(BaseModel):
    """描述曲式中的单个段落，同时提供中文解释。"""

    section: str = Field(
        ...,
        description="Section label such as A, B, or Bridge",
        min_length=1,
    )
    bars: int = Field(..., description="Number of bars for the section")
    tension: int = Field(
        ..., description="Tension intensity scaled to 0-100 for UI consumption"
    )
    motif_label: str = Field(
        "primary",
        description="Which motif variant should be referenced when generating the section",
        min_length=1,
    )

    @field_validator("section", "motif_label")
    @classmethod
    def _strip_text(cls, value: str) -> str:
        """确保段落与动机标签不包含首尾空白。"""

        return value.strip()

    @field_validator("bars")
    @classmethod
    def _check_bars(cls, value: int) -> int:
        """限制段落小节数在 1-128 之间。"""

        if not 1 <= int(value) <= 128:
            raise ValidationError("段落小节数必须在 1-128 内", details={"bars": value})
        return int(value)

    @field_validator("tension")
    @classmethod
    def _check_tension(cls, value: int) -> int:
        """限制张力取值范围为 0-100。"""

        if not 0 <= int(value) <= 100:
            raise ValidationError("段落张力必须在 0-100 内", details={"tension": value})
        return int(value)


class ProjectSpec(BaseModel):
    """完整的工程规格，串联提示解析到渲染的所有关键参数。"""

    form: List[FormSection] = Field(...)
    key: str
    mode: str
    tempo_bpm: int
    meter: str
    style: str
    instrumentation: List[str]
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
    use_secondary_dominant: bool = Field(
        False,
        description="Insert a secondary dominant before cadences when enabled",
    )
    generated_sections: Dict[str, Dict[str, Any]] | None = Field(
        default=None, description="Cached summaries produced during rendering"
    )

    @field_validator("form")
    @classmethod
    def _validate_form(cls, value: List[FormSection]) -> List[FormSection]:
        """确保至少包含一个曲式段落。"""

        if not value:
            raise ValidationError("form 至少需要一个段落")
        return value

    @field_validator("tempo_bpm")
    @classmethod
    def _validate_tempo(cls, value: int) -> int:
        """BPM 必须在 40-220 之间。"""

        if not 40 <= int(value) <= 220:
            raise ValidationError(
                "tempo_bpm 超出允许范围", details={"tempo_bpm": value}
            )
        return int(value)

    @field_validator("meter")
    @classmethod
    def _validate_meter(cls, value: str) -> str:
        """仅允许常见的 4/4 与 3/4 拍号，确保和声引擎稳定。"""

        allowed = {"4/4", "3/4"}
        if value not in allowed:
            raise ValidationError("仅支持 4/4 或 3/4 拍号", details={"meter": value})
        return value

    @field_validator("instrumentation")
    @classmethod
    def _validate_instrumentation(cls, value: List[str]) -> List[str]:
        """保证配器为非空字符串且数量不超过 16。"""

        if len(value) > 16:
            raise ValidationError("配器数量过多", details={"count": len(value)})
        cleaned: List[str] = []
        for item in value:
            item_clean = item.strip()
            if not item_clean:
                raise ValidationError("配器名称不能为空字符串")
            cleaned.append(item_clean)
        if not cleaned:
            raise ValidationError("至少需要一个配器名称")
        return cleaned

    @model_validator(mode="after")
    def _check_motif_consistency(self) -> "ProjectSpec":
        """确认曲式引用的动机标签都存在于 ``motif_specs``。"""

        labels = {section.motif_label for section in self.form}
        missing = sorted(label for label in labels if label not in self.motif_specs)
        if missing:
            raise ValidationError(
                "动机规格缺失对应条目",
                details={"missing": missing},
            )
        return self


DEFAULT_FORM_TEMPLATE: Dict[str, Sequence[tuple[str, int, int]]] = {
    "ABA": (("A", 8, 30), ("B", 8, 80), ("A'", 8, 40)),
    "AABA": (("A", 8, 30), ("A", 8, 35), ("B", 8, 80), ("A'", 8, 40)),
    "ABAB": (("A", 8, 30), ("B", 8, 70), ("A", 8, 40), ("B", 8, 75)),
}

# 自定义曲式默认值，用于解析 Prompt 中显式列出的段落序列。
CUSTOM_SECTION_DEFAULTS: Dict[str, tuple[int, int]] = {
    "INTRO": (4, 15),
    "A": (8, 30),
    "A'": (8, 35),
    "B": (8, 75),
    "BRIDGE": (8, 85),
    "C": (8, 60),
    "OUTRO": (4, 20),
}


def _build_form_sections(meta: Dict[str, Any]) -> List[FormSection]:
    """根据解析到的张力曲线与曲式信息构造段落列表。"""

    tension_curve = meta.get("tension_curve") or [30, 60, 90, 40, 35, 20]
    form_sections: List[FormSection] = []
    custom_sequence = meta.get("custom_form_sequence")
    if custom_sequence:
        for idx, raw_label in enumerate(custom_sequence):
            canonical = raw_label.upper()
            bars, default_tension = CUSTOM_SECTION_DEFAULTS.get(canonical, (8, 50))
            tension = default_tension
            if idx < len(tension_curve):
                tension = int(tension_curve[idx])
            motif_label = (
                "primary"
                if canonical.startswith("A") or canonical in {"INTRO", "OUTRO"}
                else "contrast"
            )
            form_sections.append(
                FormSection(
                    section=raw_label,
                    bars=bars,
                    tension=max(0, min(100, tension)),
                    motif_label=motif_label,
                )
            )
    else:
        form_name = meta.get("form_template", "ABA")
        sections: Sequence[tuple[str, int, int]] = DEFAULT_FORM_TEMPLATE.get(
            form_name,
            DEFAULT_FORM_TEMPLATE["ABA"],
        )
        for idx, (label, bars, default_tension) in enumerate(sections):
            tension = default_tension
            if idx < len(tension_curve):
                tension = int(tension_curve[idx])
            form_sections.append(
                FormSection(
                    section=label,
                    bars=bars,
                    tension=max(0, min(100, tension)),
                    motif_label="primary" if label.startswith("A") else "contrast",
                )
            )
    return form_sections


def default_from_prompt_meta(meta: Dict[str, Any]) -> ProjectSpec:
    """依据提示解析结果构造 :class:`ProjectSpec`，附带中英文说明。"""

    try:
        key = meta.get("key", "C")
        mode = meta.get("mode", "major")
        tempo_bpm = int(meta.get("tempo_bpm", 100))
        meter = meta.get("meter", "4/4")
        style = meta.get("style", "contemporary")
        instrumentation_raw = meta.get("instrumentation", ["piano"])
        instrumentation = [str(item) for item in instrumentation_raw][:16]

        form_sections = _build_form_sections(meta)

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
    except ValidationError:
        raise
    except PydanticValidationError as exc:
        raise ValidationError(
            "ProjectSpec 构造失败", details={"errors": exc.errors()}
        ) from exc


__all__ = ["FormSection", "ProjectSpec", "default_from_prompt_meta"]
