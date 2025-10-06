"""提示解析器：将自然语言 Prompt 转换为工程元数据。

在原有关键词匹配基础上增加了严格的数值校验与兜底逻辑：节奏 BPM
被限制在 40-220 范围，拍号限定为 4/4 或 3/4，张力曲线固定为 6 段且
取值 0-100。当解析失败或超出范围时会记录 WARN 日志并回退到安全默认。
"""

from __future__ import annotations

import logging
import re
from typing import Dict, List

logger = logging.getLogger(__name__)

# 情绪场景预设，覆盖常见风格并给出完整的 6 点张力曲线。
SCENARIO_PRESETS: List[tuple[List[str], Dict[str, object]]] = [
    (
        ["城市夜景", "都市夜", "city night"],
        {
            "key": "E",
            "mode": "minor",
            "tempo_bpm": 92,
            "meter": "4/4",
            "style": "urban-ambient",
            "instrumentation": [
                "electric-piano",
                "synth-pad",
                "synth-bass",
                "percussion",
            ],
            "tension_curve": [25, 45, 80, 90, 60, 40],
            "use_secondary_dominant": True,
        },
    ),
    (
        ["旷野清晨", "野外清晨", "morning field"],
        {
            "key": "G",
            "mode": "major",
            "tempo_bpm": 108,
            "meter": "3/4",
            "style": "pastoral-acoustic",
            "instrumentation": ["acoustic-guitar", "flute", "strings", "percussion"],
            "tension_curve": [20, 35, 55, 65, 50, 35],
        },
    ),
    (
        ["悬疑科幻", "sci-fi", "悬疑"],
        {
            "key": "C",
            "mode": "minor",
            "tempo_bpm": 78,
            "meter": "4/4",
            "style": "sci-fi-suspense",
            "instrumentation": ["synth-pad", "fx", "low-brass", "percussion"],
            "tension_curve": [30, 50, 85, 95, 70, 55],
        },
    ),
    (
        ["怀旧民谣", "nostalgia folk", "老民谣"],
        {
            "key": "D",
            "mode": "major",
            "tempo_bpm": 96,
            "meter": "4/4",
            "style": "nostalgic-folk",
            "instrumentation": ["acoustic-guitar", "harmonica", "strings"],
            "tension_curve": [25, 40, 60, 70, 45, 30],
        },
    ),
    (
        ["lo-fi 学习", "lofi", "学习节奏"],
        {
            "key": "Bb",
            "mode": "major",
            "tempo_bpm": 72,
            "meter": "4/4",
            "style": "lofi-study",
            "instrumentation": ["electric-piano", "vinyl-kit", "bass", "synth-pad"],
            "tension_curve": [20, 30, 45, 55, 40, 25],
        },
    ),
    (
        ["史诗预告片", "epic trailer", "电影预告"],
        {
            "key": "D",
            "mode": "minor",
            "tempo_bpm": 126,
            "meter": "4/4",
            "style": "epic-trailer",
            "instrumentation": ["strings", "brass", "choir", "percussion"],
            "tension_curve": [35, 55, 90, 100, 80, 60],
        },
    ),
    (
        ["抒情钢琴", "lyrical piano", "独奏钢琴"],
        {
            "key": "F",
            "mode": "major",
            "tempo_bpm": 78,
            "meter": "4/4",
            "style": "lyrical-piano",
            "instrumentation": ["piano", "strings"],
            "tension_curve": [20, 35, 55, 65, 45, 30],
        },
    ),
    (
        ["清新原声", "acoustic fresh", "轻原声"],
        {
            "key": "C",
            "mode": "major",
            "tempo_bpm": 112,
            "meter": "4/4",
            "style": "fresh-acoustic",
            "instrumentation": ["acoustic-guitar", "ukulele", "percussion"],
            "tension_curve": [25, 45, 60, 70, 50, 35],
        },
    ),
    (
        ["复古合成", "retro synth", "合成wave"],
        {
            "key": "A",
            "mode": "minor",
            "tempo_bpm": 118,
            "meter": "4/4",
            "style": "retro-synthwave",
            "instrumentation": ["synth-lead", "synth-bass", "drum-machine"],
            "tension_curve": [30, 50, 80, 85, 65, 45],
        },
    ),
    (
        ["爵士小编制", "jazz combo", "小型爵士"],
        {
            "key": "Eb",
            "mode": "major",
            "tempo_bpm": 140,
            "meter": "4/4",
            "style": "modern-jazz",
            "instrumentation": ["piano", "saxophone", "upright-bass", "drums"],
            "tension_curve": [35, 50, 75, 85, 65, 50],
        },
    ),
    (
        ["森林探险", "forest adventure", "探险"],
        {
            "key": "E",
            "mode": "major",
            "tempo_bpm": 104,
            "meter": "3/4",
            "style": "adventure-orchestral",
            "instrumentation": ["strings", "woodwinds", "percussion"],
            "tension_curve": [30, 45, 70, 80, 55, 40],
        },
    ),
]

