"""General-purpose utilities used across the Motifmaker package.

This module intentionally keeps the helpers lightweight so that they can be
reused by both the command line interface and the FastAPI service without
introducing any side effects.  Each function includes comprehensive type
annotations and documentation to make the behaviour explicit.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict

# Public constant that exposes a minimal mapping from semantic instrument names
# to General MIDI program numbers.  The mapping is intentionally sparse but
# covers the typical instrument hints produced by the parser.
PROGRAM_MAP: Dict[str, int] = {
    "piano": 0,
    "strings": 48,
    "violin": 40,
    "electric-piano": 4,
    "synth-pad": 88,
    "synth-bass": 38,
    "guitar": 24,
}

_LOG_FORMAT = "% (levelname)s [%(name)s] %(message)s".replace(" %", "%")


def configure_logging(level: int) -> None:
    """Configure basic logging for the current process.

    The helper is used by the CLI entry points to expose ``--verbose`` and
    ``--debug`` switches.  Reconfiguring logging multiple times would normally
    produce duplicate handlers, so the implementation guards against that and
    only installs a handler when necessary.

    Args:
        level: Logging level to apply to the root logger, e.g. ``logging.INFO``.
    """

    root_logger = logging.getLogger()
    if not root_logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(_LOG_FORMAT))
        root_logger.addHandler(handler)
    root_logger.setLevel(level)


def beats_to_seconds(beats: float, tempo_bpm: float) -> float:
    """Convert beats into seconds at the given tempo.

    Args:
        beats: Musical beats to convert. ``0`` or negative values are supported
            and simply yield ``0`` or a negative number of seconds.
        tempo_bpm: Tempo in beats per minute. Must be greater than ``0``.

    Returns:
        The duration in seconds that corresponds to the provided number of
        beats.

    Raises:
        ValueError: If ``tempo_bpm`` is ``0`` or negative.

    Examples:
        >>> round(beats_to_seconds(4, 120), 2)
        2.0
    """

    if tempo_bpm <= 0:
        raise ValueError("Tempo must be positive for beat to second conversion")
    # Convert beats to seconds using the reciprocal of beats per minute.
    return (60.0 / tempo_bpm) * beats


def ensure_directory(path: str | Path) -> Path:
    """Ensure that ``path`` exists as a directory and return it.

    The helper mirrors ``Path.mkdir`` with ``parents=True`` but makes the
    behaviour explicit within the code base.  Returning the :class:`Path`
    object simplifies chaining, especially in the CLI where the resolved path
    is often needed for downstream logging or serialization.

    Args:
        path: Target directory represented as a string or :class:`Path`.

    Returns:
        The resolved :class:`Path` pointing to the directory.  The directory is
        guaranteed to exist upon return.
    """

    directory = Path(path)
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def program_for_instrument(name: str) -> int:
    """Map a semantic instrument name to a General MIDI program number.

    Args:
        name: Instrument name such as ``"piano"`` or ``"strings"``.

    Returns:
        The matching MIDI program number.  Unknown names fall back to ``0``
        (acoustic grand piano) which is a safe default for textual-only runs.
    """

    return PROGRAM_MAP.get(name, 0)


__all__ = [
    "PROGRAM_MAP",
    "beats_to_seconds",
    "configure_logging",
    "ensure_directory",
    "program_for_instrument",
]
