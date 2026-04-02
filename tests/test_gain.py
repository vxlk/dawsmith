"""Tests for dawsmith.gain module."""

import math

from dawsmith.gain import (
    Gain,
    db,
    SILENT,
    DB_MINUS_48,
    DB_MINUS_24,
    DB_MINUS_12,
    DB_MINUS_6,
    DB_MINUS_3,
    UNITY,
    DB_PLUS_3,
    DB_PLUS_6,
)


# ---------------------------------------------------------------------------
# db() convenience function
# ---------------------------------------------------------------------------

def test_db_to_linear_unity():
    assert abs(float(db(0)) - 1.0) < 1e-9


def test_db_to_linear_minus_6():
    assert abs(float(db(-6)) - 10 ** (-6 / 20)) < 1e-6


def test_db_to_linear_minus_20():
    assert abs(float(db(-20)) - 0.1) < 1e-6


def test_db_to_linear_plus_6():
    expected = 10 ** (6 / 20)
    assert abs(float(db(6)) - expected) < 1e-6


# ---------------------------------------------------------------------------
# Gain class
# ---------------------------------------------------------------------------

def test_gain_float_conversion():
    g = Gain(0.75)
    assert abs(float(g) - 0.75) < 1e-9


def test_gain_int_conversion():
    g = Gain(2.9)
    assert int(g) == 2


def test_gain_from_db():
    g = Gain.from_db(-6)
    assert abs(float(g) - 10 ** (-6 / 20)) < 1e-6


def test_gain_to_db():
    g = Gain(1.0)
    assert abs(g.to_db()) < 1e-9


def test_gain_to_db_silent():
    g = Gain(0.0)
    assert g.to_db() == float("-inf")


def test_gain_to_db_roundtrip():
    for db_val in [-48, -24, -12, -6, -3, 0, 3, 6]:
        g = Gain.from_db(db_val)
        assert abs(g.to_db() - db_val) < 1e-6


# ---------------------------------------------------------------------------
# Arithmetic
# ---------------------------------------------------------------------------

def test_gain_add():
    result = Gain(0.5) + Gain(0.3)
    assert abs(float(result) - 0.8) < 1e-9


def test_gain_add_float():
    result = Gain(0.5) + 0.3
    assert abs(float(result) - 0.8) < 1e-9


def test_gain_radd():
    result = 0.5 + Gain(0.3)
    assert abs(float(result) - 0.8) < 1e-9


def test_gain_sub():
    result = Gain(1.0) - Gain(0.3)
    assert abs(float(result) - 0.7) < 1e-9


def test_gain_mul():
    result = Gain(0.5) * 2.0
    assert abs(float(result) - 1.0) < 1e-9


def test_gain_rmul():
    result = 2.0 * Gain(0.5)
    assert abs(float(result) - 1.0) < 1e-9


def test_gain_div():
    result = Gain(1.0) / 2.0
    assert abs(float(result) - 0.5) < 1e-9


# ---------------------------------------------------------------------------
# Comparison
# ---------------------------------------------------------------------------

def test_gain_eq():
    assert Gain(1.0) == 1.0
    assert Gain(0.5) == Gain(0.5)


def test_gain_lt():
    assert Gain(0.5) < Gain(1.0)


def test_gain_gt():
    assert Gain(1.0) > Gain(0.5)


def test_gain_hash():
    assert hash(Gain(1.0)) == hash(Gain(1.0))


# ---------------------------------------------------------------------------
# Named constants
# ---------------------------------------------------------------------------

def test_silent():
    assert float(SILENT) == 0.0


def test_unity():
    assert abs(float(UNITY) - 1.0) < 1e-9


def test_db_minus_6_constant():
    expected = 10 ** (-6 / 20)
    assert abs(float(DB_MINUS_6) - expected) < 1e-6


def test_db_minus_3_constant():
    expected = 10 ** (-3 / 20)
    assert abs(float(DB_MINUS_3) - expected) < 1e-6


def test_db_minus_12_constant():
    expected = 10 ** (-12 / 20)
    assert abs(float(DB_MINUS_12) - expected) < 1e-6


def test_db_minus_24_constant():
    expected = 10 ** (-24 / 20)
    assert abs(float(DB_MINUS_24) - expected) < 1e-6


def test_db_minus_48_constant():
    expected = 10 ** (-48 / 20)
    assert abs(float(DB_MINUS_48) - expected) < 1e-6


def test_db_plus_3_constant():
    expected = 10 ** (3 / 20)
    assert abs(float(DB_PLUS_3) - expected) < 1e-6


def test_db_plus_6_constant():
    expected = 10 ** (6 / 20)
    assert abs(float(DB_PLUS_6) - expected) < 1e-6


# ---------------------------------------------------------------------------
# Repr
# ---------------------------------------------------------------------------

def test_gain_repr_named():
    assert "UNITY" in repr(UNITY)


def test_gain_repr_unnamed():
    assert "Gain(" in repr(Gain(0.5))
