"""Simple prompt parsing heuristics for Motifmaker prompts."""

from __future__ import annotations

import logging
from typing import Dict, List

logger = logging.getLogger(__name__)

KEYWORDS_KEY = {
    "温暖": ("C", "major"),
    "怀旧": ("G", "major"),
    "忧伤": ("A", "minor"),
    "悲伤": ("D", "minor"),
    "梦幻": ("D", "major"),
    "夜": ("E", "minor"),
}

STYLE_KEYWORDS = {
    "电子": "electro-acoustic",
    "古典": "neo-classical",
    "爵士": "modern-jazz",
    "摇滚": "cinematic-rock",
    "民谣": "folk-chamber",
}

INSTRUMENT_HINTS = {
    "钢琴": "piano",
    "弦乐": "strings",
    "小提琴": "violin",
    "萨克斯": "saxophone",
    "电钢": "electric-piano",
    "合成": "synth-pad",
    "打击": "percussion",
    "鼓": "drums",
    "吉他": "guitar",
}

METER_KEYWORDS = {
    "华尔兹": "3/4",
    "慢": "4/4",
    "舞曲": "4/4",
    "轻快": "4/4",
}

FORM_HINTS = {
    "桥段": "AABA",
    "bridge": "AABA",
    "对话": "ABAB",
    "B 段": "ABA",
}

MOTIF_STYLE_KEYWORDS = {
    "上行回落": "ascending_arc",
    "波浪": "wavering",
    "波浪感": "wavering",
    "曲折": "zigzag",
    "之字": "zigzag",
}

RHYTHM_DENSITY_KEYWORDS = {
    "克制": "low",
    "稀疏": "low",
    "张力": "high",
    "紧张": "high",
    "跳跃": "high",
}

HARMONY_LEVEL_KEYWORDS = {
    "色彩": "colorful",
    "爵士": "colorful",
    "丰富": "colorful",
}


def _detect_key_mode(prompt: str) -> tuple[str, str]:
    """Infer key and mode from the prompt using keyword matching.

    Args:
        prompt: Normalised prompt string.

    Returns:
        Tuple containing (key, mode).
    """

    for keyword, pair in KEYWORDS_KEY.items():
        if keyword in prompt:
            return pair
    return "C", "major"


def _detect_tempo(prompt: str) -> int:
    """Infer tempo in BPM from textual descriptors.

    Args:
        prompt: Normalised prompt string.

    Returns:
        Tempo in beats per minute.
    """

    if "慢" in prompt:
        return 70
    if "快" in prompt or "激动" in prompt:
        return 120
    if "夜" in prompt:
        return 90
    return 100


def _detect_meter(prompt: str) -> str:
    """Infer time signature from keywords.

    Args:
        prompt: Normalised prompt string.

    Returns:
        Meter string such as ``"4/4"``.
    """

    for keyword, meter in METER_KEYWORDS.items():
        if keyword in prompt:
            return meter
    return "4/4"


def _detect_style(prompt: str) -> str:
    """Infer stylistic label from keywords.

    Args:
        prompt: Normalised prompt string.

    Returns:
        Style label used for instrumentation defaults.
    """

    for keyword, style in STYLE_KEYWORDS.items():
        if keyword in prompt:
            return style
    return "contemporary"


def _detect_instrumentation(prompt: str) -> List[str]:
    """Collect instrumentation hints without duplicates.

    Args:
        prompt: Normalised prompt string.

    Returns:
        Ordered list of inferred instrument names.
    """

    instruments: List[str] = []
    for keyword, name in INSTRUMENT_HINTS.items():
        if keyword in prompt and name not in instruments:
            instruments.append(name)
    if not instruments:
        instruments.append("piano")
    return instruments


def _detect_form(prompt: str) -> str:
    """Select a form template from keywords.

    Args:
        prompt: Normalised prompt string.

    Returns:
        Form template key such as ``"ABA"``.
    """

    for keyword, form in FORM_HINTS.items():
        if keyword in prompt:
            return form
    return "ABA"


def _detect_tension(prompt: str) -> List[float]:
    """Provide a simple tension curve based on textual cues.

    Args:
        prompt: Normalised prompt string.

    Returns:
        List of normalised tension values.
    """

    if "最高" in prompt and "B" in prompt:
        return [0.3, 0.9, 0.4]
    if "渐进" in prompt:
        return [0.2, 0.4, 0.8]
    return [0.3, 0.7, 0.4]


def _detect_motif_style(prompt: str) -> str | None:
    """Map descriptive keywords to motif style templates.

    Args:
        prompt: Normalised prompt string.

    Returns:
        Motif style identifier or ``None`` if unspecified.
    """

    for keyword, style in MOTIF_STYLE_KEYWORDS.items():
        if keyword in prompt:
            return style
    return None


def _detect_rhythm_density(prompt: str) -> str | None:
    """Infer rhythm density hints from the prompt.

    Args:
        prompt: Normalised prompt string.

    Returns:
        Density keyword or ``None``.
    """

    for keyword, density in RHYTHM_DENSITY_KEYWORDS.items():
        if keyword in prompt:
            return density
    if "轻快" in prompt:
        return "medium"
    return None


def _detect_harmony_level(prompt: str) -> str | None:
    """Infer the harmony complexity level.

    Args:
        prompt: Normalised prompt string.

    Returns:
        Harmony complexity keyword or ``None``.
    """

    for keyword, level in HARMONY_LEVEL_KEYWORDS.items():
        if keyword in prompt:
            return level
    return None


def parse_natural_prompt(text: str) -> Dict[str, object]:
    """Parse a natural language description into structured metadata.

    Args:
        text: User provided prompt in Chinese or English.

    Returns:
        Dictionary containing hints for key, tempo, instrumentation and stylistic
        controls.  The result feeds directly into
        :func:`motifmaker.schema.default_from_prompt_meta`.
    """

    prompt = text.strip()
    key, mode = _detect_key_mode(prompt)
    tempo = _detect_tempo(prompt)
    meter = _detect_meter(prompt)
    style = _detect_style(prompt)
    instruments = _detect_instrumentation(prompt)
    form_template = _detect_form(prompt)
    tension_curve = _detect_tension(prompt)
    motif_style = _detect_motif_style(prompt)
    rhythm_density = _detect_rhythm_density(prompt)
    harmony_level = _detect_harmony_level(prompt)

    meta: Dict[str, object] = {
        "key": key,
        "mode": mode,
        "tempo_bpm": tempo,
        "meter": meter,
        "style": style,
        "instrumentation": instruments,
        "form_template": form_template,
        "tension_curve": tension_curve,
    }

    if motif_style:
        meta["motif_style"] = motif_style
        meta["primary_contour"] = motif_style
    if rhythm_density:
        meta["primary_rhythm"] = rhythm_density
    if harmony_level:
        meta["harmony_level"] = harmony_level

    if "动机" in prompt and "primary_contour" not in meta:
        meta["primary_contour"] = "wave"

    if "城市" in prompt or "夜" in prompt:
        if "synth-pad" not in instruments:
            instruments.append("synth-pad")
        meta["style"] = "urban-ambient"

    if "电子" in prompt:
        if "synth-bass" not in instruments:
            instruments.append("synth-bass")

    meta["instrumentation"] = instruments

    logger.info(
        "Parsed prompt into meta: key=%s mode=%s style=%s", key, mode, meta["style"]
    )
    logger.debug("Prompt meta details: %s", meta)

    return meta


__all__ = ["parse_natural_prompt"]
