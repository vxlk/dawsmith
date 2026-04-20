"""Duration constants for musical note lengths.

Durations resolve to float (beats) via ``__float__``.
Convention: QUARTER = 1.0 beat (standard in 4/4 time).

Usage::

    from dawsmith import QUARTER, EIGHTH, HALF, WHOLE

    clip.add_note(C4, 0.0, QUARTER)        # 1 beat
    clip.add_note(C4, 1.0, QUARTER.dot)    # 1.5 beats (dotted quarter)
    clip.add_note(C4, 2.5, EIGHTH.triplet) # 0.333 beats
    clip.add_note(C4, 0.0, QUARTER + EIGHTH)  # tied: 1.5 beats
"""

from __future__ import annotations


class Duration:
    """A musical duration in beats. QUARTER = 1.0 beat.

    Resolves to float for the C++ layer via ``__float__``.

    Args:
        beats: Length in beats (must be non-negative).
        name: Optional display name (e.g. ``"QUARTER"``).

    Raises:
        ValueError: If *beats* is negative.
    """

    __slots__ = ("_beats", "_name")

    def __init__(self, beats: float, name: str | None = None) -> None:
        beats = float(beats)
        if beats < 0:
            raise ValueError(f"Duration must be non-negative, got {beats}")
        self._beats = beats
        self._name = name

    def __float__(self) -> float:
        return self._beats

    def __add__(self, other: float | Duration) -> Duration:
        return Duration(self._beats + float(other))

    def __radd__(self, other: float) -> Duration:
        return Duration(float(other) + self._beats)

    def __sub__(self, other: float | Duration) -> Duration:
        return Duration(self._beats - float(other))

    def __mul__(self, factor: float) -> Duration:
        return Duration(self._beats * float(factor))

    def __rmul__(self, factor: float) -> Duration:
        return Duration(self._beats * float(factor))

    def __truediv__(self, divisor: float) -> Duration:
        return Duration(self._beats / float(divisor))

    @property
    def dot(self) -> Duration:
        """Dotted duration (1.5x)."""
        name = f"{self._name}.dot" if self._name else None
        return Duration(self._beats * 1.5, name)

    @property
    def triplet(self) -> Duration:
        """Triplet duration (2/3x)."""
        name = f"{self._name}.triplet" if self._name else None
        return Duration(self._beats * 2 / 3, name)

    @property
    def double_dot(self) -> Duration:
        """Double-dotted duration (1.75x)."""
        name = f"{self._name}.double_dot" if self._name else None
        return Duration(self._beats * 1.75, name)

    def __eq__(self, other: object) -> bool:
        return abs(self._beats - float(other)) < 1e-9  # type: ignore[arg-type]

    def __lt__(self, other: float | Duration) -> bool:
        return self._beats < float(other)

    def __le__(self, other: float | Duration) -> bool:
        return self._beats <= float(other)

    def __gt__(self, other: float | Duration) -> bool:
        return self._beats > float(other)

    def __ge__(self, other: float | Duration) -> bool:
        return self._beats >= float(other)

    def __hash__(self) -> int:
        return hash(self._beats)

    def __repr__(self) -> str:
        if self._name:
            return self._name
        return f"Duration({self._beats})"

    @property
    def beats(self) -> float:
        """Length in beats."""
        return self._beats


# --- Named duration constants ---

WHOLE = Duration(4.0, "WHOLE")
HALF = Duration(2.0, "HALF")
QUARTER = Duration(1.0, "QUARTER")
EIGHTH = Duration(0.5, "EIGHTH")
SIXTEENTH = Duration(0.25, "SIXTEENTH")
THIRTY_SECOND = Duration(0.125, "THIRTY_SECOND")

__all__ = [
    "Duration",
    "WHOLE",
    "HALF",
    "QUARTER",
    "EIGHTH",
    "SIXTEENTH",
    "THIRTY_SECOND",
]
