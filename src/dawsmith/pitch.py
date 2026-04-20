"""Pitch and interval constants for musical note representation.

Pitches are named constants that resolve to MIDI note numbers via ``__int__``.
Octave convention: C4 = 60 (MIDI standard).

Usage::

    from dawsmith.pitch import C4, E4, G4, Csharp4, Eflat3
    import dawsmith.pitch as n  # short alias

    clip.add_note(C4, 0.0, 1.0)       # middle C
    clip.add_note(n.Eflat3, 1.0, 1.0)  # Eb below middle C
    clip.add_note(C4 + PERFECT_FIFTH, 2.0, 1.0)  # G4
"""

from __future__ import annotations

from typing import Literal, overload

NoteName = Literal[
    "C-1", "C#-1", "Db-1", "D-1", "D#-1", "Eb-1", "E-1", "F-1", "F#-1", "Gb-1", "G-1", "G#-1", "Ab-1", "A-1", "A#-1", "Bb-1", "B-1",
    "C0", "C#0", "Db0", "D0", "D#0", "Eb0", "E0", "F0", "F#0", "Gb0", "G0", "G#0", "Ab0", "A0", "A#0", "Bb0", "B0",
    "C1", "C#1", "Db1", "D1", "D#1", "Eb1", "E1", "F1", "F#1", "Gb1", "G1", "G#1", "Ab1", "A1", "A#1", "Bb1", "B1",
    "C2", "C#2", "Db2", "D2", "D#2", "Eb2", "E2", "F2", "F#2", "Gb2", "G2", "G#2", "Ab2", "A2", "A#2", "Bb2", "B2",
    "C3", "C#3", "Db3", "D3", "D#3", "Eb3", "E3", "F3", "F#3", "Gb3", "G3", "G#3", "Ab3", "A3", "A#3", "Bb3", "B3",
    "C4", "C#4", "Db4", "D4", "D#4", "Eb4", "E4", "F4", "F#4", "Gb4", "G4", "G#4", "Ab4", "A4", "A#4", "Bb4", "B4",
    "C5", "C#5", "Db5", "D5", "D#5", "Eb5", "E5", "F5", "F#5", "Gb5", "G5", "G#5", "Ab5", "A5", "A#5", "Bb5", "B5",
    "C6", "C#6", "Db6", "D6", "D#6", "Eb6", "E6", "F6", "F#6", "Gb6", "G6", "G#6", "Ab6", "A6", "A#6", "Bb6", "B6",
    "C7", "C#7", "Db7", "D7", "D#7", "Eb7", "E7", "F7", "F#7", "Gb7", "G7", "G#7", "Ab7", "A7", "A#7", "Bb7", "B7",
    "C8", "C#8", "Db8", "D8", "D#8", "Eb8", "E8", "F8", "F#8", "Gb8", "G8", "G#8", "Ab8", "A8", "A#8", "Bb8", "B8",
    "C9", "C#9", "Db9", "D9", "D#9", "Eb9", "E9", "F9", "F#9", "Gb9", "G9",
]