# 传统关键词依旧保留，补充更多描述词以提升解析覆盖率。
KEYWORDS_KEY = {
    "温暖": ("C", "major"),
    "怀旧": ("G", "major"),
    "忧伤": ("A", "minor"),
    "悲伤": ("D", "minor"),
    "梦幻": ("D", "major"),
    "夜": ("E", "minor"),
    "史诗": ("D", "minor"),
    "清新": ("C", "major"),
    "科幻": ("C", "minor"),
}

STYLE_KEYWORDS = {
    "电子": "electro-acoustic",
    "古典": "neo-classical",
    "爵士": "modern-jazz",
    "摇滚": "cinematic-rock",
    "民谣": "folk-chamber",
    "预告": "epic-trailer",
    "原声": "fresh-acoustic",
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
    "木吉他": "acoustic-guitar",
    "铜管": "brass",
    "贝斯": "bass",
    "合成贝斯": "synth-bass",
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
    "段落循环": "ABAB",
}

MOTIF_STYLE_KEYWORDS = {
    "上行回落": "ascending_arc",
    "波浪": "wavering",
    "波浪感": "wavering",
    "曲折": "zigzag",
    "之字": "zigzag",
    "平滑": "ascending_return",
}

RHYTHM_DENSITY_KEYWORDS = {
    "克制": "low",
    "稀疏": "low",
    "张力": "high",
    "紧张": "high",
    "跳跃": "high",
    "稳重": "medium",
}

HARMONY_LEVEL_KEYWORDS = {
    "色彩": "colorful",
    "爵士": "colorful",
    "丰富": "colorful",
    "简单": "basic",
}

SECONDARY_DOMINANT_KEYWORDS = ("二级属", "secondary dominant")

BPM_PATTERN = re.compile(r"(\d{2,3})\s*(?:BPM|bpm|拍)")
METER_PATTERN = re.compile(r"(\d\s*/\s*\d)")
FORM_SEQUENCE_PATTERN = re.compile(
    r"((?:Intro|Outro|Bridge|A|B|C)(?:[′']?)(?:\s*[-–—]\s*(?:Intro|Outro|Bridge|A|B|C)(?:[′']?))+)",
    re.IGNORECASE,
)

_DEFAULT_TENSION = [30, 45, 60, 70, 50, 35]
_ALLOWED_METERS = {"4/4", "3/4"}


def _normalise(text: str) -> str:
    """去除前后空白并返回原字符串副本。"""

    return text.strip()


def _detect_scenario(prompt: str) -> Dict[str, object]:
    """匹配情绪预设，返回深拷贝以免后续修改影响常量。"""

    lowered = prompt.lower()
    for keywords, preset in SCENARIO_PRESETS:
        if any(keyword.lower() in lowered for keyword in keywords):
            meta = dict(preset)
            if "instrumentation" in meta:
                meta["instrumentation"] = list(meta["instrumentation"])
            return meta
    return {}


def _detect_key_mode(prompt: str) -> tuple[str, str]:
    """根据关键词推断调性与调式。"""

    for keyword, pair in KEYWORDS_KEY.items():
        if keyword in prompt:
            return pair
    return "C", "major"


def _detect_tempo(prompt: str) -> int:
    """根据形容词推断基础速度。"""

    if "慢" in prompt:
        return 70
    if "快" in prompt or "激动" in prompt:
        return 120
    if "夜" in prompt:
        return 90
    if "史诗" in prompt:
        return 126
    return 100


def _detect_meter(prompt: str) -> str:
    """根据关键词推断拍号。"""

    for keyword, meter in METER_KEYWORDS.items():
        if keyword in prompt:
            return meter
    return "4/4"


def _detect_style(prompt: str) -> str:
    """匹配风格关键词，作为场景预设的补充覆盖。"""

    for keyword, style in STYLE_KEYWORDS.items():
        if keyword in prompt:
            return style
    return "contemporary"


def _detect_instrumentation(prompt: str) -> List[str]:
    """根据提示追加配器信息，避免重复。"""

    instruments: List[str] = []
    for keyword, name in INSTRUMENT_HINTS.items():
        if keyword in prompt and name not in instruments:
            instruments.append(name)
    return instruments


def _detect_form(prompt: str) -> tuple[str | None, List[str] | None]:
    """返回模板关键字与自定义序列二选一。"""

    match = FORM_SEQUENCE_PATTERN.search(prompt)
    if match:
        tokens = [
            token.strip().upper().replace("′", "'")
            for token in re.split(r"[-–—]", match.group(1))
            if token.strip()
        ]
        return None, tokens
    for keyword, form in FORM_HINTS.items():
        if keyword.lower() in prompt.lower():
            return form, None
    return None, None


def _detect_tension(prompt: str) -> List[int]:
    """根据描述返回 6 个节点的张力曲线。"""

    if "最高" in prompt and "B" in prompt:
        return [30, 60, 90, 95, 70, 50]
    if "渐进" in prompt:
        return [20, 35, 50, 65, 80, 60]
    if "舒缓" in prompt:
        return [15, 25, 35, 45, 40, 30]
    return list(_DEFAULT_TENSION)


def _detect_motif_style(prompt: str) -> str | None:
    """动机风格关键词映射。"""

    for keyword, style in MOTIF_STYLE_KEYWORDS.items():
        if keyword in prompt:
            return style
    return None


