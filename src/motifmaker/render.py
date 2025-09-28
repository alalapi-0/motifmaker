"""Rendering utilities for combining melodic layers into MIDI output."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Tuple

import pretty_midi

from .form import SectionSketch, expand_form
from .harmony import HarmonyEvent, generate_harmony
from .motif import Motif, generate_motif
from .schema import ProjectSpec
from .utils import beats_to_seconds, ensure_directory, program_for_instrument


def _root_pitch_from_key(key: str) -> int:
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
    root_pitch = _root_pitch_from_key(spec.key)
    motifs: Dict[str, Motif] = {}
    for label, motif_spec in spec.motif_specs.items():
        motif_params = dict(motif_spec)
        motif_params.setdefault("mode", spec.mode)
        motif_params.setdefault("root_pitch", root_pitch)
        motifs[label] = generate_motif(motif_params)
    sketches = expand_form(spec, motifs)
    harmony_map = generate_harmony(spec, sketches)
    return motifs, sketches, harmony_map


def _render_melody(
    sketches: List[SectionSketch], tempo: float, program: int
) -> pretty_midi.Instrument:
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
) -> pretty_midi.Instrument:
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
) -> pretty_midi.Instrument:
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
                    pitch=event.bass_pitch,
                    start=start,
                    end=end,
                    velocity=80,
                )
            )
        beat_cursor += sum(note.duration_beats for note in sketch.notes)
    return instrument


def _render_percussion(total_beats: float, tempo: float) -> pretty_midi.Instrument:
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


def render_project(
    project_spec: ProjectSpec, out_mid_path: str | Path, out_json_path: str | Path
) -> Dict[str, str]:
    """Render the full project to MIDI and save the specification."""

    _, sketches, harmony_map = _collect_sections(project_spec)
    tempo = float(project_spec.tempo_bpm)

    instruments: List[pretty_midi.Instrument] = []
    instrumentation = project_spec.instrumentation or ["piano"]
    primary_program = program_for_instrument(instrumentation[0])
    instruments.append(_render_melody(sketches, tempo, primary_program))

    harmony_program = (
        program_for_instrument(instrumentation[1]) if len(instrumentation) > 1 else 48
    )
    instruments.append(_render_harmony(sketches, harmony_map, tempo, harmony_program))
    instruments.append(_render_bass(sketches, harmony_map, tempo))

    total_beats = sum(
        sum(note.duration_beats for note in sketch.notes) for sketch in sketches
    )
    instruments.append(_render_percussion(total_beats, tempo))

    midi = pretty_midi.PrettyMIDI()
    for inst in instruments:
        midi.instruments.append(inst)

    out_mid_path = Path(out_mid_path)
    out_json_path = Path(out_json_path)
    ensure_directory(out_mid_path.parent)
    ensure_directory(out_json_path.parent)

    midi.write(str(out_mid_path))
    out_json_path.write_text(
        json.dumps(project_spec.model_dump(mode="json"), ensure_ascii=False, indent=2)
    )

    return {"midi": str(out_mid_path), "spec": str(out_json_path)}


__all__ = ["render_project"]
