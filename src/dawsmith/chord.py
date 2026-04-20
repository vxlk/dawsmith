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

from __future__ import annotations

from collections.abc import Iterable, Sequence

from dawsmith.pitch import Pitch


# ---------------------------------------------------------------------------
# ChordShape
# ---------------------------------------------------------------------------

class ChordShape:
    """A chord quality defined as semitone offsets from a root.

    Iterable and indexable, so it works anywhere a list of intervals did.

    Args:
        intervals: Semitone offsets from root (e.g. ``[0, 4, 7]`` for major).
        name: Optional display name (e.g. ``"MAJOR"``).
    """

    __slots__ = ("_intervals", "_name")

    def __init__(self, intervals: Iterable[int], name: str | None = None) -> None:
        self._intervals = tuple(int(i) for i in intervals)
        self._name = name

    def __repr__(self) -> str:
        return self._name or f"ChordShape({list(self._intervals)})"

    def __iter__(self):  # type: ignore[override]
        return iter(self._intervals)

    def __len__(self) -> int:
        return len(self._intervals)

    def __getitem__(self, index: int) -> int:
        return self._intervals[index]

    def __eq__(self, other: object) -> bool:
        if isinstance(other, ChordShape):
            return self._intervals == other._intervals
        try:
            return self._intervals == tuple(int(i) for i in other)  # type: ignore[union-attr]
        except (TypeError, ValueError):
            return NotImplemented  # type: ignore[return-value]

    def __hash__(self) -> int:
        return hash(self._intervals)

    @property
    def intervals(self) -> tuple[int, ...]:
        """Semitone offsets as an immutable tuple."""
        return self._intervals

    @property
    def name(self) -> str | None:
        """Display name, or ``None`` for unnamed shapes."""
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

    Args:
        root: Root pitch (``Pitch`` or raw MIDI number).
        shape: Chord quality (``ChordShape`` or iterable of semitone offsets).
    """

    __slots__ = ("_pitches", "_root", "_shape")

    def __init__(self, root: Pitch | int, shape: ChordShape | Iterable[int]) -> None:
        root = root if isinstance(root, Pitch) else Pitch(int(root))
        shape = shape if isinstance(shape, ChordShape) else ChordShape(shape)
        self._root = root
        self._shape = shape
        self._pitches = tuple(Pitch(int(root) + iv) for iv in shape)

    @classmethod
    def from_pitches(
        cls,
        pitches: Iterable[Pitch | int],
        root: Pitch | None = None,
        shape: ChordShape | None = None,
    ) -> Chord:
        """Construct a Chord from explicit pitches.

        Pitches are sorted low-to-high.  If *root* is omitted the lowest
        pitch is used.

        Args:
            pitches: Pitch objects or MIDI numbers.
            root: Override root pitch (default: lowest pitch).
            shape: Optional ``ChordShape`` to associate with the chord.

        Returns:
            A new ``Chord`` with the given pitches.
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
    def pitches(self) -> tuple[Pitch, ...]:
        """Tuple of Pitch objects, lowest to highest."""
        return self._pitches

    @property
    def root(self) -> Pitch:
        """The original root pitch."""
        return self._root

    @property
    def shape(self) -> ChordShape | None:
        """The ``ChordShape``, if known."""
        return self._shape

    @property
    def bass(self) -> Pitch:
        """The lowest sounding pitch (differs from root in inversions)."""
        return self._pitches[0]

    # --- voicing methods ---

    def invert(self, n: int = 1) -> Chord:
        """Return a new Chord with the bottom *n* notes raised an octave.

        For a triad, ``invert(1)`` is first inversion, ``invert(2)`` is
        second inversion.

        Args:
            n: Number of notes to raise (1-based, must be less than
                the number of chord tones).

        Returns:
            A new ``Chord`` in the requested inversion.

        Raises:
            ValueError: If *n* is out of range for this chord.
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

    def transpose(self, interval: int) -> Chord:
        """Return a new Chord shifted by *interval* semitones.

        Args:
            interval: Semitones to shift (positive = up, negative = down).
                Accepts ``Interval`` objects via ``int()`` conversion.

        Returns:
            A new ``Chord`` at the transposed pitch.
        """
        semitones = int(interval)
        new_pitches = [Pitch(int(p) + semitones) for p in self._pitches]
        new_root = Pitch(int(self._root) + semitones)
        return Chord.from_pitches(
            new_pitches, root=new_root, shape=self._shape
        )

    def drop2(self) -> Chord:
        """Drop-2 voicing: lower the 2nd-from-top note by an octave.

        Returns:
            A new ``Chord`` with drop-2 voicing applied.

        Raises:
            ValueError: If the chord has fewer than 4 notes.
        """
        if len(self._pitches) < 4:
            raise ValueError("Drop-2 voicing requires at least 4 notes")
        pitches = list(self._pitches)
        pitches[-2] = Pitch(int(pitches[-2]) - 12)
        return Chord.from_pitches(
            pitches, root=self._root, shape=self._shape
        )

    def drop3(self) -> Chord:
        """Drop-3 voicing: lower the 3rd-from-top note by an octave.

        Returns:
            A new ``Chord`` with drop-3 voicing applied.

        Raises:
            ValueError: If the chord has fewer than 4 notes.
        """
        if len(self._pitches) < 4:
            raise ValueError("Drop-3 voicing requires at least 4 notes")
        pitches = list(self._pitches)
        pitches[-3] = Pitch(int(pitches[-3]) - 12)
        return Chord.from_pitches(
            pitches, root=self._root, shape=self._shape
        )

    def open_voicing(self) -> Chord:
        """Spread voicing: raise every other note by an octave.

        Returns:
            A new ``Chord`` with wider spacing between voices.
        """
        pitches = list(self._pitches)
        opened: list[Pitch] = []
        for i, p in enumerate(pitches):
            if i % 2 == 1:
                opened.append(Pitch(int(p) + 12))
            else:
                opened.append(p)
        return Chord.from_pitches(
            opened, root=self._root, shape=self._shape
        )

    def close_voicing(self) -> Chord:
        """Compress all notes within one octave of the bass.

        Returns:
            A new ``Chord`` in close position.
        """
        bass_midi = int(self._pitches[0])
        closed: list[Pitch] = [self._pitches[0]]
        for p in self._pitches[1:]:
            relative = (int(p) - bass_midi) % 12
            if relative == 0:
                relative = 12  # avoid unison with bass
            closed.append(Pitch(bass_midi + relative))
        return Chord.from_pitches(
            closed, root=self._root, shape=self._shape
        )

    # --- output ---

    def to_notes(
        self,
        start_beat: float,
        length: float,
        velocity: int | None = None,
    ) -> list[tuple[int, float, float, int]]:
        """Generate note tuples for ``clip.add_notes()``.

        ``Duration`` and ``Velocity`` objects are also accepted for
        *start_beat*, *length*, and *velocity* respectively (converted
        via ``float()`` / ``int()``).

        Args:
            start_beat: Start position in beats.
            length: Note duration in beats.
            velocity: MIDI velocity 0-127 (default 100).

        Returns:
            List of ``(pitch, start_beat, length, velocity)`` tuples.
        """
        vel = int(velocity) if velocity is not None else 100
        sb = float(start_beat)
        ln = float(length)
        return [(int(p), sb, ln, vel) for p in self._pitches]

    # --- dunders ---

    def __repr__(self) -> str:
        if self._shape and self._shape.name:
            return f"Chord({self._root!r}, {self._shape.name})"
        return f"Chord({list(int(p) for p in self._pitches)})"

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Chord):
            return self._pitches == other._pitches
        return NotImplemented  # type: ignore[return-value]

    def __hash__(self) -> int:
        return hash(self._pitches)

    def __len__(self) -> int:
        return len(self._pitches)

    def __iter__(self):  # type: ignore[override]
        return iter(self._pitches)

    def __contains__(self, pitch: Pitch | int) -> bool:
        midi = int(pitch)
        return any(int(p) == midi for p in self._pitches)


# ---------------------------------------------------------------------------
# ScaleDegree + progression
# ---------------------------------------------------------------------------

class ScaleDegree:
    """A scale degree with an associated chord quality.

    Used with :func:`progression` to build chord sequences from Roman
    numeral constants like ``I``, ``iv``, ``V7``.

    Args:
        degree: 0-based index into the scale pattern.
        shape: Chord quality (``ChordShape`` or iterable of semitone offsets).
        name: Optional Roman-numeral name (e.g. ``"V7"``).
    """

    __slots__ = ("_degree", "_shape", "_name")

    def __init__(
        self,
        degree: int,
        shape: ChordShape | Iterable[int],
        name: str | None = None,
    ) -> None:
        self._degree = int(degree)
        self._shape = shape if isinstance(shape, ChordShape) else ChordShape(shape)
        self._name = name

    @property
    def degree(self) -> int:
        """0-based index into the scale pattern."""
        return self._degree

    @property
    def shape(self) -> ChordShape:
        """The ``ChordShape`` built on this degree."""
        return self._shape

    def __repr__(self) -> str:
        return self._name or f"ScaleDegree({self._degree}, {self._shape!r})"

    def __eq__(self, other: object) -> bool:
        if isinstance(other, ScaleDegree):
            return self._degree == other._degree and self._shape == other._shape
        return NotImplemented  # type: ignore[return-value]

    def __hash__(self) -> int:
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


def progression(
    root: Pitch | int,
    scale_pattern: Sequence[int],
    *degrees: ScaleDegree,
) -> list[Chord]:
    """Build a list of Chords from scale degrees.

    Args:
        root: Root pitch of the key (``Pitch`` or raw MIDI number).
        scale_pattern: Scale intervals list (e.g. ``MAJOR_SCALE``).
        *degrees: ``ScaleDegree`` constants (``I``, ``IV``, ``V``, etc.).

    Returns:
        List of ``Chord`` objects, one per degree.

    Raises:
        ValueError: If a degree index exceeds the scale length.

    Example::

        from dawsmith.pitch import C4
        from dawsmith.harmony import MAJOR_SCALE
        from dawsmith.chord import progression, I, IV, V

        chords = progression(C4, MAJOR_SCALE, I, IV, V, I)
    """
    root_midi = int(root)
    chords: list[Chord] = []
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
