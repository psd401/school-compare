"""Socrata API client for OSPI data from data.wa.gov."""

from typing import Optional
import pandas as pd
import streamlit as st
from sodapy import Socrata

from config.settings import get_settings, DATASET_IDS
from pathlib import Path

from .models import (
    School,
    District,
    AssessmentData,
    DemographicData,
    GraduationData,
    StaffingData,
    SpendingData,
)

# Path to F-196 spending data CSV
F196_DATA_PATH = Path(__file__).parent.parent.parent / "data" / "f196" / "per_pupil_expenditure.csv"


class OSPIClient:
    """Client for fetching Washington state education data from data.wa.gov."""

    def __init__(self):
        settings = get_settings()
        self.domain = settings.SOCRATA_DOMAIN
        self.app_token = settings.SOCRATA_APP_TOKEN or None
        self._client: Optional[Socrata] = None

    @property
    def client(self) -> Socrata:
        """Lazy-loaded Socrata client."""
        if self._client is None:
            self._client = Socrata(self.domain, self.app_token)
        return self._client

    def _query(
        self,
        dataset_id: str,
        select: Optional[str] = None,
        where: Optional[str] = None,
        order: Optional[str] = None,
        limit: int = 10000,
    ) -> list[dict]:
        """Execute a SoQL query against a dataset."""
        kwargs = {"limit": limit}
        if select:
            kwargs["select"] = select
        if where:
            kwargs["where"] = where
        if order:
            kwargs["order"] = order

        return self.client.get(dataset_id, **kwargs)

    # -------------------------------------------------------------------------
    # Directory/Search Methods
    # -------------------------------------------------------------------------

    @st.cache_data(ttl=86400, show_spinner=False)
    def search_schools(_self, query: str, limit: int = 50) -> list[School]:
        """Search for schools by name."""
        where_clause = f"upper(schoolname) like upper('%{query}%')"
        results = _self._query(
            DATASET_IDS["assessment"],
            select="DISTINCT schoolcode, schoolname, districtcode, districtname, county, esdname",
            where=f"{where_clause} AND organizationlevel='School'",
            order="schoolname",
            limit=limit,
        )

        schools = []
        seen = set()
        for r in results:
            code = r.get("schoolcode", "")
            if code and code not in seen:
                seen.add(code)
                schools.append(
                    School(
                        school_code=code,
                        school_name=r.get("schoolname", ""),
                        district_code=r.get("districtcode", ""),
                        district_name=r.get("districtname", ""),
                        county=r.get("county", ""),
                        esd_name=r.get("esdname", ""),
                    )
                )
        return schools

    @st.cache_data(ttl=86400, show_spinner=False)
    def search_districts(_self, query: str, limit: int = 50) -> list[District]:
        """Search for districts by name."""
        where_clause = f"upper(districtname) like upper('%{query}%')"
        results = _self._query(
            DATASET_IDS["assessment"],
            select="DISTINCT districtcode, districtname, county, esdname",
            where=f"{where_clause} AND organizationlevel='District'",
            order="districtname",
            limit=limit,
        )

        districts = []
        seen = set()
        for r in results:
            code = r.get("districtcode", "")
            if code and code not in seen:
                seen.add(code)
                districts.append(
                    District(
                        district_code=code,
                        district_name=r.get("districtname", ""),
                        county=r.get("county", ""),
                        esd_name=r.get("esdname", ""),
                    )
                )
        return districts

    @st.cache_data(ttl=86400, show_spinner=False)
    def get_all_districts(_self) -> list[District]:
        """Get all districts in Washington state."""
        results = _self._query(
            DATASET_IDS["assessment"],
            select="DISTINCT districtcode, districtname, county, esdname",
            where="organizationlevel='District'",
            order="districtname",
            limit=500,
        )

        districts = []
        seen = set()
        for r in results:
            code = r.get("districtcode", "")
            if code and code not in seen:
                seen.add(code)
                districts.append(
                    District(
                        district_code=code,
                        district_name=r.get("districtname", ""),
                        county=r.get("county", ""),
                        esd_name=r.get("esdname", ""),
                    )
                )
        return districts

    # -------------------------------------------------------------------------
    # Assessment Data Methods
    # -------------------------------------------------------------------------

    @st.cache_data(ttl=86400, show_spinner=False)
    def get_assessment_data(
        _self,
        organization_id: str,
        organization_level: str = "District",
        school_year: str = "2023-24",
        test_subject: Optional[str] = None,
        student_group: str = "All Students",
        grade_level: str = "All Grades",
    ) -> list[AssessmentData]:
        """Fetch assessment data for a school or district."""
        # Build where clause
        if organization_level == "School":
            id_field = "schoolcode"
        else:
            id_field = "districtcode"

        where_parts = [
            f"{id_field}='{organization_id}'",
            f"organizationlevel='{organization_level}'",
            f"schoolyear='{school_year}'",
            f"gradelevel='{grade_level}'",
            # Only get main assessments (SBAC for ELA/Math, WCAS for Science)
            "(testadministration='SBAC' OR testadministration='WCAS')",
        ]

        if test_subject:
            where_parts.append(f"testsubject='{test_subject}'")

        if student_group:
            where_parts.append(f"studentgroup='{student_group}'")

        where_clause = " AND ".join(where_parts)

        results = _self._query(
            DATASET_IDS["assessment"],
            where=where_clause,
            limit=1000,
        )

        assessments = []
        for r in results:
            # Determine if data is suppressed (dat field contains "N<10" or similar)
            dat_value = r.get("dat", "")
            is_suppressed = dat_value is not None and dat_value != "" and dat_value != "None"

            # Level percentages are stored as decimals (0.52 = 52%)
            level1 = _safe_percent(r.get("percentlevel1"))
            level2 = _safe_percent(r.get("percentlevel2"))
            level3 = _safe_percent(r.get("percentlevel3"))
            level4 = _safe_percent(r.get("percentlevel4"))

            # Calculate proficiency (level 3 + level 4)
            if level3 is not None and level4 is not None:
                percent_met = level3 + level4
            else:
                percent_met = None

            assessments.append(
                AssessmentData(
                    organization_id=organization_id,
                    organization_name=r.get("districtname") or r.get("schoolname", ""),
                    school_year=r.get("schoolyear", school_year),
                    test_subject=r.get("testsubject", ""),
                    grade_level=r.get("gradelevel", grade_level),
                    student_group=r.get("studentgroup", student_group),
                    student_group_type=r.get("studentgrouptype", ""),
                    count_expected=_safe_int(r.get("count_of_students_expected")),
                    count_met_standard=_safe_int(r.get("count_consistent_grade_level_knowledge_and_above")),
                    percent_met_standard=percent_met,
                    percent_level_1=level1,
                    percent_level_2=level2,
                    percent_level_3=level3,
                    percent_level_4=level4,
                    is_suppressed=is_suppressed,
                    suppression_reason=dat_value if is_suppressed else "",
                )
            )
        return assessments

    @st.cache_data(ttl=86400, show_spinner=False)
    def get_assessment_summary(
        _self,
        organization_id: str,
        organization_level: str = "District",
        school_year: str = "2023-24",
    ) -> pd.DataFrame:
        """Get assessment summary for all subjects for an organization."""
        data = _self.get_assessment_data(
            organization_id=organization_id,
            organization_level=organization_level,
            school_year=school_year,
            student_group="All Students",
            grade_level="All Grades",
        )

        if not data:
            return pd.DataFrame()

        rows = []
        for a in data:
            rows.append(
                {
                    "Organization": a.organization_name,
                    "Subject": a.test_subject,
                    "Proficiency Rate": a.proficiency_rate,
                    "Level 1 %": a.percent_level_1,
                    "Level 2 %": a.percent_level_2,
                    "Level 3 %": a.percent_level_3,
                    "Level 4 %": a.percent_level_4,
                    "Students Tested": a.count_expected,
                    "Suppressed": a.is_suppressed,
                }
            )

        return pd.DataFrame(rows)

    # -------------------------------------------------------------------------
    # Demographics Methods
    # -------------------------------------------------------------------------

    @st.cache_data(ttl=86400, show_spinner=False)
    def get_demographics(
        _self,
        organization_id: str,
        organization_level: str = "District",
        school_year: str = "2024-25",  # Enrollment data is released ahead of assessment data
    ) -> list[DemographicData]:
        """Fetch enrollment demographics for a school or district."""
        if organization_level == "School":
            id_field = "schoolcode"
        else:
            id_field = "districtcode"

        # Get aggregate data (all grades combined)
        where_clause = f"{id_field}='{organization_id}' AND organizationlevel='{organization_level}' AND schoolyear='{school_year}' AND gradelevel='All Grades'"

        results = _self._query(
            DATASET_IDS["enrollment"],
            where=where_clause,
            limit=10,
        )

        demographics = []

        if not results:
            return demographics

        r = results[0]
        org_name = r.get("districtname") or r.get("schoolname", "")
        total = _safe_int(r.get("all_students")) or 1  # Avoid division by zero

        # Race/Ethnicity mapping
        race_fields = {
            "American Indian/Alaskan Native": "american_indian_alaskan_native",
            "Asian": "asian",
            "Black/African American": "black_african_american",
            "Hispanic/Latino": "hispanic_latino_of_any_race",
            "Native Hawaiian/Pacific Islander": "native_hawaiian_other_pacific",
            "Two or More Races": "two_or_more_races",
            "White": "white",
        }

        for group_name, field in race_fields.items():
            count = _safe_int(r.get(field))
            if count is not None:
                demographics.append(
                    DemographicData(
                        organization_id=organization_id,
                        organization_name=org_name,
                        school_year=school_year,
                        student_group=group_name,
                        student_group_type="Race/Ethnicity",
                        headcount=count,
                        percent_of_total=(count / total * 100) if total > 0 else None,
                        is_suppressed=False,
                    )
                )

        # Program participation
        program_fields = {
            "Students with Disabilities": "students_with_disabilities",
            "English Language Learners": "english_language_learners",
            "Low-Income": "low_income",
            "Homeless": "homeless",
            "Foster Care": "foster_care",
            "Migrant": "migrant",
        }

        for group_name, field in program_fields.items():
            count = _safe_int(r.get(field))
            if count is not None:
                demographics.append(
                    DemographicData(
                        organization_id=organization_id,
                        organization_name=org_name,
                        school_year=school_year,
                        student_group=group_name,
                        student_group_type="Program",
                        headcount=count,
                        percent_of_total=(count / total * 100) if total > 0 else None,
                        is_suppressed=False,
                    )
                )

        # Gender
        gender_fields = {
            "Female": "female",
            "Male": "male",
            "Gender X": "gender_x",
        }

        for group_name, field in gender_fields.items():
            count = _safe_int(r.get(field))
            if count is not None:
                demographics.append(
                    DemographicData(
                        organization_id=organization_id,
                        organization_name=org_name,
                        school_year=school_year,
                        student_group=group_name,
                        student_group_type="Gender",
                        headcount=count,
                        percent_of_total=(count / total * 100) if total > 0 else None,
                        is_suppressed=False,
                    )
                )

        return demographics

    # -------------------------------------------------------------------------
    # Graduation Methods
    # -------------------------------------------------------------------------

    @st.cache_data(ttl=86400, show_spinner=False)
    def get_graduation_data(
        _self,
        organization_id: str,
        organization_level: str = "District",
        school_year: str = "2023-24",
        student_group: str = "All Students",
    ) -> list[GraduationData]:
        """Fetch graduation rates for a school or district."""
        if organization_level == "School":
            id_field = "schoolcode"
        else:
            id_field = "districtcode"

        where_clause = f"{id_field}='{organization_id}' AND organizationlevel='{organization_level}' AND schoolyear='{school_year}'"

        if student_group:
            where_clause += f" AND studentgroup='{student_group}'"

        results = _self._query(
            DATASET_IDS["graduation"],
            where=where_clause,
            limit=500,
        )

        graduation = []
        for r in results:
            # Check for suppression via dat field
            dat_value = r.get("dat", "")
            is_suppressed = dat_value is not None and "N<10" in str(dat_value)

            # Graduation rate is stored as decimal (0.85 = 85%)
            grad_rate = _safe_float(r.get("graduationrate"))
            if grad_rate is not None and grad_rate <= 1:
                grad_rate = grad_rate * 100

            graduation.append(
                GraduationData(
                    organization_id=organization_id,
                    organization_name=r.get("districtname") or r.get("schoolname", ""),
                    school_year=r.get("schoolyear", school_year),
                    student_group=r.get("studentgroup", student_group),
                    cohort=r.get("cohort", ""),
                    graduation_rate=grad_rate,
                    is_suppressed=is_suppressed,
                )
            )
        return graduation

    # -------------------------------------------------------------------------
    # Staffing Methods
    # -------------------------------------------------------------------------

    @st.cache_data(ttl=86400, show_spinner=False)
    def get_staffing_data(
        _self,
        organization_id: str,
        organization_level: str = "District",
        school_year: str = "2024-25",  # Staffing data is released ahead of assessment data
    ) -> list[StaffingData]:
        """Fetch teacher/staffing data for a school or district."""
        # Teacher data uses LEA instead of District
        if organization_level == "School":
            id_field = "schoolcode"
            org_level = "School"
        else:
            id_field = "leacode"
            org_level = "LEA"

        where_clause = f"{id_field}='{organization_id}' AND organizationlevel='{org_level}' AND schoolyear='{school_year}' AND demographiccategory='All'"

        results = _self._query(
            DATASET_IDS["teachers"],
            where=where_clause,
            limit=10,
        )

        staffing = []
        for r in results:
            # ma_percent is stored as decimal (0.745 = 74.5%)
            masters_pct = _safe_float(r.get("ma_percent"))
            if masters_pct is not None and masters_pct <= 1:
                masters_pct = masters_pct * 100

            # Calculate student-teacher ratio from enrollment data
            teacher_count = _safe_int(r.get("teachercount"))
            student_teacher_ratio = None

            # Try to get enrollment to calculate ratio
            if teacher_count and teacher_count > 0:
                enrollment_results = _self._query(
                    DATASET_IDS["enrollment"],
                    select="all_students",
                    where=f"{id_field.replace('lea', 'district')}='{organization_id}' AND organizationlevel='{organization_level}' AND schoolyear='{school_year}' AND gradelevel='All Grades'",
                    limit=1,
                )
                if enrollment_results:
                    enrollment = _safe_int(enrollment_results[0].get("all_students"))
                    if enrollment:
                        student_teacher_ratio = round(enrollment / teacher_count, 1)

            staffing.append(
                StaffingData(
                    organization_id=organization_id,
                    organization_name=r.get("leaname") or r.get("schoolname") or r.get("organizationname", ""),
                    school_year=r.get("schoolyear", school_year),
                    teacher_count=teacher_count,
                    avg_years_experience=_safe_float(r.get("avgyearsexperience")),
                    percent_with_masters=masters_pct,
                    student_teacher_ratio=student_teacher_ratio,
                )
            )
        return staffing

    # -------------------------------------------------------------------------
    # Spending Data Methods (from F-196 CSV)
    # -------------------------------------------------------------------------

    @st.cache_data(ttl=86400, show_spinner=False)
    def get_spending_data(
        _self,
        district_code: str,
        school_year: str = "24-25",
    ) -> Optional[SpendingData]:
        """
        Fetch per-pupil expenditure data for a district from F-196 data.

        Note: Spending data is only available at the district level, not school level.
        School year format: "24-25" (not "2024-25")
        """
        if not F196_DATA_PATH.exists():
            return None

        df = pd.read_csv(F196_DATA_PATH)

        # Find the district row
        row = df[df['district_code'].astype(str) == str(district_code)]
        if row.empty:
            return None

        row = row.iloc[0]

        # Get data for the specified year
        per_pupil_col = f'per_pupil_{school_year}'
        enrollment_col = f'enrollment_{school_year}'
        expenditure_col = f'expenditure_{school_year}'

        if per_pupil_col not in row.index:
            return None

        per_pupil = row.get(per_pupil_col)
        enrollment = row.get(enrollment_col)
        expenditure = row.get(expenditure_col)

        if pd.isna(per_pupil):
            return None

        return SpendingData(
            district_code=str(district_code),
            district_name=row.get('district_name', ''),
            school_year=school_year,
            per_pupil_expenditure=float(per_pupil) if pd.notna(per_pupil) else None,
            total_expenditure=float(expenditure) if pd.notna(expenditure) else None,
            enrollment=int(enrollment) if pd.notna(enrollment) else None,
        )

    @st.cache_data(ttl=86400, show_spinner=False)
    def get_spending_trend(
        _self,
        district_code: str,
    ) -> dict[str, float]:
        """
        Get per-pupil expenditure trend for a district across all available years.

        Returns dict mapping school year to per-pupil expenditure.
        """
        if not F196_DATA_PATH.exists():
            return {}

        df = pd.read_csv(F196_DATA_PATH)

        row = df[df['district_code'].astype(str) == str(district_code)]
        if row.empty:
            return {}

        row = row.iloc[0]
        trend = {}

        years = ['14-15', '15-16', '16-17', '17-18', '18-19', '19-20', '20-21', '21-22', '22-23', '23-24', '24-25']
        for year in years:
            col = f'per_pupil_{year}'
            if col in row.index and pd.notna(row[col]):
                trend[year] = float(row[col])

        return trend


def _safe_float(value) -> Optional[float]:
    """Safely convert value to float."""
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def _safe_percent(value) -> Optional[float]:
    """Safely convert decimal to percentage (0.52 -> 52.0)."""
    if value is None:
        return None
    try:
        val = float(value)
        # If stored as decimal (0-1 range), convert to percentage
        if 0 <= val <= 1:
            return val * 100
        return val
    except (ValueError, TypeError):
        return None


def _safe_int(value) -> Optional[int]:
    """Safely convert value to int."""
    if value is None:
        return None
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return None


# Singleton instance
_client: Optional[OSPIClient] = None


def get_client() -> OSPIClient:
    """Get or create the OSPI client singleton."""
    global _client
    if _client is None:
        _client = OSPIClient()
    return _client