class Pitch:
    """A MIDI pitch that supports musical arithmetic.

    Resolves to int for the C++ layer via ``__int__``/``__index__``.

    Args:
        midi: MIDI note number (0-127).
        name: Optional display name (e.g. ``"C4"``).

    Raises:
        ValueError: If *midi* is outside the 0-127 range.
    """

    __slots__ = ("_midi", "_name")

    def __init__(self, midi: int, name: str | None = None) -> None:
        midi = int(midi)
        if not 0 <= midi <= 127:
            raise ValueError(f"MIDI pitch must be 0-127, got {midi}")
        self._midi = midi
        self._name = name

    def __int__(self) -> int:
        return self._midi

    def __index__(self) -> int:
        return self._midi

    def __add__(self, other: int | Interval) -> Pitch:
        if isinstance(other, Pitch):
            raise TypeError("Cannot add two pitches; use pitch + interval (int)")
        return Pitch(self._midi + int(other))

    def __radd__(self, other: int) -> Pitch:
        return Pitch(int(other) + self._midi)

    @overload
    def __sub__(self, other: Pitch) -> int: ...
    @overload
    def __sub__(self, other: int | Interval) -> Pitch: ...

    def __sub__(self, other: Pitch | int | Interval) -> int | Pitch:
        if isinstance(other, Pitch):
            return self._midi - other._midi
        return Pitch(self._midi - int(other))

    def __rsub__(self, other: int) -> Pitch:
        return Pitch(int(other) - self._midi)

    def __eq__(self, other: object) -> bool:
        return self._midi == int(other)  # type: ignore[arg-type]

    def __lt__(self, other: int | Pitch) -> bool:
        return self._midi < int(other)

    def __le__(self, other: int | Pitch) -> bool:
        return self._midi <= int(other)

    def __gt__(self, other: int | Pitch) -> bool:
        return self._midi > int(other)

    def __ge__(self, other: int | Pitch) -> bool:
        return self._midi >= int(other)

    def __hash__(self) -> int:
        return hash(self._midi)

    def __repr__(self) -> str:
        if self._name:
            return self._name
        return f"Pitch({self._midi})"

    @property
    def midi(self) -> int:
        """MIDI note number (0-127)."""
        return self._midi

    @property
    def name(self) -> str | None:
        """Display name, or ``None`` for unnamed pitches."""
        return self._name

    @property
    def octave(self) -> int:
        """Octave number (C4 = octave 4)."""
        return (self._midi // 12) - 1

    @property
    def pitch_class(self) -> int:
        """Pitch class (0-11, where 0 = C, 1 = C#/Db, ..., 11 = B)."""
        return self._midi % 12


class Interval:
    """A musical interval in semitones. Adds to Pitch to produce a new Pitch.

    Args:
        semitones: Number of semitones.
        name: Optional display name (e.g. ``"PERFECT_FIFTH"``).
    """

    __slots__ = ("_semitones", "_name")

    def __init__(self, semitones: int, name: str | None = None) -> None:
        self._semitones = int(semitones)
        self._name = name

    def __int__(self) -> int:
        return self._semitones

    def __index__(self) -> int:
        return self._semitones

    def __repr__(self) -> str:
        return self._name or f"Interval({self._semitones})"

    def __eq__(self, other: object) -> bool:
        return self._semitones == int(other)  # type: ignore[arg-type]

    def __hash__(self) -> int:
        return hash(self._semitones)


# --- Named intervals ---

UNISON = Interval(0, "UNISON")
MINOR_SECOND = Interval(1, "MINOR_SECOND")
MAJOR_SECOND = Interval(2, "MAJOR_SECOND")
MINOR_THIRD = Interval(3, "MINOR_THIRD")
MAJOR_THIRD = Interval(4, "MAJOR_THIRD")
PERFECT_FOURTH = Interval(5, "PERFECT_FOURTH")
TRITONE = Interval(6, "TRITONE")
PERFECT_FIFTH = Interval(7, "PERFECT_FIFTH")
MINOR_SIXTH = Interval(8, "MINOR_SIXTH")
MAJOR_SIXTH = Interval(9, "MAJOR_SIXTH")
MINOR_SEVENTH = Interval(10, "MINOR_SEVENTH")
MAJOR_SEVENTH = Interval(11, "MAJOR_SEVENTH")
OCTAVE = Interval(12, "OCTAVE")


# --- Named pitch constants ---

# Mapping: pitch class -> (natural/sharp name, flat name or None)
_NOTE_NAMES: dict[int, tuple[str, str | None]] = {
    0: ("C", None),
    1: ("Csharp", "Dflat"),
    2: ("D", None),
    3: ("Dsharp", "Eflat"),
    4: ("E", None),
    5: ("F", None),
    6: ("Fsharp", "Gflat"),
    7: ("G", None),
    8: ("Gsharp", "Aflat"),
    9: ("A", None),
    10: ("Asharp", "Bflat"),
    11: ("B", None),
}

# Reverse mapping for note() string parsing: normalized name -> pitch class
_PARSE_MAP: dict[str, int] = {}


def _generate_pitches() -> dict[str, Pitch]:
    """Generate all named pitch constants C0..G9, including enharmonic spellings."""
    pitches: dict[str, Pitch] = {}
    for midi in range(128):
        octave = (midi // 12) - 1
        pc = midi % 12
        sharp_name, flat_name = _NOTE_NAMES[pc]

        name = f"{sharp_name}{octave}"
        pitches[name] = Pitch(midi, name)

        if flat_name:
            fname = f"{flat_name}{octave}"
            pitches[fname] = Pitch(midi, fname)

    return pitches


_ALL_PITCHES: dict[str, Pitch] = _generate_pitches()

# Inject into module namespace so `from dawsmith.pitch import C4` works
globals().update(_ALL_PITCHES)

# Build parse map for note() function
for _pc, (_sharp, _flat) in _NOTE_NAMES.items():
    _PARSE_MAP[_sharp.lower()] = _pc
    if _flat:
        _PARSE_MAP[_flat.lower()] = _pc
# Also support '#' and 'b' shorthand in note() parsing
for _pc, (_sharp, _flat) in _NOTE_NAMES.items():
    _base = _sharp[0].lower()  # e.g. 'c', 'd', etc.
    if len(_sharp) > 1:  # has sharp variant
        _PARSE_MAP[_base + "#"] = _pc
        _PARSE_MAP[_base + "s"] = _pc
    if _flat:
        _PARSE_MAP[_flat[0].lower() + "b"] = _pc


def note(name: NoteName) -> Pitch:
    """Parse a note name string to a Pitch.

    Accepts: ``"C4"``, ``"C#4"``, ``"Cb4"``, ``"Csharp4"``, ``"Dflat4"``, etc.

    Args:
        name: Note name string with octave number.

    Returns:
        The corresponding ``Pitch`` object.

    Raises:
        ValueError: If *name* cannot be parsed or is out of MIDI range.

    Examples::

        note("C4")    # -> Pitch(60)
        note("C#4")   # -> Pitch(61)
        note("Eb3")   # -> Pitch(51)
    """
    # Try direct lookup first (handles Csharp4, Dflat4, C4, etc.)
    normalized = name.replace("#", "sharp").replace("\u266f", "sharp").replace("\u266d", "flat")
    if normalized in _ALL_PITCHES:
        return _ALL_PITCHES[normalized]

    # Parse letter + accidental + octave
    s = name.strip()
    # Find where the octave number starts (possibly negative for octave -1)
    i = len(s) - 1
    while i > 0 and (s[i].isdigit() or (s[i] == "-" and i > 0)):
        i -= 1
    i += 1

    note_part = s[:i].lower().replace("#", "sharp").replace("\u266f", "sharp").replace("\u266d", "flat")
    oct_part = s[i:]

    try:
        octave = int(oct_part)
    except ValueError:
        raise ValueError(f"Unknown note name: {name!r}") from None

    if note_part not in _PARSE_MAP:
        raise ValueError(f"Unknown note name: {name!r}")

    pc = _PARSE_MAP[note_part]
    midi = (octave + 1) * 12 + pc
    if not 0 <= midi <= 127:
        raise ValueError(f"Note {name!r} is out of MIDI range (midi={midi})")

    return Pitch(midi, name)


# Build __all__ for star imports
__all__ = [
    "Pitch",
    "Interval",
    "NoteName",
    "note",
    "UNISON",
    "MINOR_SECOND",
    "MAJOR_SECOND",
    "MINOR_THIRD",
    "MAJOR_THIRD",
    "PERFECT_FOURTH",
    "TRITONE",
    "PERFECT_FIFTH",
    "MINOR_SIXTH",
    "MAJOR_SIXTH",
    "MINOR_SEVENTH",
    "MAJOR_SEVENTH",
    "OCTAVE",
] + list(_ALL_PITCHES.keys())