def _detect_rhythm_density(prompt: str) -> str | None:
    """节奏密度关键词映射。"""

    for keyword, density in RHYTHM_DENSITY_KEYWORDS.items():
        if keyword in prompt:
            return density
    if "轻快" in prompt:
        return "medium"
    return None


def _detect_harmony_level(prompt: str) -> str | None:
    """和声复杂度关键词映射。"""

    for keyword, level in HARMONY_LEVEL_KEYWORDS.items():
        if keyword in prompt:
            return level
    return None


def _extract_numeric_overrides(prompt: str) -> Dict[str, object]:
    """解析显式写出的 BPM 与拍号覆盖。"""

    overrides: Dict[str, object] = {}
    bpm_match = BPM_PATTERN.search(prompt)
    if bpm_match:
        overrides["tempo_bpm"] = int(bpm_match.group(1))
    meter_match = METER_PATTERN.search(prompt)
    if meter_match:
        overrides["meter"] = meter_match.group(1).replace(" ", "")
    return overrides


def _clamp_tempo(value: int) -> int:
    """将 BPM 限制在安全范围，超出时记录警告。"""

    if 40 <= value <= 220:
        return value
    logger.warning("tempo_bpm 超出范围，已回退到 100: %s", value)
    return 100


def _clamp_meter(value: str) -> str:
    """保证拍号属于允许集合。"""

    if value in _ALLOWED_METERS:
        return value
    logger.warning("meter 非允许值，已回退到 4/4: %s", value)
    return "4/4"


def _normalise_tension_curve(values: List[object] | None) -> List[int]:
    """确保张力曲线长度为 6 且取值在 0-100。"""

    if not values:
        logger.warning("未解析到张力曲线，使用默认值")
        return list(_DEFAULT_TENSION)
    normalised: List[int] = []
    for raw in values:
        try:
            number = int(float(raw))
        except (TypeError, ValueError):
            logger.warning("张力曲线包含无法解析的值: %s", raw)
            continue
        normalised.append(max(0, min(100, number)))
    if not normalised:
        logger.warning("张力曲线清洗后为空，使用默认值")
        normalised = list(_DEFAULT_TENSION)
    if len(normalised) < 6:
        normalised.extend([normalised[-1]] * (6 - len(normalised)))
    if len(normalised) > 6:
        normalised = normalised[:6]
    return normalised


def _merge_instrumentation(base: List[str], additions: List[str]) -> List[str]:
    """合并配器并限制总数不超过 16。"""

    result: List[str] = []
    for name in base + additions:
        if name not in result:
            result.append(name)
        if len(result) >= 16:
            logger.warning("配器数量达到上限 16，后续条目被忽略")
            break
    return result or ["piano"]


def parse_natural_prompt(text: str) -> Dict[str, object]:
    """将自然语言提示解析为结构化元数据。"""

    prompt = _normalise(text)
    scenario_meta = _detect_scenario(prompt)
    meta: Dict[str, object] = dict(scenario_meta)

    if "key" not in meta:
        key, mode = _detect_key_mode(prompt)
        meta.update({"key": key, "mode": mode})
    if "tempo_bpm" not in meta:
        meta["tempo_bpm"] = _detect_tempo(prompt)
    if "meter" not in meta:
        meta["meter"] = _detect_meter(prompt)
    if "style" not in meta:
        meta["style"] = _detect_style(prompt)

    instruments = list(meta.get("instrumentation", []))
    additions = _detect_instrumentation(prompt)
    meta["instrumentation"] = _merge_instrumentation(instruments, additions)

    form_template, form_sequence = _detect_form(prompt)
    if form_sequence:
        meta["custom_form_sequence"] = form_sequence
    elif form_template:
        meta["form_template"] = form_template
    else:
        meta["form_template"] = meta.get("form_template", "ABA")

    meta["tension_curve"] = _normalise_tension_curve(
        meta.get("tension_curve") or _detect_tension(prompt)
    )

    motif_style = _detect_motif_style(prompt)
    if motif_style:
        meta["motif_style"] = motif_style
        meta["primary_contour"] = motif_style
    rhythm_density = _detect_rhythm_density(prompt)
    if rhythm_density:
        meta["primary_rhythm"] = rhythm_density
        meta["rhythm_density"] = rhythm_density
    harmony_level = _detect_harmony_level(prompt)
    if harmony_level:
        meta["harmony_level"] = harmony_level

    if any(keyword in prompt.lower() for keyword in SECONDARY_DOMINANT_KEYWORDS):
        meta["use_secondary_dominant"] = True

    meta.update(_extract_numeric_overrides(prompt))

    meta["tempo_bpm"] = _clamp_tempo(int(meta.get("tempo_bpm", 100)))
    meta["meter"] = _clamp_meter(str(meta.get("meter", "4/4")))

    logger.info(
        "Parsed prompt into meta: key=%s mode=%s style=%s",
        meta.get("key"),
        meta.get("mode"),
        meta.get("style"),
    )
    logger.debug("Prompt meta details: %s", meta)

    return meta


__all__ = ["parse_natural_prompt"]
