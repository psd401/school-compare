"""Tests for client helper functions — safe type conversions."""

import pytest

from src.data.client import _safe_float, _safe_percent, _safe_int


class TestSafeFloat:
    def test_valid_float(self):
        assert _safe_float(3.14) == 3.14

    def test_valid_string(self):
        assert _safe_float("3.14") == 3.14

    def test_integer(self):
        assert _safe_float(42) == 42.0

    def test_none(self):
        assert _safe_float(None) is None

    def test_invalid_string(self):
        assert _safe_float("N/A") is None

    def test_empty_string(self):
        assert _safe_float("") is None

    def test_zero(self):
        assert _safe_float(0) == 0.0

    def test_negative(self):
        assert _safe_float(-1.5) == -1.5


class TestSafePercent:
    def test_decimal_to_percent(self):
        """Values 0-1 should be converted to 0-100."""
        assert _safe_percent(0.52) == 52.0

    def test_zero(self):
        assert _safe_percent(0) == 0.0

    def test_one(self):
        assert _safe_percent(1.0) == 100.0

    def test_already_percentage(self):
        """Values > 1 should be returned as-is."""
        assert _safe_percent(52.0) == 52.0

    def test_none(self):
        assert _safe_percent(None) is None

    def test_string_decimal(self):
        assert _safe_percent("0.75") == 75.0

    def test_invalid_string(self):
        assert _safe_percent("N<10") is None

    def test_boundary_half(self):
        assert _safe_percent(0.5) == 50.0


class TestSafeInt:
    def test_valid_int(self):
        assert _safe_int(42) == 42

    def test_float_to_int(self):
        assert _safe_int(42.7) == 42

    def test_string_int(self):
        assert _safe_int("100") == 100

    def test_string_float(self):
        """String floats should be truncated to int."""
        assert _safe_int("100.5") == 100

    def test_none(self):
        assert _safe_int(None) is None

    def test_invalid_string(self):
        assert _safe_int("N/A") is None

    def test_empty_string(self):
        assert _safe_int("") is None

    def test_zero(self):
        assert _safe_int(0) == 0

    def test_negative(self):
        assert _safe_int(-5) == -5
