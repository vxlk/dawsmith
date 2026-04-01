"""Tests for dawsmith.chord -- ChordShape, Chord, ScaleDegree, progression."""

import pytest
from dawsmith.pitch import C4, E4, G4, A3, Pitch, PERFECT_FIFTH, OCTAVE
from dawsmith.chord import (
    ChordShape,
    Chord,
    ScaleDegree,
    progression,
    MAJOR,
    MINOR,
    DIM,
    AUG,
    MAJ7,
    MIN7,
    DOM7,
    HALF_DIM7,
    SUS2,
    SUS4,
    I,
    ii,
    iii,
    IV,
    V,
    vi,
    vii,
    I7,
    V7,
)
from dawsmith.harmony import MAJOR_SCALE, MINOR_SCALE
from dawsmith.velocity import mf
from dawsmith.duration import QUARTER, WHOLE


# ---------------------------------------------------------------------------
# ChordShape
# ---------------------------------------------------------------------------

class TestChordShape:
    def test_creation_and_iteration(self):
        shape = ChordShape([0, 4, 7])
        assert list(shape) == [0, 4, 7]

    def test_repr_named(self):
        assert repr(MAJOR) == "MAJOR"

    def test_repr_unnamed(self):
        shape = ChordShape([0, 4, 7])
        assert repr(shape) == "ChordShape([0, 4, 7])"

    def test_equality_with_list(self):
        assert MAJOR == [0, 4, 7]

    def test_equality_between_shapes(self):
        assert MAJOR == ChordShape([0, 4, 7])
        assert MAJOR != MINOR

    def test_hash(self):
        assert hash(MAJOR) == hash(ChordShape([0, 4, 7]))
        s = {MAJOR, ChordShape([0, 4, 7])}
        assert len(s) == 1

    def test_len(self):
        assert len(MAJOR) == 3
        assert len(MAJ7) == 4

    def test_getitem(self):
        assert MAJOR[0] == 0
        assert MAJOR[1] == 4
        assert MAJOR[2] == 7

    def test_intervals_property(self):
        assert MAJOR.intervals == (0, 4, 7)

    def test_name_property(self):
        assert MAJOR.name == "MAJOR"
        assert ChordShape([0, 4, 7]).name is None


# ---------------------------------------------------------------------------
# Chord — construction
# ---------------------------------------------------------------------------

class TestChord:
    def test_major_chord_pitches(self):
        c = Chord(C4, MAJOR)
        assert [int(p) for p in c.pitches] == [60, 64, 67]

    def test_minor_chord_pitches(self):
        c = Chord(A3, MINOR)
        assert [int(p) for p in c.pitches] == [57, 60, 64]

    def test_seventh_chord_pitches(self):
        c = Chord(C4, MAJ7)
        assert [int(p) for p in c.pitches] == [60, 64, 67, 71]

    def test_from_pitches(self):
        c = Chord.from_pitches([G4, C4, E4])
        assert [int(p) for p in c.pitches] == [60, 64, 67]

    def test_with_raw_int_root(self):
        c = Chord(60, MAJOR)
        assert [int(p) for p in c.pitches] == [60, 64, 67]

    def test_with_list_intervals(self):
        c = Chord(C4, [0, 4, 7])
        assert [int(p) for p in c.pitches] == [60, 64, 67]

    def test_root_property(self):
        c = Chord(C4, MAJOR)
        assert int(c.root) == 60

    def test_shape_property(self):
        c = Chord(C4, MAJOR)
        assert c.shape == MAJOR

    def test_bass_property(self):
        c = Chord(C4, MAJOR)
        assert int(c.bass) == 60

    def test_bass_differs_from_root_in_inversion(self):
        c = Chord(C4, MAJOR).invert(1)
        assert int(c.root) == 60  # root stays C4
        assert int(c.bass) == 64  # bass is E4

    def test_repr_with_named_shape(self):
        c = Chord(C4, MAJOR)
        assert repr(c) == "Chord(C4, MAJOR)"

    def test_repr_from_pitches(self):
        c = Chord.from_pitches([C4, E4, G4])
        assert "Chord(" in repr(c)

    def test_equality(self):
        assert Chord(C4, MAJOR) == Chord(C4, MAJOR)

    def test_inequality(self):
        assert Chord(C4, MAJOR) != Chord(C4, MINOR)

    def test_hash(self):
        s = {Chord(C4, MAJOR), Chord(C4, MAJOR)}
        assert len(s) == 1

    def test_len(self):
        assert len(Chord(C4, MAJOR)) == 3
        assert len(Chord(C4, MAJ7)) == 4

    def test_iter(self):
        pitches = list(Chord(C4, MAJOR))
        assert [int(p) for p in pitches] == [60, 64, 67]

    def test_contains(self):
        c = Chord(C4, MAJOR)
        assert C4 in c
        assert E4 in c
        assert G4 in c
        assert A3 not in c

    def test_contains_with_int(self):
        c = Chord(C4, MAJOR)
        assert 60 in c
        assert 61 not in c


