"""Utility helpers for Motifmaker."""

from __future__ import annotations

from pathlib import Path
from typing import Dict

PROGRAM_MAP: Dict[str, int] = {
    "piano": 0,
    "strings": 48,
    "violin": 40,
    "electric-piano": 4,
    "synth-pad": 88,
    "synth-bass": 38,
    "guitar": 24,
}


def beats_to_seconds(beats: float, tempo_bpm: float) -> float:
    """Convert beats into seconds at a given tempo."""

    return (60.0 / tempo_bpm) * beats


def ensure_directory(path: str | Path) -> Path:
    """Ensure a directory exists and return it as :class:`Path`."""

    directory = Path(path)
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def program_for_instrument(name: str) -> int:
    """Map a textual instrument name to a MIDI program number."""

    return PROGRAM_MAP.get(name, 0)


__all__ = [
    "beats_to_seconds",
    "ensure_directory",
    "program_for_instrument",
    "PROGRAM_MAP",
]
