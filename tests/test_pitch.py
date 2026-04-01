"""Tests for dawsmith.pitch -- Pitch, Interval, named constants, note()."""

import pytest
from dawsmith.pitch import (
    Pitch,
    Interval,
    note,
    C4,
    E4,
    G4,
    Csharp4,
    Dflat4,
    A0,
    UNISON,
    MINOR_THIRD,
    MAJOR_THIRD,
    PERFECT_FIFTH,
    OCTAVE,
)


class TestPitch:
    def test_int_resolution(self):
        assert int(C4) == 60
        assert int(E4) == 64
        assert int(G4) == 67

    def test_index_resolution(self):
        # __index__ allows use in list indexing, hex(), etc.
        assert C4.__index__() == 60

    def test_midi_property(self):
        assert C4.midi == 60

    def test_octave_property(self):
        assert C4.octave == 4
        assert A0.octave == 0

    def test_pitch_class_property(self):
        assert C4.pitch_class == 0
        assert E4.pitch_class == 4

    def test_name_property(self):
        assert C4.name == "C4"
        assert Csharp4.name == "Csharp4"

    def test_repr(self):
        assert repr(C4) == "C4"
        assert repr(Pitch(60)) == "Pitch(60)"

    def test_add_int(self):
        result = C4 + 7
        assert int(result) == 67  # G4

    def test_add_interval(self):
        result = C4 + PERFECT_FIFTH
        assert int(result) == 67

    def test_radd(self):
        result = 7 + C4
        assert int(result) == 67

    def test_sub_int(self):
        result = G4 - 7
        assert int(result) == 60  # C4

    def test_sub_pitch_gives_interval(self):
        interval = G4 - C4
        assert interval == 7  # perfect fifth in semitones
        assert isinstance(interval, int)

    def test_add_pitch_raises(self):
        with pytest.raises(TypeError, match="Cannot add two pitches"):
            C4 + G4

    def test_comparison(self):
        assert C4 < G4
        assert G4 > C4
        assert C4 <= C4
        assert C4 >= C4
        assert C4 == Pitch(60)
        assert C4 == 60

    def test_hash(self):
        assert hash(C4) == hash(Pitch(60))
        s = {C4, Pitch(60)}
        assert len(s) == 1

    def test_validation(self):
        with pytest.raises(ValueError, match="0-127"):
            Pitch(-1)
        with pytest.raises(ValueError, match="0-127"):
            Pitch(128)

    def test_enharmonic_equivalence(self):
        assert int(Csharp4) == int(Dflat4)
        assert Csharp4 == Dflat4


class TestInterval:
    def test_int_resolution(self):
        assert int(PERFECT_FIFTH) == 7
        assert int(OCTAVE) == 12

    def test_repr(self):
        assert repr(PERFECT_FIFTH) == "PERFECT_FIFTH"

    def test_equality(self):
        assert PERFECT_FIFTH == 7
        assert MAJOR_THIRD == 4

    def test_pitch_arithmetic(self):
        # C4 + major third = E4
        assert int(C4 + MAJOR_THIRD) == 64
        # C4 + minor third = Eb4
        assert int(C4 + MINOR_THIRD) == 63
        # C4 + octave = C5
        assert int(C4 + OCTAVE) == 72


class TestNoteFunction:
    def test_natural_notes(self):
        assert int(note("C4")) == 60
        assert int(note("A4")) == 69

    def test_sharp_hash(self):
        assert int(note("C#4")) == 61

    def test_sharp_explicit(self):
        assert int(note("Csharp4")) == 61

    def test_flat(self):
        assert int(note("Db4")) == 61
        assert int(note("Eflat3")) == 51

    def test_unknown_raises(self):
        with pytest.raises(ValueError, match="Unknown note name"):
            note("X4")

    def test_out_of_range(self):
        with pytest.raises(ValueError):
            note("C11")


class TestNamedPitches:
    def test_c4_is_60(self):
        assert int(C4) == 60

    def test_a0_is_21(self):
        assert int(A0) == 21

    def test_import_sharp(self):
        from dawsmith.pitch import Fsharp5
        assert int(Fsharp5) == 78

    def test_import_flat(self):
        from dawsmith.pitch import Bflat3
        assert int(Bflat3) == 58