# ---------------------------------------------------------------------------
# Inversions
# ---------------------------------------------------------------------------

class TestInversion:
    def test_invert_1_triad(self):
        c = Chord(C4, MAJOR).invert(1)
        assert [int(p) for p in c.pitches] == [64, 67, 72]  # E4, G4, C5

    def test_invert_2_triad(self):
        c = Chord(C4, MAJOR).invert(2)
        assert [int(p) for p in c.pitches] == [67, 72, 76]  # G4, C5, E5

    def test_invert_1_seventh(self):
        c = Chord(C4, MAJ7).invert(1)
        assert [int(p) for p in c.pitches] == [64, 67, 71, 72]  # E4, G4, B4, C5

    def test_invert_2_seventh(self):
        c = Chord(C4, MAJ7).invert(2)
        assert [int(p) for p in c.pitches] == [67, 71, 72, 76]  # G4, B4, C5, E5

    def test_invert_3_seventh(self):
        c = Chord(C4, MAJ7).invert(3)
        assert [int(p) for p in c.pitches] == [71, 72, 76, 79]  # B4, C5, E5, G5

    def test_invert_returns_new_chord(self):
        c = Chord(C4, MAJOR)
        inv = c.invert(1)
        assert c is not inv
        assert [int(p) for p in c.pitches] == [60, 64, 67]  # original unchanged

    def test_invert_preserves_root(self):
        c = Chord(C4, MAJOR).invert(1)
        assert int(c.root) == 60

    def test_invert_0_raises(self):
        with pytest.raises(ValueError, match="Inversion must be"):
            Chord(C4, MAJOR).invert(0)

    def test_invert_too_high_raises(self):
        with pytest.raises(ValueError, match="Inversion must be"):
            Chord(C4, MAJOR).invert(3)  # triad only has inversions 1-2

    def test_invert_negative_raises(self):
        with pytest.raises(ValueError, match="Inversion must be"):
            Chord(C4, MAJOR).invert(-1)


# ---------------------------------------------------------------------------
# Transposition
# ---------------------------------------------------------------------------

class TestTranspose:
    def test_transpose_perfect_fifth(self):
        c = Chord(C4, MAJOR).transpose(PERFECT_FIFTH)
        assert [int(p) for p in c.pitches] == [67, 71, 74]  # G4, B4, D5

    def test_transpose_by_int(self):
        c = Chord(C4, MAJOR).transpose(7)
        assert [int(p) for p in c.pitches] == [67, 71, 74]

    def test_transpose_preserves_shape(self):
        c = Chord(C4, MAJOR).transpose(7)
        assert c.shape == MAJOR

    def test_transpose_returns_new_chord(self):
        c = Chord(C4, MAJOR)
        t = c.transpose(7)
        assert c is not t
        assert [int(p) for p in c.pitches] == [60, 64, 67]

    def test_transpose_updates_root(self):
        c = Chord(C4, MAJOR).transpose(7)
        assert int(c.root) == 67


# ---------------------------------------------------------------------------
# Drop voicings
# ---------------------------------------------------------------------------

class TestDropVoicing:
    def test_drop2_seventh(self):
        # Cmaj7 close: C4 E4 G4 B4 -> drop 2nd from top (G4) -> G3 C4 E4 B4
        c = Chord(C4, MAJ7).drop2()
        midi = [int(p) for p in c.pitches]
        assert midi == [55, 60, 64, 71]  # G3, C4, E4, B4

    def test_drop2_returns_sorted(self):
        c = Chord(C4, MAJ7).drop2()
        midi = [int(p) for p in c.pitches]
        assert midi == sorted(midi)

    def test_drop2_triad_raises(self):
        with pytest.raises(ValueError, match="at least 4 notes"):
            Chord(C4, MAJOR).drop2()

    def test_drop3_seventh(self):
        # Cmaj7 close: C4 E4 G4 B4 -> drop 3rd from top (E4) -> E3 C4 G4 B4
        c = Chord(C4, MAJ7).drop3()
        midi = [int(p) for p in c.pitches]
        assert midi == [52, 60, 67, 71]  # E3, C4, G4, B4

    def test_drop3_triad_raises(self):
        with pytest.raises(ValueError, match="at least 4 notes"):
            Chord(C4, MAJOR).drop3()


# ---------------------------------------------------------------------------
# Open / close voicing
# ---------------------------------------------------------------------------

