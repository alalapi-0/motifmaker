"""Rendering utilities for combining melodic layers into textual summaries."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Dict, Iterable, List, Tuple, TypedDict

from .form import SectionSketch, expand_form
from .harmony import HarmonyEvent, generate_harmony
from .motif import Motif, MotifSpec, generate_motif
from .schema import FormSection, ProjectSpec
from .utils import beats_to_seconds, ensure_directory, program_for_instrument

if TYPE_CHECKING:  # pragma: no cover - typing helper
    import pretty_midi

logger = logging.getLogger(__name__)


class RenderResult(TypedDict):
    """Typed dictionary describing the artefacts created by :func:`render_project`."""

    output_dir: str
    spec: str
    summary: str
    midi: str | None
    sections: Dict[str, Dict[str, object]]


@dataclass
class SectionSummary:
    """Text-friendly summary of a generated section."""

    name: str
    motif_label: str
    note_count: int
    unique_pitches: List[int]
    chords: List[str]

    def as_dict(self) -> Dict[str, object]:
        """Return a JSON-serialisable representation."""

        return {
            "name": self.name,
            "motif_label": self.motif_label,
            "note_count": self.note_count,
            "unique_pitches": self.unique_pitches,
            "chords": self.chords,
            "regeneration_count": 0,
        }

    def describe(self) -> str:
        """Return a single-line textual description."""

        chord_summary = ", ".join(self.chords) if self.chords else "(no harmony)"
        return (
            f"Section {self.name} uses motif '{self.motif_label}' with {self.note_count} notes "
            f"and chords: {chord_summary}"
        )


def _root_pitch_from_key(key: str) -> int:
    """Map a key string to a MIDI pitch value for the tonic.

    Args:
        key: Key signature label such as ``"C"`` or ``"Bb"``.

    Returns:
        MIDI pitch number representing the tonic.
    """

    mapping = {
        "C": 60,
        "G": 67,
        "D": 62,
        "A": 69,
        "E": 64,
        "F": 65,
        "Bb": 70,
    }
    return mapping.get(key, 60)


def _collect_sections(
    spec: ProjectSpec,
) -> Tuple[Dict[str, Motif], List[SectionSketch], Dict[str, List[HarmonyEvent]]]:
    """Generate motifs, expand form, and derive harmony mapping.

    Args:
        spec: Complete project specification.

    Returns:
        Tuple containing motif mapping, section sketches and harmony events.
    """

    root_pitch = _root_pitch_from_key(spec.key)
    motifs: Dict[str, Motif] = {}
    for label, motif_spec in spec.motif_specs.items():
        motif_params: MotifSpec = {
            "contour": motif_spec.get("contour", spec.motif_style),
            "motif_style": motif_spec.get("motif_style", spec.motif_style),
            "rhythm_density": motif_spec.get("rhythm_density", spec.rhythm_density),
            "mode": spec.mode,
            "root_pitch": root_pitch,
        }
        motifs[label] = generate_motif(motif_params)
    sketches = expand_form(spec, motifs)
    harmony_map = generate_harmony(spec, sketches)
    return motifs, sketches, harmony_map


def _render_melody(
    sketches: List[SectionSketch], tempo: float, program: int
) -> "pretty_midi.Instrument":
    """Render melodic line to PrettyMIDI instrument.

    Args:
        sketches: Section sketches to serialise.
        tempo: Tempo in BPM.
        program: General MIDI program number for the instrument.

    Returns:
        Populated :class:`pretty_midi.Instrument` instance.
    """

    pretty_midi = _require_pretty_midi()
    instrument = pretty_midi.Instrument(program=program)
    beat_cursor = 0.0
    for sketch in sketches:
        for note in sketch.notes:
            start = beats_to_seconds(beat_cursor, tempo)
            end = beats_to_seconds(beat_cursor + note.duration_beats, tempo)
            instrument.notes.append(
                pretty_midi.Note(pitch=note.pitch, start=start, end=end, velocity=95)
            )
            beat_cursor += note.duration_beats
    return instrument


def _render_harmony(
    sketches: List[SectionSketch],
    harmony_map: Dict[str, List[HarmonyEvent]],
    tempo: float,
    program: int,
) -> "pretty_midi.Instrument":
    """Render harmony layer.

    Args:
        sketches: Section sketches aligning to harmony events.
        harmony_map: Mapping from section name to harmony events.
        tempo: Tempo in BPM.
        program: General MIDI program number.

    Returns:
        Populated harmony instrument.
    """

    pretty_midi = _require_pretty_midi()
    instrument = pretty_midi.Instrument(program=program)
    beat_cursor = 0.0
    for sketch in sketches:
        for event in harmony_map.get(sketch.name, []):
            start = beats_to_seconds(beat_cursor + event.start_beat, tempo)
            end = beats_to_seconds(
                beat_cursor + event.start_beat + event.duration_beats, tempo
            )
            for pitch in event.pitches:
                instrument.notes.append(
                    pretty_midi.Note(pitch=pitch, start=start, end=end, velocity=70)
                )
        beat_cursor += sum(note.duration_beats for note in sketch.notes)
    return instrument


def _render_bass(
    sketches: List[SectionSketch],
    harmony_map: Dict[str, List[HarmonyEvent]],
    tempo: float,
) -> "pretty_midi.Instrument":
    """Render a simple pedal bass line.

    Args:
        sketches: Section sketches for timing reference.
        harmony_map: Harmony events describing bass motion.
        tempo: Tempo in BPM.

    Returns:
        Bass instrument emphasising root motion.
    """

    pretty_midi = _require_pretty_midi()
    instrument = pretty_midi.Instrument(program=33)
    beat_cursor = 0.0
    for sketch in sketches:
        for event in harmony_map.get(sketch.name, []):
            start = beats_to_seconds(beat_cursor + event.start_beat, tempo)
            end = beats_to_seconds(
                beat_cursor + event.start_beat + event.duration_beats, tempo
            )
            instrument.notes.append(
                pretty_midi.Note(
                    pitch=event.bass_pitch, start=start, end=end, velocity=80
                )
            )
        beat_cursor += sum(note.duration_beats for note in sketch.notes)
    return instrument


def _render_percussion(total_beats: float, tempo: float) -> "pretty_midi.Instrument":
    """Render a basic hi-hat pulse for textual demos.

    Args:
        total_beats: Total number of beats in the arrangement.
        tempo: Tempo in BPM.

    Returns:
        Percussion instrument emphasising metre.
    """

    pretty_midi = _require_pretty_midi()
    instrument = pretty_midi.Instrument(program=0, is_drum=True)
    beat = 0.0
    while beat < total_beats:
        start = beats_to_seconds(beat, tempo)
        end = beats_to_seconds(beat + 0.25, tempo)
        instrument.notes.append(
            pretty_midi.Note(pitch=42, start=start, end=end, velocity=60)
        )
        beat += 1.0
    return instrument


def _build_section_summaries(
    spec: ProjectSpec,
    sketches: List[SectionSketch],
    harmony_map: Dict[str, List[HarmonyEvent]],
) -> Dict[str, SectionSummary]:
    """Summarise each section into text-friendly data structures.

    Args:
        spec: Original project specification for motif labels.
        sketches: Expanded melodic sketches for each section.
        harmony_map: Harmony events aligned with the sections.

    Returns:
        Mapping from section name to :class:`SectionSummary` objects.
    """

    section_lookup: Dict[str, FormSection] = {
        section.section: section for section in spec.form
    }
    summaries: Dict[str, SectionSummary] = {}
    for sketch in sketches:
        form_section = section_lookup.get(sketch.name)
        motif_label = form_section.motif_label if form_section else "unknown"
        harmony_events = harmony_map.get(sketch.name, [])
        chords = [event.chord_name for event in harmony_events]
        unique_pitches = sorted({note.pitch for note in sketch.notes})
        summaries[sketch.name] = SectionSummary(
            name=sketch.name,
            motif_label=motif_label,
            note_count=len(sketch.notes),
            unique_pitches=unique_pitches,
            chords=chords,
        )
    return summaries


def _write_summary_file(
    summary_path: Path, summaries: Iterable[SectionSummary]
) -> None:
    """Persist human-readable summaries to disk.

    Args:
        summary_path: Destination file path.
        summaries: Iterable of section summaries to serialise.
    """

    lines = [summary.describe() for summary in summaries]
    summary_path.write_text("\n".join(lines), encoding="utf-8")


def render_project(
    project_spec: ProjectSpec, output_dir: str | Path, emit_midi: bool = False
) -> RenderResult:
    """Render the project into textual artefacts and optionally MIDI.

    Args:
        project_spec: Fully populated :class:`ProjectSpec` describing the work.
        output_dir: Directory where artefacts should be placed.
        emit_midi: Whether to serialise a ``.mid`` file. Defaults to ``False`` to
            honour the text-only behaviour required in continuous integration.

    Returns:
        A :class:`RenderResult` describing the created artefacts.
    """

    output_path = ensure_directory(output_dir)
    logger.info("Rendering project into %s (emit_midi=%s)", output_path, emit_midi)

    _, sketches, harmony_map = _collect_sections(project_spec)
    summaries = _build_section_summaries(project_spec, sketches, harmony_map)

    existing_counts = project_spec.generated_sections or {}
    serialised_summaries: Dict[str, Dict[str, object]] = {}
    for name, summary in summaries.items():
        serialised = summary.as_dict()
        # 保留已有的再生次数，确保多次渲染时历史信息不丢失。
        serialised["regeneration_count"] = int(
            existing_counts.get(name, {}).get("regeneration_count", 0)
        )
        serialised_summaries[name] = serialised

    updated_spec = project_spec.model_copy(
        update={"generated_sections": serialised_summaries}
    )

    spec_path = output_path / "spec.json"
    spec_path.write_text(
        json.dumps(updated_spec.model_dump(mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    summary_path = output_path / "summary.txt"
    _write_summary_file(summary_path, summaries.values())

    midi_path: Path | None = None
    if emit_midi:
        pretty_midi = _require_pretty_midi()
        tempo = float(project_spec.tempo_bpm)
        instrumentation = project_spec.instrumentation or ["piano"]
        midi = pretty_midi.PrettyMIDI()
        primary_program = program_for_instrument(instrumentation[0])
        midi.instruments.append(_render_melody(sketches, tempo, primary_program))
        harmony_program = (
            program_for_instrument(instrumentation[1])
            if len(instrumentation) > 1
            else 48
        )
        midi.instruments.append(
            _render_harmony(sketches, harmony_map, tempo, harmony_program)
        )
        midi.instruments.append(_render_bass(sketches, harmony_map, tempo))
        total_beats = sum(
            sum(note.duration_beats for note in sketch.notes) for sketch in sketches
        )
        midi.instruments.append(_render_percussion(total_beats, tempo))
        midi_path = output_path / "track.mid"
        midi.write(str(midi_path))
        logger.info("MIDI file written to %s", midi_path)

    return RenderResult(
        output_dir=str(output_path),
        spec=str(spec_path),
        summary=str(summary_path),
        midi=str(midi_path) if midi_path else None,
        sections=serialised_summaries,
    )


def regenerate_section(
    project_spec: ProjectSpec, section_name: str
) -> tuple[ProjectSpec, Dict[str, Dict[str, object]]]:
    """Regenerate a single section while preserving others.

    Args:
        project_spec: Existing project specification with (optional) cached summaries.
        section_name: Identifier of the section to regenerate (e.g. ``"B"``).

    Returns:
        A tuple containing the updated :class:`ProjectSpec` and the combined
        section summaries (including unchanged sections).

    Raises:
        ValueError: If the section does not exist in the specification.
    """

    existing = dict(project_spec.generated_sections or {})
    _, sketches, harmony_map = _collect_sections(project_spec)
    summaries = _build_section_summaries(project_spec, sketches, harmony_map)
    if section_name not in summaries:
        raise ValueError(f"Unknown section '{section_name}' in specification")
    new_summary = summaries[section_name].as_dict()
    previous_count = int(existing.get(section_name, {}).get("regeneration_count", 0))
    new_summary["regeneration_count"] = previous_count + 1
    existing[section_name] = new_summary
    updated_spec = project_spec.model_copy(update={"generated_sections": existing})
    return updated_spec, existing


__all__ = ["RenderResult", "regenerate_section", "render_project"]


def _require_pretty_midi() -> "pretty_midi":
    """Import :mod:`pretty_midi` lazily to avoid hard dependency.

    Returns:
        The imported :mod:`pretty_midi` module.

    Raises:
        RuntimeError: If :mod:`pretty_midi` 未安装但调用了需要 MIDI 的功能。
    """

    try:
        import pretty_midi
    except ModuleNotFoundError as exc:  # pragma: no cover - optional dependency
        raise RuntimeError(
            "pretty_midi is required when emit_midi=True; install optional dependencies"
        ) from exc
    return pretty_midi
