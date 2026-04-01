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


class Duration:
    """A musical duration in beats. QUARTER = 1.0 beat.

    Resolves to float for the C++ layer via ``__float__``.
    """

    __slots__ = ("_beats", "_name")

    def __init__(self, beats, name=None):
        beats = float(beats)
        if beats < 0:
            raise ValueError(f"Duration must be non-negative, got {beats}")
        self._beats = beats
        self._name = name

    def __float__(self):
        return self._beats

    def __add__(self, other):
        return Duration(self._beats + float(other))

    def __radd__(self, other):
        return Duration(float(other) + self._beats)

    def __sub__(self, other):
        return Duration(self._beats - float(other))

    def __mul__(self, factor):
        return Duration(self._beats * float(factor))

    def __rmul__(self, factor):
        return Duration(self._beats * float(factor))

    def __truediv__(self, divisor):
        return Duration(self._beats / float(divisor))

    @property
    def dot(self):
        """Dotted duration (1.5x)."""
        name = f"{self._name}.dot" if self._name else None
        return Duration(self._beats * 1.5, name)

    @property
    def triplet(self):
        """Triplet duration (2/3x)."""
        name = f"{self._name}.triplet" if self._name else None
        return Duration(self._beats * 2 / 3, name)

    @property
    def double_dot(self):
        """Double-dotted duration (1.75x)."""
        name = f"{self._name}.double_dot" if self._name else None
        return Duration(self._beats * 1.75, name)

    def __eq__(self, other):
        return abs(self._beats - float(other)) < 1e-9

    def __lt__(self, other):
        return self._beats < float(other)

    def __le__(self, other):
        return self._beats <= float(other)

    def __gt__(self, other):
        return self._beats > float(other)

    def __ge__(self, other):
        return self._beats >= float(other)

    def __hash__(self):
        return hash(self._beats)

    def __repr__(self):
        if self._name:
            return self._name
        return f"Duration({self._beats})"

    @property
    def beats(self):
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
