"""Pitch and interval constants for musical note representation.

Pitches are named constants that resolve to MIDI note numbers via __int__.
Octave convention: C4 = 60 (MIDI standard).

Usage::

    from dawsmith.pitch import C4, E4, G4, Csharp4, Eflat3
    import dawsmith.pitch as n  # short alias

    clip.add_note(C4, 0.0, 1.0)       # middle C
    clip.add_note(n.Eflat3, 1.0, 1.0)  # Eb below middle C
    clip.add_note(C4 + PERFECT_FIFTH, 2.0, 1.0)  # G4
"""


class Pitch:
    """A MIDI pitch that supports musical arithmetic.

    Resolves to int for the C++ layer via ``__int__``/``__index__``.
    """

    __slots__ = ("_midi", "_name")

    def __init__(self, midi, name=None):
        midi = int(midi)
        if not 0 <= midi <= 127:
            raise ValueError(f"MIDI pitch must be 0-127, got {midi}")
        self._midi = midi
        self._name = name

    def __int__(self):
        return self._midi

    def __index__(self):
        return self._midi

    def __add__(self, other):
        if isinstance(other, Pitch):
            raise TypeError("Cannot add two pitches; use pitch + interval (int)")
        return Pitch(self._midi + int(other))

    def __radd__(self, other):
        return Pitch(int(other) + self._midi)

    def __sub__(self, other):
        if isinstance(other, Pitch):
            return self._midi - other._midi  # interval between pitches
        return Pitch(self._midi - int(other))

    def __rsub__(self, other):
        return Pitch(int(other) - self._midi)

    def __eq__(self, other):
        return self._midi == int(other)

    def __lt__(self, other):
        return self._midi < int(other)

    def __le__(self, other):
        return self._midi <= int(other)

    def __gt__(self, other):
        return self._midi > int(other)

    def __ge__(self, other):
        return self._midi >= int(other)

    def __hash__(self):
        return hash(self._midi)

    def __repr__(self):
        if self._name:
            return self._name
        return f"Pitch({self._midi})"

    @property
    def midi(self):
        return self._midi

    @property
    def name(self):
        return self._name

    @property
    def octave(self):
        return (self._midi // 12) - 1

    @property
    def pitch_class(self):
        return self._midi % 12


class Interval:
    """A musical interval in semitones. Adds to Pitch to produce a new Pitch."""

    __slots__ = ("_semitones", "_name")

    def __init__(self, semitones, name=None):
        self._semitones = int(semitones)
        self._name = name

    def __int__(self):
        return self._semitones

    def __index__(self):
        return self._semitones

    def __repr__(self):
        return self._name or f"Interval({self._semitones})"

    def __eq__(self, other):
        return self._semitones == int(other)

    def __hash__(self):
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
_NOTE_NAMES = {
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
_PARSE_MAP = {}


def _generate_pitches():
    """Generate all named pitch constants C0..G9, including enharmonic spellings."""
    pitches = {}
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


_ALL_PITCHES = _generate_pitches()

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


def note(name):
    """Parse a note name string to a Pitch.

    Accepts: ``"C4"``, ``"C#4"``, ``"Cb4"``, ``"Csharp4"``, ``"Dflat4"``, etc.

    Examples::

        note("C4")    # -> Pitch(60)
        note("C#4")   # -> Pitch(61)
        note("Eb3")   # -> Pitch(51)
    """
    # Try direct lookup first (handles Csharp4, Dflat4, C4, etc.)
    normalized = name.replace("#", "sharp").replace("♯", "sharp").replace("♭", "flat")
    if normalized in _ALL_PITCHES:
        return _ALL_PITCHES[normalized]

    # Parse letter + accidental + octave
    s = name.strip()
    # Find where the octave number starts (possibly negative for octave -1)
    i = len(s) - 1
    while i > 0 and (s[i].isdigit() or (s[i] == "-" and i > 0)):
        i -= 1
    i += 1

    note_part = s[:i].lower().replace("#", "sharp").replace("♯", "sharp").replace("♭", "flat")
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
