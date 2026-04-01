"""Chord classes and constants for musical composition.

Chords are first-class objects that support inversions, voicings,
transposition, and scale-degree-based progressions.

Usage::

    from dawsmith.pitch import C4
    from dawsmith.chord import Chord, MAJOR, MAJ7, progression, I, IV, V
    from dawsmith.harmony import MAJOR_SCALE
    from dawsmith import QUARTER, mf

    # Build and voice a chord
    c = Chord(C4, MAJOR)
    c.pitches              # (Pitch(60), Pitch(64), Pitch(67))
    c.invert(1)            # first inversion
    c.transpose(7)         # transpose up a perfect fifth

    # Output for clip.add_notes()
    clip.add_notes(c.to_notes(start_beat=0.0, length=QUARTER, velocity=mf))

    # Progressions from scale degrees
    chords = progression(C4, MAJOR_SCALE, I, IV, V, I)
"""

from dawsmith.pitch import Pitch


# ---------------------------------------------------------------------------
# ChordShape
# ---------------------------------------------------------------------------

class ChordShape:
    """A chord quality defined as semitone offsets from a root.

    Iterable and indexable, so it works anywhere a list of intervals did.
    """

    __slots__ = ("_intervals", "_name")

    def __init__(self, intervals, name=None):
        self._intervals = tuple(int(i) for i in intervals)
        self._name = name

    def __repr__(self):
        return self._name or f"ChordShape({list(self._intervals)})"

    def __iter__(self):
        return iter(self._intervals)

    def __len__(self):
        return len(self._intervals)

    def __getitem__(self, index):
        return self._intervals[index]

    def __eq__(self, other):
        if isinstance(other, ChordShape):
            return self._intervals == other._intervals
        try:
            return self._intervals == tuple(int(i) for i in other)
        except (TypeError, ValueError):
            return NotImplemented

    def __hash__(self):
        return hash(self._intervals)

    @property
    def intervals(self):
        return self._intervals

    @property
    def name(self):
        return self._name


# --- Chord shape constants ---

MAJOR     = ChordShape([0, 4, 7], "MAJOR")
MINOR     = ChordShape([0, 3, 7], "MINOR")
DIM       = ChordShape([0, 3, 6], "DIM")
AUG       = ChordShape([0, 4, 8], "AUG")
MAJ7      = ChordShape([0, 4, 7, 11], "MAJ7")
MIN7      = ChordShape([0, 3, 7, 10], "MIN7")
DOM7      = ChordShape([0, 4, 7, 10], "DOM7")
DIM7      = ChordShape([0, 3, 6, 9], "DIM7")
HALF_DIM7 = ChordShape([0, 3, 6, 10], "HALF_DIM7")
SUS2      = ChordShape([0, 2, 7], "SUS2")
SUS4      = ChordShape([0, 5, 7], "SUS4")
ADD9      = ChordShape([0, 4, 7, 14], "ADD9")
MIN_MAJ7  = ChordShape([0, 3, 7, 11], "MIN_MAJ7")
MAJ9      = ChordShape([0, 4, 7, 11, 14], "MAJ9")
MIN9      = ChordShape([0, 3, 7, 10, 14], "MIN9")
DOM9      = ChordShape([0, 4, 7, 10, 14], "DOM9")


# ---------------------------------------------------------------------------
# Chord
# ---------------------------------------------------------------------------

