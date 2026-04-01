"""Tests for dawsmith.duration -- Duration class and named constants."""

import pytest
from dawsmith.duration import (
    Duration,
    WHOLE,
    HALF,
    QUARTER,
    EIGHTH,
    SIXTEENTH,
    THIRTY_SECOND,
)


class TestDuration:
    def test_float_resolution(self):
        assert float(QUARTER) == 1.0
        assert float(HALF) == 2.0
        assert float(WHOLE) == 4.0
        assert float(EIGHTH) == 0.5
        assert float(SIXTEENTH) == 0.25
        assert float(THIRTY_SECOND) == 0.125

    def test_beats_property(self):
        assert QUARTER.beats == 1.0

    def test_repr(self):
        assert repr(QUARTER) == "QUARTER"
        assert repr(Duration(1.5)) == "Duration(1.5)"

    def test_add(self):
        tied = QUARTER + EIGHTH
        assert float(tied) == 1.5

    def test_radd(self):
        result = 1.0 + QUARTER
        assert float(result) == 2.0

    def test_sub(self):
        result = HALF - QUARTER
        assert float(result) == 1.0

    def test_mul(self):
        result = QUARTER * 3
        assert float(result) == 3.0

    def test_rmul(self):
        result = 3 * QUARTER
        assert float(result) == 3.0

    def test_div(self):
        result = WHOLE / 2
        assert float(result) == 2.0

    def test_dot(self):
        dotted = QUARTER.dot
        assert float(dotted) == 1.5
        assert repr(dotted) == "QUARTER.dot"

    def test_triplet(self):
        trip = QUARTER.triplet
        assert abs(float(trip) - 2.0 / 3.0) < 1e-9
        assert repr(trip) == "QUARTER.triplet"

    def test_double_dot(self):
        dd = QUARTER.double_dot
        assert float(dd) == 1.75

    def test_dot_chain(self):
        # Dotted eighth
        dotted_eighth = EIGHTH.dot
        assert float(dotted_eighth) == 0.75

    def test_comparison(self):
        assert EIGHTH < QUARTER
        assert QUARTER == Duration(1.0)
        assert QUARTER == 1.0

    def test_hash(self):
        assert hash(QUARTER) == hash(Duration(1.0))

    def test_negative_raises(self):
        with pytest.raises(ValueError, match="non-negative"):
            Duration(-1.0)

    def test_tied_equals_dotted(self):
        # QUARTER + EIGHTH = 1.5 = QUARTER.dot
        assert QUARTER + EIGHTH == QUARTER.dot
