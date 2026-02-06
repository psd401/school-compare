"""Combined district data for correlation analysis."""

import pandas as pd
import streamlit as st
from sodapy import Socrata

from config.settings import get_settings, DATASET_IDS
from .client import F196_DATA_PATH


# Available metrics for scatter plots
METRICS = {
    "per_pupil_expenditure": {
        "label": "Per-Pupil Expenditure ($)",
        "category": "Spending",
        "format": "${:,.0f}",
    },
    "ela_proficiency": {
        "label": "ELA Proficiency Rate (%)",
        "category": "Achievement",
        "format": "{:.1f}%",
    },
    "math_proficiency": {
        "label": "Math Proficiency Rate (%)",
        "category": "Achievement",
        "format": "{:.1f}%",
    },
    "science_proficiency": {
        "label": "Science Proficiency Rate (%)",
        "category": "Achievement",
        "format": "{:.1f}%",
    },
    "graduation_rate_4yr": {
        "label": "4-Year Graduation Rate (%)",
        "category": "Graduation",
        "format": "{:.1f}%",
    },
    "pct_low_income": {
        "label": "Low-Income Students (%)",
        "category": "Demographics",
        "format": "{:.1f}%",
    },
    "pct_ell": {
        "label": "English Language Learners (%)",
        "category": "Demographics",
        "format": "{:.1f}%",
    },
    "pct_sped": {
        "label": "Students with Disabilities (%)",
        "category": "Demographics",
        "format": "{:.1f}%",
    },
    "teacher_experience": {
        "label": "Avg Teacher Experience (years)",
        "category": "Staffing",
        "format": "{:.1f}",
    },
    "pct_teachers_masters": {
        "label": "Teachers with Masters (%)",
        "category": "Staffing",
        "format": "{:.1f}%",
    },
    "student_teacher_ratio": {
        "label": "Student-Teacher Ratio",
        "category": "Staffing",
        "format": "{:.1f}:1",
    },
    "enrollment": {
        "label": "Total Enrollment",
        "category": "Size",
        "format": "{:,.0f}",
    },
}


def _get_socrata_client() -> Socrata:
    """Get Socrata client for batch queries."""
    settings = get_settings()
    return Socrata(settings.SOCRATA_DOMAIN, settings.SOCRATA_APP_TOKEN or None)


@st.cache_data(ttl=86400, show_spinner="Loading spending data...")
def _load_spending_data() -> pd.DataFrame:
    """Load spending data from F-196 CSV."""
    if not F196_DATA_PATH.exists():
        return pd.DataFrame()

    df = pd.read_csv(F196_DATA_PATH)
    # Select only current year columns
    cols = ['district_code', 'district_name', 'per_pupil_24-25', 'enrollment_24-25']
    available = [c for c in cols if c in df.columns]
    df = df[available].copy()

    df = df.rename(columns={
        'per_pupil_24-25': 'per_pupil_expenditure',
        'enrollment_24-25': 'enrollment',
    })
    df['district_code'] = df['district_code'].astype(str)
    return df


@st.cache_data(ttl=86400, show_spinner="Loading assessment data...")
def _load_assessment_data() -> pd.DataFrame:
    """Load all district assessment data in one query."""
    client = _get_socrata_client()

    # Query all district-level assessment data for All Students, All Grades
    # Use 2024-25 dataset (most recent available assessment data)
    results = client.get(
        DATASET_IDS["assessment_2024_25"],
        where="organizationlevel='District' AND schoolyear='2024-25' AND gradelevel='All Grades' AND studentgroup='All Students' AND (testadministration='SBAC' OR testadministration='WCAS')",
        select="districtcode, testsubject, percentlevel3, percentlevel4",
        limit=5000,
    )

    if not results:
        return pd.DataFrame()

    df = pd.DataFrame(results)

    # Calculate proficiency for each subject
    rows = []
    for _, row in df.iterrows():
        district_code = row.get('districtcode')
        subject = row.get('testsubject')

        try:
            level3 = float(row.get('percentlevel3', 0) or 0)
            level4 = float(row.get('percentlevel4', 0) or 0)
            # Convert from decimal to percentage
            if level3 <= 1:
                level3 *= 100
            if level4 <= 1:
                level4 *= 100
            proficiency = level3 + level4
        except (ValueError, TypeError):
            proficiency = None

        rows.append({
            'district_code': district_code,
            'subject': subject,
            'proficiency': proficiency,
        })

    df = pd.DataFrame(rows)

    # Pivot to get columns per subject
    if df.empty:
        return pd.DataFrame()

    pivot = df.pivot_table(
        index='district_code',
        columns='subject',
        values='proficiency',
        aggfunc='first'
    ).reset_index()

    pivot = pivot.rename(columns={
        'ELA': 'ela_proficiency',
        'Math': 'math_proficiency',
        'Science': 'science_proficiency',
    })

    return pivot


