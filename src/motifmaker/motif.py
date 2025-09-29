"""Motif generation utilities.

The functions in this module transform lightweight textual descriptors into a
fully expanded melodic motif.  They are intentionally deterministic so that
unit tests and partial regeneration can rely on reproducible results.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Dict, Iterable, List, Sequence, TypedDict

import numpy as np

if TYPE_CHECKING:  # pragma: no cover - typing helper
    import pretty_midi

logger = logging.getLogger(__name__)

SCALE_MAJOR: Sequence[int] = (0, 2, 4, 5, 7, 9, 11)
SCALE_MINOR: Sequence[int] = (0, 2, 3, 5, 7, 8, 10)


class MotifSpec(TypedDict, total=False):
    """Typed dictionary describing motif generation hints.

    Attributes:
        contour: Legacy contour name kept for backwards compatibility.
        rhythm_density: Density keyword such as ``"low"`` or ``"high"``.
        mode: Musical mode (``"major"`` or ``"minor"``).
        root_pitch: MIDI root pitch used as anchor for scale degrees.
        motif_style: High level contour template (``"ascending_arc"`` etc.).
    """

    contour: str
    rhythm_density: str
    mode: str
    root_pitch: int
    motif_style: str


@dataclass
class MotifNote:
    """Represents a single motif note.

    Attributes:
        pitch: MIDI pitch number.
        duration_beats: Duration of the note expressed in beats.
    """

    pitch: int
    duration_beats: float


@dataclass
class Motif:
    """A short melodic motif defined as a sequence of :class:`MotifNote`."""

    notes: List[MotifNote]

    @property
    def total_beats(self) -> float:
        """Total duration of the motif in beats.

        Returns:
            Sum of ``duration_beats`` for every note in the motif.
        """

        return sum(note.duration_beats for note in self.notes)


_STYLE_CONTOURS: Dict[str, Sequence[int]] = {
    "ascending_arc": (0, 2, 4, 7, 5, 2, 0),
    "wavering": (0, 1, 0, 2, 1, 2, 0),
    "zigzag": (0, 4, 1, 5, 2, 6, 3),
}

_CONTOUR_FALLBACKS: Dict[str, Sequence[int]] = {
    "wave": (0, 2, 5, 2, 0),
    "descending": (5, 4, 2, 0),
    "ascending-return": (0, 2, 4, 2, 0),
}

_DENSITY_DURATIONS: Dict[str, Sequence[float]] = {
    "low": (1.0, 1.0, 2.0),
    "medium": (0.75, 1.25, 1.0, 1.0),
    "high": (0.5, 0.5, 0.5, 0.5, 1.0),
    # Backwards compatible aliases from earlier revisions.
    "sparse": (1.0, 1.0, 2.0),
    "syncopated": (0.75, 0.75, 0.5, 1.0),
    "dense": (0.5, 0.5, 1.0, 1.0),
}


def _scale_for_mode(mode: str) -> Sequence[int]:
    """Return the appropriate scale degrees for a mode.

    Args:
        mode: Either ``"major"`` or ``"minor"``.

    Returns:
        Sequence of semitone offsets representing the chosen scale.
    """

    return SCALE_MAJOR if mode == "major" else SCALE_MINOR


def _contour_from_style(contour: str | None, style: str | None) -> Sequence[int]:
    """Resolve the contour sequence based on style preference.

    ``motif_style`` supersedes the legacy ``contour`` hints.

    Args:
        contour: Legacy contour label from previous versions.
        style: High-level motif template selected by the user or parser.

    Returns:
        Sequence of scale-degree steps that describe the melodic contour.
    """

    if style and style in _STYLE_CONTOURS:
        return _STYLE_CONTOURS[style]
    if contour and contour in _CONTOUR_FALLBACKS:
        return _CONTOUR_FALLBACKS[contour]
    return _CONTOUR_FALLBACKS["ascending-return"]


def _durations_for_density(density: str | None) -> Sequence[float]:
    """Return a tuple of beat durations for the given density label.

    Args:
        density: Density keyword or ``None`` to use defaults.

    Returns:
        Sequence of beat lengths that repeats cyclically during motif expansion.
    """

    if density and density in _DENSITY_DURATIONS:
        return _DENSITY_DURATIONS[density]
    return _DENSITY_DURATIONS["medium"]


def _determine_pitch(scale: Sequence[int], step: int, root_pitch: int) -> int:
    """Map a scale degree index to an absolute MIDI pitch.

    Args:
        scale: Sequence of semitone offsets describing the chosen scale.
        step: Index into the scale sequence.
        root_pitch: MIDI pitch representing the tonic.

    Returns:
        MIDI pitch after combining ``root_pitch`` with the selected scale step.
    """

    clamped = int(np.clip(step, 0, len(scale) - 1))
    return root_pitch + scale[clamped]


def generate_motif(spec: MotifSpec) -> Motif:
    """Generate a deterministic motif from a specification dictionary.

    Args:
        spec: Typed dictionary describing contour, density and tonal settings.

    Returns:
        A :class:`Motif` whose note sequence follows the requested contour and
        rhythmic density.

    Raises:
        ValueError: If the generated motif would be empty due to missing data.

    Examples:
        >>> motif = generate_motif({"motif_style": "ascending_arc", "mode": "major", "root_pitch": 60})
        >>> len(motif.notes) > 0
        True
    """

    contour = spec.get("contour")
    style = spec.get("motif_style")
    density = spec.get("rhythm_density") or "medium"
    mode = spec.get("mode") or "major"
    root_pitch = int(spec.get("root_pitch") or 60)

    contour_steps = _contour_from_style(contour, style)
    durations = _durations_for_density(density)
    scale = _scale_for_mode(mode)

    notes: List[MotifNote] = []
    for idx, step in enumerate(contour_steps):
        # 将轮廓步长映射到音阶音级，再结合节奏模板生成音符。
        pitch = _determine_pitch(scale, step, root_pitch)
        duration = float(durations[idx % len(durations)])
        notes.append(MotifNote(pitch=pitch, duration_beats=duration))

    if not notes:
        raise ValueError("Generated motif contained no notes")

    logger.debug(
        "Generated motif with style %s, density %s and %d notes",
        style or contour,
        density,
        len(notes),
    )

    return Motif(notes=notes)


def motif_to_midi(
    motif: Motif, tempo_bpm: float, program: int = 0
) -> "pretty_midi.Instrument":
    """Convert a motif into a PrettyMIDI instrument track.

    Args:
        motif: The motif to serialize.
        tempo_bpm: Tempo used to convert beats to seconds.
        program: General MIDI program number determining the instrument timbre.

    Returns:
        A populated :class:`pretty_midi.Instrument` instance.
    """

    try:
        import pretty_midi
    except ModuleNotFoundError as exc:  # pragma: no cover - optional dependency
        raise RuntimeError(
            "pretty_midi is required to convert motifs into MIDI instruments"
        ) from exc

    instrument = pretty_midi.Instrument(program=program)
    time = 0.0
    beat_duration = 60.0 / tempo_bpm
    for note in motif.notes:
        start = time
        end = time + note.duration_beats * beat_duration
        instrument.notes.append(
            pretty_midi.Note(velocity=80, pitch=note.pitch, start=start, end=end)
        )
        time = end
    return instrument


__all__ = ["Motif", "MotifNote", "MotifSpec", "generate_motif", "motif_to_midi"]
