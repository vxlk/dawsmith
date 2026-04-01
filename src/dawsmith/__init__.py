"""DAWsmith -- programmatic music production engine."""

__version__ = "0.1.0"

try:
    from dawsmith._native import (
        create_engine,
        Engine,
        Edit,
        Track,
        MidiClip,
        Plugin,
        PluginDescription,
        RenderOptions,
        EngineDestroyedError,
        ObjectDeletedError,
    )

    def _add_notes(self, notes):
        """Add multiple notes to this clip.

        Args:
            notes: Iterable of ``(pitch, start_beat, length_beats)`` or
                ``(pitch, start_beat, length_beats, velocity)`` tuples.
                Each element can be a raw number or a Pitch/Duration/Velocity
                object.

        Example (musician-friendly)::

            from dawsmith.pitch import C4, E4, G4
            clip.add_notes([
                (C4,  0.0, QUARTER, mf),
                (E4,  1.0, QUARTER, mf),
                (G4,  2.0, HALF,    f),
            ])

        Example (programmer-friendly)::

            clip.add_notes([
                (60, 0.0, 1.0, 100),
                (64, 1.0, 1.0, 90),
                (67, 2.0, 2.0, 110),
            ])
        """
        for note_data in notes:
            if len(note_data) == 3:
                pitch, start, length = note_data
                self.add_note(int(pitch), float(start), float(length))
            elif len(note_data) == 4:
                pitch, start, length, vel = note_data
                self.add_note(
                    int(pitch), float(start), float(length), velocity=int(vel)
                )
            else:
                raise ValueError(
                    f"Each note must be (pitch, start, length) or "
                    f"(pitch, start, length, velocity), got {len(note_data)} elements"
                )

    MidiClip.add_notes = _add_notes

except ImportError as e:
    import warnings
    warnings.warn(
        f"Native module not found: {e}. "
        "Build with 'pip install -e .' to compile C++ bindings.",
        ImportWarning,
        stacklevel=2,
    )

# Musical constants -- always available even without native module
from dawsmith.pitch import Pitch, Interval, note  # noqa: E402
from dawsmith.pitch import (  # noqa: E402
    UNISON,
    MINOR_SECOND,
    MAJOR_SECOND,
    MINOR_THIRD,
    MAJOR_THIRD,
    PERFECT_FOURTH,
    TRITONE,
    PERFECT_FIFTH,
    MINOR_SIXTH,
    MAJOR_SIXTH,
    MINOR_SEVENTH,
    MAJOR_SEVENTH,
    OCTAVE,
)
from dawsmith.duration import (  # noqa: E402
    Duration,
    WHOLE,
    HALF,
    QUARTER,
    EIGHTH,
    SIXTEENTH,
    THIRTY_SECOND,
)
from dawsmith.velocity import (  # noqa: E402
    Velocity,
    ppp,
    pp,
    p,
    mp,
    mf,
    f,
    ff,
    fff,
)
from dawsmith.chord import (  # noqa: E402
    Chord,
    ChordShape,
    ScaleDegree,
    progression,
    MAJOR,
    MINOR,
    DIM,
    AUG,
    MAJ7,
    MIN7,
    DOM7,
    DIM7,
    HALF_DIM7,
    SUS2,
    SUS4,
    ADD9,
    MIN_MAJ7,
    MAJ9,
    MIN9,
    DOM9,
    I,
    ii,
    iii,
    IV,
    V,
    vi,
    vii,
    I7,
    ii7,
    iii7,
    IV7,
    V7,
    vi7,
    vii7,
)
from dawsmith.harmony import (  # noqa: E402
    scale,
    MAJOR_SCALE,
    MINOR_SCALE,
    HARMONIC_MINOR,
    MELODIC_MINOR,
    DORIAN,
    PHRYGIAN,
    LYDIAN,
    MIXOLYDIAN,
    LOCRIAN,
    PENTATONIC,
    MINOR_PENTATONIC,
    BLUES,
    CHROMATIC,
    WHOLE_TONE,
)

__all__ = [
    # Native engine
    "create_engine",
    "Engine",
    "Edit",
    "Track",
    "MidiClip",
    "Plugin",
    "PluginDescription",
    "RenderOptions",
    "EngineDestroyedError",
    "ObjectDeletedError",
    # Pitch (classes + intervals only; named pitches in dawsmith.pitch)
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
    # Duration
    "Duration",
    "WHOLE",
    "HALF",
    "QUARTER",
    "EIGHTH",
    "SIXTEENTH",
    "THIRTY_SECOND",
    # Velocity
    "Velocity",
    "ppp",
    "pp",
    "p",
    "mp",
    "mf",
    "f",
    "ff",
    "fff",
    # Chord
    "Chord",
    "ChordShape",
    "ScaleDegree",
    "progression",
    "MAJOR",
    "MINOR",
    "DIM",
    "AUG",
    "MAJ7",
    "MIN7",
    "DOM7",
    "DIM7",
    "HALF_DIM7",
    "SUS2",
    "SUS4",
    "ADD9",
    "MIN_MAJ7",
    "MAJ9",
    "MIN9",
    "DOM9",
    "I",
    "ii",
    "iii",
    "IV",
    "V",
    "vi",
    "vii",
    "I7",
    "ii7",
    "iii7",
    "IV7",
    "V7",
    "vi7",
    "vii7",
    # Scales
    "scale",
    "MAJOR_SCALE",
    "MINOR_SCALE",
    "HARMONIC_MINOR",
    "MELODIC_MINOR",
    "DORIAN",
    "PHRYGIAN",
    "LYDIAN",
    "MIXOLYDIAN",
    "LOCRIAN",
    "PENTATONIC",
    "MINOR_PENTATONIC",
    "BLUES",
    "CHROMATIC",
    "WHOLE_TONE",
]
