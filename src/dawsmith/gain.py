"""Gain constants mapping common dB values to linear gain.

Linear gain is the native unit for ``AudioClip.set_gain()`` and
``Track.set_volume()``.  This module provides named constants at
standard dB levels and a ``db()`` convenience function for arbitrary
conversions.

Usage::

    from dawsmith.gain import db, UNITY, DB_MINUS_6, SILENT

    clip.set_gain(DB_MINUS_6)     # ~0.501
    clip.set_gain(db(-3))         # ~0.708
    track.set_volume(db(-12))     # ~0.251
"""

import math


class Gain:
    """Linear gain value with dB awareness.

    Resolves to float for the C++ layer via ``__float__``.
    """

    __slots__ = ("_value", "_name")

    def __init__(self, value, name=None):
        self._value = float(value)
        self._name = name

    @classmethod
    def from_db(cls, db_value, name=None):
        """Create a Gain from a decibel value."""
        if db_value <= -100.0:
            return cls(0.0, name)
        return cls(10.0 ** (db_value / 20.0), name)

    def to_db(self):
        """Convert this linear gain to decibels."""
        if self._value <= 0.0:
            return float("-inf")
        return 20.0 * math.log10(self._value)

    def __float__(self):
        return self._value

    def __int__(self):
        return int(self._value)

    def __add__(self, other):
        return Gain(self._value + float(other))

    def __radd__(self, other):
        return Gain(float(other) + self._value)

    def __sub__(self, other):
        return Gain(self._value - float(other))

    def __rsub__(self, other):
        return Gain(float(other) - self._value)

    def __mul__(self, other):
        return Gain(self._value * float(other))

    def __rmul__(self, other):
        return Gain(float(other) * self._value)

    def __truediv__(self, other):
        return Gain(self._value / float(other))

    def __eq__(self, other):
        return abs(self._value - float(other)) < 1e-9

    def __lt__(self, other):
        return self._value < float(other)

    def __le__(self, other):
        return self._value <= float(other)

    def __gt__(self, other):
        return self._value > float(other)

    def __ge__(self, other):
        return self._value >= float(other)

    def __hash__(self):
        return hash(self._value)

    def __repr__(self):
        if self._name:
            return f"{self._name}({self._value:.6f})"
        return f"Gain({self._value:.6f})"

    @property
    def value(self):
        return self._value


def db(decibels):
    """Convert a dB value to a Gain (linear).

    Example::

        clip.set_gain(db(-6))   # half-amplitude
        clip.set_gain(db(0))    # unity
    """
    return Gain.from_db(decibels)


# --- Named constants ---

SILENT = Gain(0.0, "SILENT")

DB_MINUS_48 = Gain.from_db(-48, "DB_MINUS_48")
DB_MINUS_24 = Gain.from_db(-24, "DB_MINUS_24")
DB_MINUS_12 = Gain.from_db(-12, "DB_MINUS_12")
DB_MINUS_6 = Gain.from_db(-6, "DB_MINUS_6")
DB_MINUS_3 = Gain.from_db(-3, "DB_MINUS_3")
UNITY = Gain.from_db(0, "UNITY")
DB_PLUS_3 = Gain.from_db(3, "DB_PLUS_3")
DB_PLUS_6 = Gain.from_db(6, "DB_PLUS_6")

__all__ = [
    "Gain",
    "db",
    "SILENT",
    "DB_MINUS_48",
    "DB_MINUS_24",
    "DB_MINUS_12",
    "DB_MINUS_6",
    "DB_MINUS_3",
    "UNITY",
    "DB_PLUS_3",
    "DB_PLUS_6",
]
