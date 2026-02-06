"""Tests for combined module — metric helpers and formatting."""

import pytest
import math

from src.data.combined import (
    METRICS,
    SCHOOL_METRICS,
    get_metric_label,
    get_metric_format,
    format_metric_value,
)


class TestMetrics:
    def test_all_metrics_have_required_keys(self):
        for key, meta in METRICS.items():
            assert "label" in meta, f"{key} missing 'label'"
            assert "category" in meta, f"{key} missing 'category'"
            assert "format" in meta, f"{key} missing 'format'"

    def test_expected_metrics_exist(self):
        expected = [
            "per_pupil_expenditure",
            "ela_proficiency",
            "math_proficiency",
            "science_proficiency",
            "graduation_rate_4yr",
            "pct_low_income",
            "pct_ell",
            "pct_sped",
            "teacher_experience",
            "pct_teachers_masters",
            "student_teacher_ratio",
            "enrollment",
        ]
        for key in expected:
            assert key in METRICS, f"Missing metric: {key}"

    def test_metric_count(self):
        assert len(METRICS) == 12


class TestSchoolMetrics:
    def test_all_school_metrics_have_required_keys(self):
        for key, meta in SCHOOL_METRICS.items():
            assert "label" in meta, f"{key} missing 'label'"
            assert "category" in meta, f"{key} missing 'category'"
            assert "format" in meta, f"{key} missing 'format'"

    def test_school_metrics_count(self):
        assert len(SCHOOL_METRICS) == 10

    def test_school_metrics_exclude_spending_and_graduation(self):
        assert "per_pupil_expenditure" not in SCHOOL_METRICS
        assert "graduation_rate_4yr" not in SCHOOL_METRICS

    def test_school_metrics_are_subset_of_district_metrics(self):
        for key in SCHOOL_METRICS:
            assert key in METRICS, f"School metric '{key}' not in district METRICS"


class TestGetMetricLabel:
    def test_known_metric(self):
        assert get_metric_label("per_pupil_expenditure") == "Per-Pupil Expenditure ($)"

    def test_unknown_metric_returns_key(self):
        assert get_metric_label("nonexistent") == "nonexistent"

    def test_ela_proficiency(self):
        assert get_metric_label("ela_proficiency") == "ELA Proficiency Rate (%)"


class TestGetMetricFormat:
    def test_currency_format(self):
        assert get_metric_format("per_pupil_expenditure") == "${:,.0f}"

    def test_percent_format(self):
        assert get_metric_format("ela_proficiency") == "{:.1f}%"

    def test_unknown_metric_returns_bare_format(self):
        assert get_metric_format("nonexistent") == "{}"


class TestFormatMetricValue:
    def test_currency(self):
        assert format_metric_value("per_pupil_expenditure", 15000) == "$15,000"

    def test_percentage(self):
        assert format_metric_value("ela_proficiency", 65.3) == "65.3%"

    def test_ratio(self):
        assert format_metric_value("student_teacher_ratio", 18.5) == "18.5:1"

    def test_enrollment(self):
        assert format_metric_value("enrollment", 50000) == "50,000"

    def test_nan_returns_na(self):
        assert format_metric_value("ela_proficiency", float("nan")) == "N/A"

    def test_none_returns_na(self):
        # pandas NaN check treats None as NaN
        assert format_metric_value("ela_proficiency", None) == "N/A"