class TestOpenCloseVoicing:
    def test_open_voicing_triad(self):
        # C4 E4 G4 -> odd index (E4) raised -> C4 G4 E5
        c = Chord(C4, MAJOR).open_voicing()
        midi = [int(p) for p in c.pitches]
        assert midi == [60, 67, 76]  # C4, G4, E5

    def test_open_voicing_seventh(self):
        # C4 E4 G4 B4 -> odd indices (E4, B4) raised -> C4 G4 E5 B5
        c = Chord(C4, MAJ7).open_voicing()
        midi = [int(p) for p in c.pitches]
        assert midi == [60, 67, 76, 83]

    def test_close_voicing(self):
        # Take an open voicing and close it back within one octave
        opened = Chord(C4, MAJOR).open_voicing()
        closed = opened.close_voicing()
        midi = [int(p) for p in closed.pitches]
        # All notes within 12 semitones of bass
        assert max(midi) - min(midi) < 12

    def test_close_voicing_already_close(self):
        c = Chord(C4, MAJOR)
        closed = c.close_voicing()
        midi = [int(p) for p in closed.pitches]
        assert max(midi) - min(midi) < 12


# ---------------------------------------------------------------------------
# to_notes
# ---------------------------------------------------------------------------

class TestToNotes:
    def test_format(self):
        notes = Chord(C4, MAJOR).to_notes(0.0, 1.0)
        assert len(notes) == 3
        for pitch, start, length, vel in notes:
            assert isinstance(pitch, int)
            assert start == 0.0
            assert length == 1.0

    def test_default_velocity(self):
        notes = Chord(C4, MAJOR).to_notes(0.0, 1.0)
        for _, _, _, vel in notes:
            assert vel == 100

    def test_with_velocity(self):
        notes = Chord(C4, MAJOR).to_notes(0.0, 1.0, velocity=mf)
        for _, _, _, vel in notes:
            assert vel == 80

    def test_with_duration_objects(self):
        notes = Chord(C4, MAJOR).to_notes(0.0, WHOLE, velocity=mf)
        for _, sb, ln, vel in notes:
            assert sb == 0.0
            assert ln == 4.0
            assert vel == 80

    def test_pitches_match(self):
        notes = Chord(C4, MAJOR).to_notes(0.0, 1.0)
        pitches = [n[0] for n in notes]
        assert pitches == [60, 64, 67]


# ---------------------------------------------------------------------------
# ScaleDegree
# ---------------------------------------------------------------------------

class TestScaleDegree:
    def test_degree_property(self):
        assert I.degree == 0
        assert V.degree == 4

    def test_shape_property(self):
        assert I.shape == MAJOR
        assert ii.shape == MINOR
        assert vii.shape == DIM

    def test_repr(self):
        assert repr(I) == "I"
        assert repr(ii) == "ii"
        assert repr(V7) == "V7"

    def test_equality(self):
        assert I == ScaleDegree(0, MAJOR)
        assert I != V

    def test_hash(self):
        s = {I, ScaleDegree(0, MAJOR)}
        assert len(s) == 1


# ---------------------------------------------------------------------------
# Progression
# ---------------------------------------------------------------------------

class TestProgression:
    def test_I_IV_V_I(self):
        chords = progression(C4, MAJOR_SCALE, I, IV, V, I)
        roots = [int(c.root) for c in chords]
        assert roots == [60, 65, 67, 60]  # C, F, G, C

    def test_chord_shapes(self):
        chords = progression(C4, MAJOR_SCALE, I, IV, V, I)
        shapes = [c.shape for c in chords]
        assert shapes == [MAJOR, MAJOR, MAJOR, MAJOR]

    def test_pop_progression(self):
        # I - vi - IV - V
        chords = progression(C4, MAJOR_SCALE, I, vi, IV, V)
        roots = [int(c.root) for c in chords]
        assert roots == [60, 69, 65, 67]  # C, A, F, G

    def test_pop_progression_shapes(self):
        chords = progression(C4, MAJOR_SCALE, I, vi, IV, V)
        assert chords[1].shape == MINOR  # vi is minor

    def test_with_seventh_degrees(self):
        chords = progression(C4, MAJOR_SCALE, I7, V7)
        assert chords[0].shape == MAJ7
        assert chords[1].shape == DOM7

    def test_minor_key(self):
        chords = progression(A3, MINOR_SCALE, I, IV, V)
        roots = [int(c.root) for c in chords]
        assert roots == [57, 62, 64]  # A, D, E

    def test_returns_chord_objects(self):
        chords = progression(C4, MAJOR_SCALE, I, V)
        for c in chords:
            assert isinstance(c, Chord)

    def test_degree_out_of_range(self):
        # PENTATONIC has 5 notes, degree 6 is out of range
        from dawsmith.harmony import PENTATONIC
        with pytest.raises(ValueError, match="out of range"):
            progression(C4, PENTATONIC, vii)

    def test_all_diatonic_degrees(self):
        chords = progression(C4, MAJOR_SCALE, I, ii, iii, IV, V, vi, vii)
        roots = [int(c.root) for c in chords]
        assert roots == [60, 62, 64, 65, 67, 69, 71]