@st.cache_data(ttl=86400, show_spinner="Loading graduation data...")
def _load_graduation_data() -> pd.DataFrame:
    """Load all district graduation data in one query."""
    client = _get_socrata_client()

    results = client.get(
        DATASET_IDS["graduation"],
        where="organizationlevel='District' AND schoolyear='2023-24' AND studentgroup='All Students' AND cohort='Four Year'",
        select="districtcode, graduationrate",
        limit=500,
    )

    if not results:
        return pd.DataFrame()

    df = pd.DataFrame(results)
    df = df.rename(columns={'districtcode': 'district_code', 'graduationrate': 'graduation_rate_4yr'})

    # Convert to percentage
    df['graduation_rate_4yr'] = pd.to_numeric(df['graduation_rate_4yr'], errors='coerce')
    df.loc[df['graduation_rate_4yr'] <= 1, 'graduation_rate_4yr'] *= 100

    return df


@st.cache_data(ttl=86400, show_spinner="Loading demographics data...")
def _load_demographics_data() -> pd.DataFrame:
    """Load all district demographics data in one query."""
    client = _get_socrata_client()

    results = client.get(
        DATASET_IDS["enrollment"],
        where="organizationlevel='District' AND schoolyear='2024-25' AND gradelevel='All Grades'",
        select="districtcode, all_students, low_income, english_language_learners, students_with_disabilities",
        limit=500,
    )

    if not results:
        return pd.DataFrame()

    df = pd.DataFrame(results)
    df = df.rename(columns={'districtcode': 'district_code'})

    # Convert to numeric
    for col in ['all_students', 'low_income', 'english_language_learners', 'students_with_disabilities']:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    # Calculate percentages
    df['pct_low_income'] = (df['low_income'] / df['all_students'] * 100).round(1)
    df['pct_ell'] = (df['english_language_learners'] / df['all_students'] * 100).round(1)
    df['pct_sped'] = (df['students_with_disabilities'] / df['all_students'] * 100).round(1)

    return df[['district_code', 'pct_low_income', 'pct_ell', 'pct_sped']]


@st.cache_data(ttl=86400, show_spinner="Loading staffing data...")
def _load_staffing_data() -> pd.DataFrame:
    """Load all district staffing data in one query."""
    client = _get_socrata_client()

    results = client.get(
        DATASET_IDS["teachers"],
        where="organizationlevel='LEA' AND schoolyear='2024-25' AND demographiccategory='All'",
        select="leacode, avgyearsexperience, ma_percent, teachercount",
        limit=500,
    )

    if not results:
        return pd.DataFrame()

    df = pd.DataFrame(results)
    df = df.rename(columns={
        'leacode': 'district_code',
        'avgyearsexperience': 'teacher_experience',
        'ma_percent': 'pct_teachers_masters',
        'teachercount': 'teacher_count',
    })

    # Convert to numeric
    df['teacher_experience'] = pd.to_numeric(df['teacher_experience'], errors='coerce')
    df['pct_teachers_masters'] = pd.to_numeric(df['pct_teachers_masters'], errors='coerce')
    df['teacher_count'] = pd.to_numeric(df['teacher_count'], errors='coerce')

    # Convert masters percent from decimal to percentage
    df.loc[df['pct_teachers_masters'] <= 1, 'pct_teachers_masters'] *= 100

    return df[['district_code', 'teacher_experience', 'pct_teachers_masters', 'teacher_count']]


@st.cache_data(ttl=86400, show_spinner="Combining district data...")
def get_all_district_data() -> pd.DataFrame:
    """
    Load and combine all district-level data into a single DataFrame.

    Uses batch queries (5 total API calls) instead of per-district queries.
    Returns DataFrame with columns for each metric plus district info.
    """
    # Load each data source
    spending = _load_spending_data()
    assessment = _load_assessment_data()
    graduation = _load_graduation_data()
    demographics = _load_demographics_data()
    staffing = _load_staffing_data()

    if spending.empty:
        return pd.DataFrame()

    # Start with spending data as base (has district names)
    df = spending.copy()

    # Merge assessment data
    if not assessment.empty:
        df = df.merge(assessment, on='district_code', how='left')

    # Merge graduation data
    if not graduation.empty:
        df = df.merge(graduation, on='district_code', how='left')

    # Merge demographics data
    if not demographics.empty:
        df = df.merge(demographics, on='district_code', how='left')

    # Merge staffing data
    if not staffing.empty:
        df = df.merge(staffing, on='district_code', how='left')

    # Calculate student-teacher ratio from enrollment and teacher_count
    if 'enrollment' in df.columns and 'teacher_count' in df.columns:
        df['student_teacher_ratio'] = (df['enrollment'] / df['teacher_count']).round(1)

    # Ensure numeric columns
    numeric_cols = [
        'per_pupil_expenditure', 'enrollment', 'ela_proficiency', 'math_proficiency',
        'science_proficiency', 'graduation_rate_4yr', 'pct_low_income', 'pct_ell',
        'pct_sped', 'teacher_experience', 'pct_teachers_masters', 'student_teacher_ratio'
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    return df


def get_metric_label(metric_key: str) -> str:
    """Get display label for a metric."""
    return METRICS.get(metric_key, {}).get("label", metric_key)


def get_metric_format(metric_key: str) -> str:
    """Get format string for a metric."""
    return METRICS.get(metric_key, {}).get("format", "{}")


def format_metric_value(metric_key: str, value) -> str:
    """Format a metric value for display."""
    if pd.isna(value):
        return "N/A"
    fmt = get_metric_format(metric_key)
    try:
        return fmt.format(value)
    except Exception:
        return str(value)
