"""Tests for dawsmith.harmony -- scale() and scale pattern constants."""

import pytest
from dawsmith.pitch import C4, A3, Pitch
from dawsmith.harmony import (
    scale,
    MAJOR_SCALE,
    MINOR_SCALE,
    PENTATONIC,
    MINOR_PENTATONIC,
    BLUES,
)


class TestScale:
    def test_major_scale(self):
        pitches = scale(C4, MAJOR_SCALE)
        midi = [int(p) for p in pitches]
        assert midi == [60, 62, 64, 65, 67, 69, 71, 72]

    def test_minor_scale(self):
        pitches = scale(A3, MINOR_SCALE)
        midi = [int(p) for p in pitches]
        assert midi == [57, 59, 60, 62, 64, 65, 67, 69]

    def test_pentatonic(self):
        pitches = scale(C4, PENTATONIC)
        midi = [int(p) for p in pitches]
        assert midi == [60, 62, 64, 67, 69, 72]

    def test_minor_pentatonic(self):
        pitches = scale(A3, MINOR_PENTATONIC)
        midi = [int(p) for p in pitches]
        assert midi == [57, 60, 62, 64, 67, 69]

    def test_blues(self):
        pitches = scale(C4, BLUES)
        midi = [int(p) for p in pitches]
        assert midi == [60, 63, 65, 66, 67, 70, 72]

    def test_two_octaves(self):
        pitches = scale(C4, MAJOR_SCALE, octaves=2)
        midi = [int(p) for p in pitches]
        assert midi == [60, 62, 64, 65, 67, 69, 71, 72, 74, 76, 77, 79, 81, 83, 84]

    def test_returns_pitch_objects(self):
        pitches = scale(C4, MAJOR_SCALE)
        for pitch in pitches:
            assert isinstance(pitch, Pitch)

    def test_high_range_clamping(self):
        # Scale starting high should not include notes > 127
        pitches = scale(Pitch(120), MAJOR_SCALE)
        for pitch in pitches:
            assert int(pitch) <= 127

    def test_with_raw_int_root(self):
        pitches = scale(60, MAJOR_SCALE)
        midi = [int(p) for p in pitches]
        assert midi == [60, 62, 64, 65, 67, 69, 71, 72]
