"""Data models for Washington school/district data."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class School:
    """Represents a Washington state public school."""

    school_code: str
    school_name: str
    district_code: str
    district_name: str
    county: str = ""
    esd_name: str = ""
    city: str = ""
    grade_levels: str = ""
    organization_type: str = "School"

    @property
    def display_name(self) -> str:
        return f"{self.school_name} ({self.district_name})"

    @property
    def organization_id(self) -> str:
        return self.school_code


@dataclass
class District:
    """Represents a Washington state public school district."""

    district_code: str
    district_name: str
    county: str = ""
    esd_name: str = ""
    organization_type: str = "District"

    @property
    def display_name(self) -> str:
        return self.district_name

    @property
    def organization_id(self) -> str:
        return self.district_code


@dataclass
class AssessmentData:
    """Assessment results for a school/district."""

    organization_id: str
    organization_name: str
    school_year: str
    test_subject: str
    grade_level: str
    student_group: str
    student_group_type: str
    count_expected: Optional[int] = None
    count_met_standard: Optional[int] = None
    percent_met_standard: Optional[float] = None
    percent_level_1: Optional[float] = None
    percent_level_2: Optional[float] = None
    percent_level_3: Optional[float] = None
    percent_level_4: Optional[float] = None
    is_suppressed: bool = False
    suppression_reason: str = ""

    @property
    def proficiency_rate(self) -> Optional[float]:
        """Combined Level 3 + Level 4 percentage."""
        if self.percent_met_standard is not None:
            return self.percent_met_standard
        if self.percent_level_3 is not None and self.percent_level_4 is not None:
            return self.percent_level_3 + self.percent_level_4
        return None


@dataclass
class DemographicData:
    """Enrollment demographics for a school/district."""

    organization_id: str
    organization_name: str
    school_year: str
    student_group: str
    student_group_type: str
    headcount: Optional[int] = None
    percent_of_total: Optional[float] = None
    is_suppressed: bool = False


@dataclass
class GraduationData:
    """Graduation rates for a school/district."""

    organization_id: str
    organization_name: str
    school_year: str
    student_group: str
    cohort: str  # "Four-Year" or "Five-Year"
    graduation_rate: Optional[float] = None
    is_suppressed: bool = False


@dataclass
class StaffingData:
    """Teacher/staffing data for a school/district."""

    organization_id: str
    organization_name: str
    school_year: str
    teacher_count: Optional[int] = None
    avg_years_experience: Optional[float] = None
    percent_with_masters: Optional[float] = None
    student_teacher_ratio: Optional[float] = None


@dataclass
class SpendingData:
    """Per-pupil expenditure data for a district (from F-196)."""

    district_code: str
    district_name: str
    school_year: str
    per_pupil_expenditure: Optional[float] = None
    total_expenditure: Optional[float] = None
    enrollment: Optional[int] = None


@dataclass
class ComparisonEntity:
    """A school or district selected for comparison."""

    organization_id: str
    organization_name: str
    organization_type: str  # "School" or "District"
    district_name: str = ""
    county: str = ""

    # Cached data
    assessment_data: list[AssessmentData] = field(default_factory=list)
    demographic_data: list[DemographicData] = field(default_factory=list)
    graduation_data: list[GraduationData] = field(default_factory=list)
    staffing_data: list[StaffingData] = field(default_factory=list)

    @property
    def display_name(self) -> str:
        if self.organization_type == "School" and self.district_name:
            return f"{self.organization_name} ({self.district_name})"
        return self.organization_name
