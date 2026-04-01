"""Tests for dawsmith.velocity -- Velocity class and dynamics constants."""

import pytest
from dawsmith.velocity import (
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


class TestVelocity:
    def test_int_resolution(self):
        assert int(mf) == 80
        assert int(f) == 96
        assert int(pp) == 33

    def test_index_resolution(self):
        assert mf.__index__() == 80

    def test_dynamics_values(self):
        assert int(ppp) == 16
        assert int(pp) == 33
        assert int(p) == 49
        assert int(mp) == 64
        assert int(mf) == 80
        assert int(f) == 96
        assert int(ff) == 112
        assert int(fff) == 127

    def test_dynamics_ordering(self):
        assert ppp < pp < p < mp < mf < f < ff < fff

    def test_repr(self):
        assert repr(mf) == "mf(80)"
        assert repr(Velocity(100)) == "Velocity(100)"

    def test_add(self):
        result = mf + 10
        assert int(result) == 90

    def test_radd(self):
        result = 10 + mf
        assert int(result) == 90

    def test_sub(self):
        result = f - 10
        assert int(result) == 86

    def test_clamping_high(self):
        result = fff + 50
        assert int(result) == 127

    def test_clamping_low(self):
        result = ppp - 100
        assert int(result) == 0

    def test_accent(self):
        result = mf.accent
        assert int(result) == 100  # 80 + 20

    def test_accent_clamp(self):
        result = fff.accent
        assert int(result) == 127  # clamped

    def test_ghost(self):
        result = mf.ghost
        assert int(result) == 50  # 80 - 30

    def test_ghost_floor(self):
        result = pp.ghost
        assert int(result) == 3  # 33 - 30

    def test_ghost_minimum(self):
        result = ppp.ghost
        assert int(result) == 1  # minimum is 1, not 0

    def test_equality(self):
        assert mf == 80
        assert mf == Velocity(80)

    def test_hash(self):
        assert hash(mf) == hash(Velocity(80))

    def test_value_property(self):
        assert mf.value == 80