class Chord:
    """An immutable chord rooted on a specific pitch.

    All voicing methods return a new ``Chord``; the original is unchanged.
    """

    __slots__ = ("_pitches", "_root", "_shape")

    def __init__(self, root, shape):
        root = root if isinstance(root, Pitch) else Pitch(int(root))
        shape = shape if isinstance(shape, ChordShape) else ChordShape(shape)
        self._root = root
        self._shape = shape
        self._pitches = tuple(Pitch(int(root) + iv) for iv in shape)

    @classmethod
    def from_pitches(cls, pitches, root=None, shape=None):
        """Construct a Chord from explicit pitches.

        Pitches are sorted low-to-high.  If *root* is omitted the lowest
        pitch is used.
        """
        obj = object.__new__(cls)
        obj._pitches = tuple(
            Pitch(int(p)) for p in sorted(pitches, key=lambda p: int(p))
        )
        obj._root = root if root is not None else obj._pitches[0]
        obj._shape = shape
        return obj

    # --- properties ---

    @property
    def pitches(self):
        """Tuple of Pitch objects, lowest to highest."""
        return self._pitches

    @property
    def root(self):
        """The original root pitch."""
        return self._root

    @property
    def shape(self):
        """The ChordShape, if known."""
        return self._shape

    @property
    def bass(self):
        """The lowest sounding pitch (differs from root in inversions)."""
        return self._pitches[0]

    # --- voicing methods ---

    def invert(self, n=1):
        """Return a new Chord with the bottom *n* notes raised an octave.

        For a triad, ``invert(1)`` is first inversion, ``invert(2)`` is
        second inversion.
        """
        if not 0 < n < len(self._pitches):
            raise ValueError(
                f"Inversion must be 1-{len(self._pitches) - 1} for a "
                f"{len(self._pitches)}-note chord, got {n}"
            )
        pitches = list(self._pitches)
        for _ in range(n):
            moved = Pitch(int(pitches[0]) + 12)
            pitches = pitches[1:] + [moved]
        return Chord.from_pitches(pitches, root=self._root, shape=self._shape)

    def transpose(self, interval):
        """Return a new Chord shifted by *interval* semitones."""
        semitones = int(interval)
        new_pitches = [Pitch(int(p) + semitones) for p in self._pitches]
        new_root = Pitch(int(self._root) + semitones)
        return Chord.from_pitches(
            new_pitches, root=new_root, shape=self._shape
        )

    def drop2(self):
        """Drop-2 voicing: lower the 2nd-from-top note by an octave.

        Requires at least 4 notes.
        """
        if len(self._pitches) < 4:
            raise ValueError("Drop-2 voicing requires at least 4 notes")
        pitches = list(self._pitches)
        pitches[-2] = Pitch(int(pitches[-2]) - 12)
        return Chord.from_pitches(
            pitches, root=self._root, shape=self._shape
        )

    def drop3(self):
        """Drop-3 voicing: lower the 3rd-from-top note by an octave.

        Requires at least 4 notes.
        """
        if len(self._pitches) < 4:
            raise ValueError("Drop-3 voicing requires at least 4 notes")
        pitches = list(self._pitches)
        pitches[-3] = Pitch(int(pitches[-3]) - 12)
        return Chord.from_pitches(
            pitches, root=self._root, shape=self._shape
        )

    def open_voicing(self):
        """Spread voicing: raise every other note by an octave."""
        pitches = list(self._pitches)
        opened = []
        for i, p in enumerate(pitches):
            if i % 2 == 1:
                opened.append(Pitch(int(p) + 12))
            else:
                opened.append(p)
        return Chord.from_pitches(
            opened, root=self._root, shape=self._shape
        )

    def close_voicing(self):
        """Compress all notes within one octave of the bass."""
        bass_midi = int(self._pitches[0])
        closed = [self._pitches[0]]
        for p in self._pitches[1:]:
            relative = (int(p) - bass_midi) % 12
            if relative == 0:
                relative = 12  # avoid unison with bass
            closed.append(Pitch(bass_midi + relative))
        return Chord.from_pitches(
            closed, root=self._root, shape=self._shape
        )

    # --- output ---

    def to_notes(self, start_beat, length, velocity=None):
        """Generate note tuples for ``clip.add_notes()``.

        Returns:
            List of ``(pitch, start_beat, length, velocity)`` tuples.
        """
        vel = int(velocity) if velocity is not None else 100
        sb = float(start_beat)
        ln = float(length)
        return [(int(p), sb, ln, vel) for p in self._pitches]

    # --- dunders ---

    def __repr__(self):
        if self._shape and self._shape.name:
            return f"Chord({self._root!r}, {self._shape.name})"
        return f"Chord({list(int(p) for p in self._pitches)})"

    def __eq__(self, other):
        if isinstance(other, Chord):
            return self._pitches == other._pitches
        return NotImplemented

    def __hash__(self):
        return hash(self._pitches)

    def __len__(self):
        return len(self._pitches)

    def __iter__(self):
        return iter(self._pitches)

    def __contains__(self, pitch):
        midi = int(pitch)
        return any(int(p) == midi for p in self._pitches)


