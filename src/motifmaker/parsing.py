"""提示解析器：将自然语言 Prompt 转换为工程元数据。

模块使用正则与关键词匹配，将情绪、风格与显式参数映射到结构化字典。
示例："城市夜景 90 BPM Lo-Fi 学习" 会匹配到 urban-ambient 的预设、
覆盖节奏为 90 BPM，并结合动机/配器关键词组合出 ProjectSpec 所需字段。
"""

from __future__ import annotations

import logging
import re
from typing import Dict, List

logger = logging.getLogger(__name__)

# 情绪场景预设，覆盖 10+ 常见风格，便于前端直接呈现默认参数。
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
            "tension_curve": [0.25, 0.6, 0.9, 0.5],
            "use_secondary_dominant": True,
        },
    ),
    (
        ["旷野清晨", "野外清晨", "morning field"],
        {
            "key": "G",
            "mode": "major",
            "tempo_bpm": 108,
            "meter": "6/8",
            "style": "pastoral-acoustic",
            "instrumentation": ["acoustic-guitar", "flute", "strings", "percussion"],
            "tension_curve": [0.2, 0.45, 0.6, 0.35],
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
            "tension_curve": [0.3, 0.55, 0.85, 0.6],
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
            "tension_curve": [0.25, 0.4, 0.65, 0.3],
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
            "tension_curve": [0.2, 0.35, 0.5, 0.3],
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
            "tension_curve": [0.35, 0.55, 0.95, 0.8],
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
            "tension_curve": [0.2, 0.4, 0.6, 0.3],
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
            "tension_curve": [0.25, 0.45, 0.55, 0.35],
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
            "tension_curve": [0.3, 0.5, 0.8, 0.5],
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
            "tension_curve": [0.35, 0.55, 0.75, 0.5],
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
            "tension_curve": [0.3, 0.45, 0.7, 0.4],
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
    "流动": "6/8",
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


def _normalise(text: str) -> str:
    """去除前后空白并返回原字符串副本。"""

    return text.strip()


def _detect_scenario(prompt: str) -> Dict[str, object]:
    """匹配情绪预设，返回深拷贝以免后续修改影响常量。"""

    lowered = prompt.lower()
    for keywords, preset in SCENARIO_PRESETS:
        if any(keyword.lower() in lowered for keyword in keywords):
            meta = dict(preset)
            # 深拷贝乐器列表，避免后续 append 修改常量。
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


def _detect_tension(prompt: str) -> List[float]:
    """根据描述返回张力曲线。"""

    if "最高" in prompt and "B" in prompt:
        return [0.3, 0.9, 0.4]
    if "渐进" in prompt:
        return [0.2, 0.4, 0.8]
    if "舒缓" in prompt:
        return [0.2, 0.35, 0.5]
    return [0.3, 0.7, 0.4]


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


def parse_natural_prompt(text: str) -> Dict[str, object]:
    """将自然语言提示解析为结构化元数据。

    示例::
        >>> parse_natural_prompt("城市夜景 90 BPM Lo-Fi 学习 A-B-A′")
        {'key': 'E', 'mode': 'minor', 'tempo_bpm': 90, 'meter': '4/4', ...}
    """

    prompt = _normalise(text)
    scenario_meta = _detect_scenario(prompt)
    meta: Dict[str, object] = dict(scenario_meta)

    # 情景预设之外的默认推断仍然执行，以便补全缺失字段。
    if "key" not in meta:
        key, mode = _detect_key_mode(prompt)
        meta.update({"key": key, "mode": mode})
    if "tempo_bpm" not in meta:
        meta["tempo_bpm"] = _detect_tempo(prompt)
    if "meter" not in meta:
        meta["meter"] = _detect_meter(prompt)
    if "style" not in meta:
        meta["style"] = _detect_style(prompt)

    # 解析配器并合并到场景预设提供的默认值中。
    instruments = list(meta.get("instrumentation", []))
    for inst in _detect_instrumentation(prompt):
        if inst not in instruments:
            instruments.append(inst)
    if not instruments:
        instruments.append("piano")
    meta["instrumentation"] = instruments

    # 曲式解析：优先读取显式序列，其次是模板关键词。
    form_template, form_sequence = _detect_form(prompt)
    if form_sequence:
        meta["custom_form_sequence"] = form_sequence
    elif form_template:
        meta["form_template"] = form_template
    else:
        meta["form_template"] = meta.get("form_template", "ABA")

    meta["tension_curve"] = meta.get("tension_curve", _detect_tension(prompt))

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

    # 二级属开关：当用户显式提及时强制开启。
    if any(keyword in prompt.lower() for keyword in SECONDARY_DOMINANT_KEYWORDS):
        meta["use_secondary_dominant"] = True

    # 显式数值覆盖写在最后，确保 BPM/拍号指令优先生效。
    meta.update(_extract_numeric_overrides(prompt))

    logger.info(
        "Parsed prompt into meta: key=%s mode=%s style=%s",
        meta.get("key"),
        meta.get("mode"),
        meta.get("style"),
    )
    logger.debug("Prompt meta details: %s", meta)

    return meta


__all__ = ["parse_natural_prompt"]
