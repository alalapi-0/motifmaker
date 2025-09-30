"""和声生成启发式，实现简化的功能走向并附带中文说明。

模块仍保留原有英文描述，同时强调本实现用于教学演示：通过基础/色彩两档
复杂度、自然小调的属功能增强以及可选的二级属衔接，向用户展示层级化音乐
生成中和声层的衔接方式。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, List, Sequence

from .form import SectionSketch
from .schema import ProjectSpec

logger = logging.getLogger(__name__)

KEY_TO_MIDI: Dict[str, int] = {
    "C": 60,
    "G": 67,
    "D": 62,
    "A": 69,
    "E": 64,
    "F": 65,
    "Bb": 70,
}


@dataclass
class HarmonyEvent:
    """Represents a chord aligned to a time span."""

    start_beat: float
    duration_beats: float
    chord_name: str
    pitches: List[int]
    bass_pitch: int


HARMONY_PROGRESSIONS: Dict[str, Sequence[tuple[int, str]]] = {
    "major": ((0, "I"), (5, "IV"), (7, "V"), (0, "I")),
    "minor": ((0, "i"), (3, "iv"), (7, "V"), (0, "i")),
}


def _scale_degrees(mode: str) -> Sequence[int]:
    """Return scale degrees used for chord building.

    Args:
        mode: Either ``"major"`` or ``"minor"``.

    Returns:
        Sequence of semitone offsets representing the diatonic scale.
    """

    return (0, 2, 4, 5, 7, 9, 11) if mode == "major" else (0, 2, 3, 5, 7, 8, 10)


def _triad(root_pitch: int, mode: str, degree: int) -> List[int]:
    """Construct a simple triad for the given scale degree.

    Args:
        root_pitch: MIDI pitch of the tonic.
        mode: Harmonic mode used for interval selection.
        degree: Scale degree index (0-based).

    Returns:
        List of MIDI pitches forming the triad.
    """

    degrees = _scale_degrees(mode)
    base = root_pitch + degrees[degree % len(degrees)]
    if mode == "minor" and degree == 4:
        third = base + 4
    else:
        third = base + (4 if mode == "major" or degree in (0, 4) else 3)
    fifth = base + 7
    return [base, third, fifth]


def _apply_color(chord: List[int], label: str) -> List[int]:
    """Extend a chord to include sevenths or modal mixture.

    Args:
        chord: Base triad to enrich.
        label: Roman numeral label describing the chord function.

    Returns:
        Extended chord with additional colour tones.
    """

    if label.upper() == "V":
        return chord + [chord[0] + 10]
    if label.lower() == "iv":
        return [chord[0], chord[0] + 5, chord[0] + 8, chord[0] + 12]
    return chord + [chord[0] + 11]


def generate_harmony(
    spec: ProjectSpec,
    sketches: List[SectionSketch],
    *,
    use_secondary_dominant: bool = False,
) -> Dict[str, List[HarmonyEvent]]:
    """根据项目规格生成和声事件，新增和声小调与二级属支持。"""

    root_pitch = KEY_TO_MIDI.get(spec.key, 60)
    progression = HARMONY_PROGRESSIONS.get(spec.mode, HARMONY_PROGRESSIONS["major"])
    colorful = spec.harmony_level == "colorful"

    harmony: Dict[str, List[HarmonyEvent]] = {}
    for section in sketches:
        events: List[HarmonyEvent] = []
        start_beat = 0.0
        total_beats = sum(note.duration_beats for note in section.notes)
        # B 段默认将分段粒度减半，以制造更密集的和声变化提升张力。
        segment_beats = 2.0 if section.name.lower().startswith("b") else 4.0
        idx = 0
        while start_beat < total_beats:
            degree_offset, label = progression[idx % len(progression)]
            degree = (degree_offset // 2) % 7
            pitches = _triad(root_pitch, spec.mode, degree)
            chord_label = label

            if spec.mode == "minor" and label.upper() == "V":
                # 在自然小调中模拟和声小调属功能：将属和弦改为大三和弦并加入升七音。
                dominant_root = root_pitch + 7
                pitches = [dominant_root, dominant_root + 4, dominant_root + 7]
                pitches.append(root_pitch + 11)
                chord_label = "V(♯7)"

            if colorful:
                # 色彩模式下继续为和弦添加七和弦或借用和弦音。
                pitches = _apply_color(pitches, label)

            # 当即将进入终止时并开启二级属功能时，插入额外的 V/V。
            if (
                use_secondary_dominant
                and (start_beat + segment_beats) >= total_beats
                and label.upper().startswith("I")
            ):
                secondary_duration = segment_beats / 2.0
                secondary_root = root_pitch + 2
                secondary_pitches = [secondary_root, secondary_root + 4, secondary_root + 7]
                events.append(
                    HarmonyEvent(
                        start_beat=start_beat,
                        duration_beats=secondary_duration,
                        chord_name="V/V",
                        pitches=secondary_pitches,
                        bass_pitch=secondary_pitches[0] - 12,
                    )
                )
                events.append(
                    HarmonyEvent(
                        start_beat=start_beat + secondary_duration,
                        duration_beats=segment_beats - secondary_duration,
                        chord_name=chord_label if not colorful else f"{chord_label}7",
                        pitches=pitches,
                        bass_pitch=pitches[0] - 12,
                    )
                )
                start_beat += segment_beats
                idx += 1
                continue

            events.append(
                HarmonyEvent(
                    start_beat=start_beat,
                    duration_beats=segment_beats,
                    chord_name=chord_label if not colorful else f"{chord_label}7",
                    pitches=pitches,
                    bass_pitch=pitches[0] - 12,
                )
            )
            start_beat += segment_beats
            idx += 1
        harmony[section.name] = events
        logger.debug("Generated %d harmony events for %s", len(events), section.name)
    return harmony


__all__ = ["HarmonyEvent", "generate_harmony", "KEY_TO_MIDI"]