# ---------------------------------------------------------------------------
# ScaleDegree + progression
# ---------------------------------------------------------------------------

class ScaleDegree:
    """A scale degree with an associated chord quality.

    Used with :func:`progression` to build chord sequences from Roman
    numeral constants like ``I``, ``iv``, ``V7``.
    """

    __slots__ = ("_degree", "_shape", "_name")

    def __init__(self, degree, shape, name=None):
        self._degree = int(degree)
        self._shape = shape if isinstance(shape, ChordShape) else ChordShape(shape)
        self._name = name

    @property
    def degree(self):
        """0-based index into the scale pattern."""
        return self._degree

    @property
    def shape(self):
        """The ChordShape built on this degree."""
        return self._shape

    def __repr__(self):
        return self._name or f"ScaleDegree({self._degree}, {self._shape!r})"

    def __eq__(self, other):
        if isinstance(other, ScaleDegree):
            return self._degree == other._degree and self._shape == other._shape
        return NotImplemented

    def __hash__(self):
        return hash((self._degree, self._shape))


# --- Diatonic triad degrees (major key) ---

I   = ScaleDegree(0, MAJOR, "I")
ii  = ScaleDegree(1, MINOR, "ii")
iii = ScaleDegree(2, MINOR, "iii")
IV  = ScaleDegree(3, MAJOR, "IV")
V   = ScaleDegree(4, MAJOR, "V")
vi  = ScaleDegree(5, MINOR, "vi")
vii = ScaleDegree(6, DIM, "vii")

# --- Diatonic seventh degrees (major key) ---

I7   = ScaleDegree(0, MAJ7, "I7")
ii7  = ScaleDegree(1, MIN7, "ii7")
iii7 = ScaleDegree(2, MIN7, "iii7")
IV7  = ScaleDegree(3, MAJ7, "IV7")
V7   = ScaleDegree(4, DOM7, "V7")
vi7  = ScaleDegree(5, MIN7, "vi7")
vii7 = ScaleDegree(6, HALF_DIM7, "vii7")


def progression(root, scale_pattern, *degrees):
    """Build a list of Chords from scale degrees.

    Args:
        root: Root pitch of the key (Pitch or int).
        scale_pattern: Scale intervals list (e.g. ``MAJOR_SCALE``).
        *degrees: :class:`ScaleDegree` constants (``I``, ``IV``, ``V``, etc.).

    Returns:
        List of :class:`Chord` objects.

    Example::

        from dawsmith.pitch import C4
        from dawsmith.harmony import MAJOR_SCALE
        from dawsmith.chord import progression, I, IV, V

        chords = progression(C4, MAJOR_SCALE, I, IV, V, I)
    """
    root_midi = int(root)
    chords = []
    for deg in degrees:
        if deg.degree >= len(scale_pattern):
            raise ValueError(
                f"Scale degree {deg.degree} out of range for "
                f"{len(scale_pattern)}-note scale"
            )
        offset = scale_pattern[deg.degree]
        chord_root = Pitch(root_midi + offset)
        chords.append(Chord(chord_root, deg.shape))
    return chords


# ---------------------------------------------------------------------------
# __all__
# ---------------------------------------------------------------------------

__all__ = [
    "ChordShape",
    "Chord",
    "ScaleDegree",
    "progression",
    # Chord shapes
    "MAJOR", "MINOR", "DIM", "AUG",
    "MAJ7", "MIN7", "DOM7", "DIM7", "HALF_DIM7",
    "SUS2", "SUS4", "ADD9", "MIN_MAJ7",
    "MAJ9", "MIN9", "DOM9",
    # Scale degrees (diatonic triads)
    "I", "ii", "iii", "IV", "V", "vi", "vii",
    # Scale degrees (diatonic sevenths)
    "I7", "ii7", "iii7", "IV7", "V7", "vi7", "vii7",
]
