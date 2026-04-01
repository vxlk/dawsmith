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

from dawsmith.pitch import Pitch


# --- Scale patterns (semitone offsets from root) ---

MAJOR_SCALE = [0, 2, 4, 5, 7, 9, 11]
MINOR_SCALE = [0, 2, 3, 5, 7, 8, 10]
HARMONIC_MINOR = [0, 2, 3, 5, 7, 8, 11]
MELODIC_MINOR = [0, 2, 3, 5, 7, 9, 11]
DORIAN = [0, 2, 3, 5, 7, 9, 10]
PHRYGIAN = [0, 1, 3, 5, 7, 8, 10]
LYDIAN = [0, 2, 4, 6, 7, 9, 11]
MIXOLYDIAN = [0, 2, 4, 5, 7, 9, 10]
LOCRIAN = [0, 1, 3, 5, 6, 8, 10]
PENTATONIC = [0, 2, 4, 7, 9]
MINOR_PENTATONIC = [0, 3, 5, 7, 10]
BLUES = [0, 3, 5, 6, 7, 10]
CHROMATIC = list(range(12))
WHOLE_TONE = [0, 2, 4, 6, 8, 10]


def scale(root, pattern, octaves=1):
    """Generate a list of Pitch objects for a scale.

    Args:
        root: Root pitch (Pitch or int MIDI number).
        pattern: Scale intervals (e.g. ``MAJOR_SCALE``, ``PENTATONIC``).
        octaves: Number of octaves to span (default 1).

    Returns:
        List of Pitch objects. Includes the root of the next octave at the end.

    Example::

        for i, pitch in enumerate(scale(C4, MAJOR_SCALE)):
            clip.add_note(pitch, float(i) * 0.5, 0.5)
    """
    root_midi = int(root)
    pitches = []
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
