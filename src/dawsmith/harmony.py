"""Scale helpers and patterns for musical composition.

For chord shapes and the Chord class, see :mod:`dawsmith.chord`.

Usage::

    from dawsmith.pitch import C4, A3
    from dawsmith.chord import Chord, MAJOR
    from dawsmith.harmony import scale, MAJOR_SCALE, MINOR_PENTATONIC
    from dawsmith import QUARTER, mf

    # Build a C major chord
    c = Chord(C4, MAJOR)
    clip.add_notes(c.to_notes(start_beat=0.0, length=QUARTER, velocity=mf))

    # Generate an A minor pentatonic scale
    for i, pitch in enumerate(scale(A3, MINOR_PENTATONIC)):
        clip.add_note(pitch, float(i), 0.5)
"""

from __future__ import annotations

from collections.abc import Sequence

from dawsmith.pitch import Pitch


# --- Scale patterns (semitone offsets from root) ---

MAJOR_SCALE: list[int] = [0, 2, 4, 5, 7, 9, 11]
MINOR_SCALE: list[int] = [0, 2, 3, 5, 7, 8, 10]
HARMONIC_MINOR: list[int] = [0, 2, 3, 5, 7, 8, 11]
MELODIC_MINOR: list[int] = [0, 2, 3, 5, 7, 9, 11]
DORIAN: list[int] = [0, 2, 3, 5, 7, 9, 10]
PHRYGIAN: list[int] = [0, 1, 3, 5, 7, 8, 10]
LYDIAN: list[int] = [0, 2, 4, 6, 7, 9, 11]
MIXOLYDIAN: list[int] = [0, 2, 4, 5, 7, 9, 10]
LOCRIAN: list[int] = [0, 1, 3, 5, 6, 8, 10]
PENTATONIC: list[int] = [0, 2, 4, 7, 9]
MINOR_PENTATONIC: list[int] = [0, 3, 5, 7, 10]
BLUES: list[int] = [0, 3, 5, 6, 7, 10]
CHROMATIC: list[int] = list(range(12))
WHOLE_TONE: list[int] = [0, 2, 4, 6, 8, 10]


def scale(
    root: Pitch | int,
    pattern: Sequence[int],
    octaves: int = 1,
) -> list[Pitch]:
    """Generate a list of Pitch objects for a scale.

    Args:
        root: Root pitch (``Pitch`` or raw MIDI number).
        pattern: Scale intervals as semitone offsets from root
            (e.g. ``MAJOR_SCALE``, ``PENTATONIC``).
        octaves: Number of octaves to span (default 1).

    Returns:
        Pitch objects from root through the final octave's root.
        Out-of-range MIDI notes (< 0 or > 127) are silently omitted.

    Example::

        for i, pitch in enumerate(scale(C4, MAJOR_SCALE)):
            clip.add_note(pitch, float(i) * 0.5, 0.5)
    """
    root_midi = int(root)
    pitches: list[Pitch] = []
    for oct in range(octaves):
        for interval in pattern:
            midi = root_midi + oct * 12 + interval
            if 0 <= midi <= 127:
                pitches.append(Pitch(midi))
    # Add the octave note at the end
    final = root_midi + octaves * 12
    if 0 <= final <= 127:
        pitches.append(Pitch(final))
    return pitches


__all__ = [
    "scale",
    # Scale patterns
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
