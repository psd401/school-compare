"""Tests for data models — dataclass creation and computed properties."""

import pytest

from src.data.models import (
    School,
    District,
    AssessmentData,
    DemographicData,
    GraduationData,
    StaffingData,
    SpendingData,
    SpendingCategory,
    ComparisonEntity,
)


class TestSchool:
    def test_display_name_includes_district(self):
        school = School(
            school_code="1234",
            school_name="Lincoln High",
            district_code="17001",
            district_name="Seattle SD",
        )
        assert school.display_name == "Lincoln High (Seattle SD)"

    def test_organization_id_returns_school_code(self):
        school = School(
            school_code="1234",
            school_name="Lincoln High",
            district_code="17001",
            district_name="Seattle SD",
        )
        assert school.organization_id == "1234"

    def test_default_organization_type(self):
        school = School(
            school_code="1234",
            school_name="Lincoln High",
            district_code="17001",
            district_name="Seattle SD",
        )
        assert school.organization_type == "School"

    def test_optional_fields_default_empty(self):
        school = School(
            school_code="1234",
            school_name="Lincoln High",
            district_code="17001",
            district_name="Seattle SD",
        )
        assert school.county == ""
        assert school.esd_name == ""
        assert school.city == ""
        assert school.grade_levels == ""


class TestDistrict:
    def test_display_name_is_district_name(self):
        district = District(district_code="17001", district_name="Seattle SD")
        assert district.display_name == "Seattle SD"

    def test_organization_id_returns_district_code(self):
        district = District(district_code="17001", district_name="Seattle SD")
        assert district.organization_id == "17001"

    def test_default_organization_type(self):
        district = District(district_code="17001", district_name="Seattle SD")
        assert district.organization_type == "District"


class TestAssessmentData:
    def test_proficiency_rate_from_percent_met_standard(self):
        a = AssessmentData(
            organization_id="17001",
            organization_name="Seattle SD",
            school_year="2023-24",
            test_subject="ELA",
            grade_level="All Grades",
            student_group="All Students",
            student_group_type="All",
            percent_met_standard=65.0,
            percent_level_3=35.0,
            percent_level_4=30.0,
        )
        # Should prefer percent_met_standard
        assert a.proficiency_rate == 65.0

    def test_proficiency_rate_from_levels_when_no_percent_met(self):
        a = AssessmentData(
            organization_id="17001",
            organization_name="Seattle SD",
            school_year="2023-24",
            test_subject="Math",
            grade_level="All Grades",
            student_group="All Students",
            student_group_type="All",
            percent_met_standard=None,
            percent_level_3=30.0,
            percent_level_4=20.0,
        )
        assert a.proficiency_rate == 50.0

    def test_proficiency_rate_none_when_no_data(self):
        a = AssessmentData(
            organization_id="17001",
            organization_name="Seattle SD",
            school_year="2023-24",
            test_subject="Science",
            grade_level="All Grades",
            student_group="All Students",
            student_group_type="All",
        )
        assert a.proficiency_rate is None

    def test_suppression_defaults(self):
        a = AssessmentData(
            organization_id="17001",
            organization_name="Seattle SD",
            school_year="2023-24",
            test_subject="ELA",
            grade_level="All Grades",
            student_group="All Students",
            student_group_type="All",
        )
        assert a.is_suppressed is False
        assert a.suppression_reason == ""


class TestDemographicData:
    def test_creation(self):
        d = DemographicData(
            organization_id="17001",
            organization_name="Seattle SD",
            school_year="2024-25",
            student_group="White",
            student_group_type="Race/Ethnicity",
            headcount=5000,
            percent_of_total=45.2,
        )
        assert d.headcount == 5000
        assert d.percent_of_total == 45.2
        assert d.is_suppressed is False


class TestGraduationData:
    def test_creation(self):
        g = GraduationData(
            organization_id="17001",
            organization_name="Seattle SD",
            school_year="2023-24",
            student_group="All Students",
            cohort="Four Year",
            graduation_rate=85.5,
        )
        assert g.graduation_rate == 85.5
        assert g.is_suppressed is False


class TestStaffingData:
    def test_creation(self):
        s = StaffingData(
            organization_id="17001",
            organization_name="Seattle SD",
            school_year="2024-25",
            teacher_count=500,
            avg_years_experience=12.3,
            percent_with_masters=65.0,
            student_teacher_ratio=18.5,
        )
        assert s.teacher_count == 500
        assert s.avg_years_experience == 12.3

    def test_optional_fields_default_none(self):
        s = StaffingData(
            organization_id="17001",
            organization_name="Seattle SD",
            school_year="2024-25",
        )
        assert s.teacher_count is None
        assert s.avg_years_experience is None
        assert s.percent_with_masters is None
        assert s.student_teacher_ratio is None


class TestSpendingData:
    def test_creation(self):
        s = SpendingData(
            district_code="17001",
            district_name="Seattle SD",
            school_year="24-25",
            per_pupil_expenditure=15000.0,
            total_expenditure=750000000.0,
            enrollment=50000,
        )
        assert s.per_pupil_expenditure == 15000.0
        assert s.enrollment == 50000


class TestSpendingCategory:
    def test_creation(self):
        c = SpendingCategory(
            district_code="17001",
            category="Basic Education",
            amount=500000000.0,
            percent_of_total=55.2,
        )
        assert c.category == "Basic Education"
        assert c.amount == 500000000.0
        assert c.percent_of_total == 55.2

    def test_optional_fields_default_none(self):
        c = SpendingCategory(
            district_code="17001",
            category="Special Education",
        )
        assert c.amount is None
        assert c.percent_of_total is None


class TestComparisonEntity:
    def test_display_name_school_with_district(self):
        entity = ComparisonEntity(
            organization_id="1234",
            organization_name="Lincoln High",
            organization_type="School",
            district_name="Seattle SD",
        )
        assert entity.display_name == "Lincoln High (Seattle SD)"

    def test_display_name_district(self):
        entity = ComparisonEntity(
            organization_id="17001",
            organization_name="Seattle SD",
            organization_type="District",
        )
        assert entity.display_name == "Seattle SD"

    def test_display_name_school_without_district(self):
        entity = ComparisonEntity(
            organization_id="1234",
            organization_name="Lincoln High",
            organization_type="School",
            district_name="",
        )
        assert entity.display_name == "Lincoln High"

    def test_cached_data_fields_default_empty(self):
        entity = ComparisonEntity(
            organization_id="17001",
            organization_name="Seattle SD",
            organization_type="District",
        )
        assert entity.assessment_data == []
        assert entity.demographic_data == []
        assert entity.graduation_data == []
        assert entity.staffing_data == []
