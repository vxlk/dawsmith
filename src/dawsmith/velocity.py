"""Velocity / dynamics constants for MIDI note intensity.

Velocities resolve to int (0-127) via ``__int__``/``__index__``.
Named after standard musical dynamics markings.

Usage::

    from dawsmith import mf, f, pp

    clip.add_note(C4, 0.0, QUARTER, mf)        # mezzo-forte (80)
    clip.add_note(C4, 1.0, QUARTER, f.accent)   # forte + 20 = 116
    clip.add_note(C4, 2.0, QUARTER, pp.ghost)   # pp - 30 = 3
    clip.add_note(C4, 3.0, QUARTER, mf + 10)    # 90
"""

from __future__ import annotations


class Velocity:
    """MIDI velocity (0-127) with musical dynamics names.

    Resolves to int for the C++ layer via ``__int__``/``__index__``.
    Values are silently clamped to the 0-127 range.

    Args:
        value: MIDI velocity value (clamped to 0-127).
        name: Optional dynamics name (e.g. ``"mf"``).
    """

    __slots__ = ("_value", "_name")

    def __init__(self, value: int, name: str | None = None) -> None:
        self._value = max(0, min(127, int(value)))
        self._name = name

    def __int__(self) -> int:
        return self._value

    def __index__(self) -> int:
        return self._value

    def __add__(self, other: int) -> Velocity:
        return Velocity(self._value + int(other))

    def __radd__(self, other: int) -> Velocity:
        return Velocity(int(other) + self._value)

    def __sub__(self, other: int) -> Velocity:
        return Velocity(self._value - int(other))

    def __rsub__(self, other: int) -> Velocity:
        return Velocity(int(other) - self._value)

    @property
    def accent(self) -> Velocity:
        """Accented: +20 velocity, clamped to 127."""
        return Velocity(self._value + 20)

    @property
    def ghost(self) -> Velocity:
        """Ghost note: -30 velocity, minimum 1."""
        return Velocity(max(1, self._value - 30))

    def __eq__(self, other: object) -> bool:
        return self._value == int(other)  # type: ignore[arg-type]

    def __lt__(self, other: int | Velocity) -> bool:
        return self._value < int(other)

    def __le__(self, other: int | Velocity) -> bool:
        return self._value <= int(other)

    def __gt__(self, other: int | Velocity) -> bool:
        return self._value > int(other)

    def __ge__(self, other: int | Velocity) -> bool:
        return self._value >= int(other)

    def __hash__(self) -> int:
        return hash(self._value)

    def __repr__(self) -> str:
        if self._name:
            return f"{self._name}({self._value})"
        return f"Velocity({self._value})"

    @property
    def value(self) -> int:
        """The clamped MIDI velocity value (0-127)."""
        return self._value


# --- Standard dynamics ---

ppp = Velocity(16, "ppp")
pp = Velocity(33, "pp")
p = Velocity(49, "p")
mp = Velocity(64, "mp")
mf = Velocity(80, "mf")
f = Velocity(96, "f")
ff = Velocity(112, "ff")
fff = Velocity(127, "fff")

__all__ = [
    "Velocity",
    "ppp",
    "pp",
    "p",
    "mp",
    "mf",
    "f",
    "ff",
    "fff",
]
