"""Combined district data for correlation analysis."""

import logging
import re
from concurrent.futures import ThreadPoolExecutor

import pandas as pd
import streamlit as st
from sodapy import Socrata

from config.settings import get_settings, DATASET_IDS
from .client import F196_DATA_PATH, F196_CATEGORIES_PATH

logger = logging.getLogger(__name__)


# Metrics available at school level (excludes spending and graduation which are district-only)
SCHOOL_METRICS = {
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

# Available metrics for scatter plots (district level — includes all)
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
    "pct_spending_basic_ed": {
        "label": "Basic Education Spending (%)",
        "category": "Spending Detail",
        "format": "{:.1f}%",
    },
    "pct_spending_sped": {
        "label": "Special Education Spending (%)",
        "category": "Spending Detail",
        "format": "{:.1f}%",
    },
    "pct_spending_cte": {
        "label": "Vocational/CTE Spending (%)",
        "category": "Spending Detail",
        "format": "{:.1f}%",
    },
    "pct_spending_compensatory": {
        "label": "Compensatory Ed Spending (%)",
        "category": "Spending Detail",
        "format": "{:.1f}%",
    },
    "pct_spending_support": {
        "label": "Districtwide Support Spending (%)",
        "category": "Spending Detail",
        "format": "{:.1f}%",
    },
    "pct_spending_transportation": {
        "label": "Transportation Spending (%)",
        "category": "Spending Detail",
        "format": "{:.1f}%",
    },
    "pct_spending_food": {
        "label": "Food Services Spending (%)",
        "category": "Spending Detail",
        "format": "{:.1f}%",
    },
}


def _get_socrata_client() -> Socrata:
    """Get Socrata client for batch queries."""
    settings = get_settings()
    return Socrata(settings.SOCRATA_DOMAIN, settings.SOCRATA_APP_TOKEN or None)


def _paginated_get(client, dataset_id, batch_size=10000, max_total=100000, **kwargs):
    """Execute a paginated Socrata query, fetching all results up to max_total."""
    all_results = []
    offset = 0
    while offset < max_total:
        try:
            batch = client.get(dataset_id, limit=batch_size, offset=offset, **kwargs)
        except Exception as e:
            logger.error("Paginated query error for dataset %s at offset %d: %s", dataset_id, offset, e)
            break
        all_results.extend(batch)
        if len(batch) < batch_size:
            break
        offset += batch_size
    return all_results


@st.cache_data(ttl=86400, show_spinner="Loading spending data...")
def _load_spending_data() -> pd.DataFrame:
    """Load spending data from F-196 CSV."""
    if not F196_DATA_PATH.exists():
        return pd.DataFrame()

    df = pd.read_csv(F196_DATA_PATH)

    # Dynamically detect the latest year from column headers
    year_pattern = re.compile(r'^per_pupil_(\d{2}-\d{2})$')
    years = sorted(m.group(1) for col in df.columns if (m := year_pattern.match(col)))
    if not years:
        logger.warning("No per_pupil year columns found in F-196 CSV")
        return pd.DataFrame()
    latest_year = years[-1]

    cols = ['district_code', 'district_name', f'per_pupil_{latest_year}', f'enrollment_{latest_year}']
    available = [c for c in cols if c in df.columns]
    df = df[available].copy()

    df = df.rename(columns={
        f'per_pupil_{latest_year}': 'per_pupil_expenditure',
        f'enrollment_{latest_year}': 'enrollment',
    })
    df['district_code'] = df['district_code'].astype(str)
    return df


@st.cache_data(ttl=86400, show_spinner="Loading assessment data...")
def _load_assessment_data() -> pd.DataFrame:
    """Load all district assessment data in one query."""
    client = _get_socrata_client()

    # Query all district-level assessment data for All Students, All Grades
    # Use 2024-25 dataset (most recent available assessment data)
    try:
        results = client.get(
            DATASET_IDS["assessment_2024_25"],
            where="organizationlevel='District' AND schoolyear='2024-25' AND gradelevel='All Grades' AND studentgroup='All Students' AND (testadministration='SBAC' OR testadministration='WCAS')",
            select="districtcode, county, esdname, testsubject, percentlevel3, percentlevel4",
            limit=5000,
        )
    except Exception as e:
        logger.error("Failed to load district assessment data: %s", e)
        return pd.DataFrame()

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
            'county': row.get('county'),
            'esdname': row.get('esdname'),
            'subject': subject,
            'proficiency': proficiency,
        })

    df = pd.DataFrame(rows)

    # Pivot to get columns per subject
    if df.empty:
        return pd.DataFrame()

    pivot = df.pivot_table(
        index=['district_code', 'county', 'esdname'],
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
    """Load all district graduation data, trying 2024-25 first, falling back to 2023-24."""
    client = _get_socrata_client()

    # Try 2024-25 dataset first (most recent)
    try:
        results = client.get(
            DATASET_IDS.get("graduation_2024_25", "isxb-523t"),
            where="organizationlevel='District' AND schoolyear='2024-25' AND studentgroup='All Students' AND cohort='Four Year'",
            select="districtcode, graduationrate",
            limit=500,
        )
    except Exception as e:
        logger.error("Failed to load graduation data (2024-25): %s", e)
        results = []

    # Fall back to legacy dataset if 2024-25 has no data
    if not results:
        try:
            results = client.get(
                DATASET_IDS["graduation"],
                where="organizationlevel='District' AND schoolyear='2023-24' AND studentgroup='All Students' AND cohort='Four Year'",
                select="districtcode, graduationrate",
                limit=500,
            )
        except Exception as e:
            logger.error("Failed to load graduation data (2023-24 fallback): %s", e)
            return pd.DataFrame()

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

    try:
        results = client.get(
            DATASET_IDS["enrollment"],
            where="organizationlevel='District' AND schoolyear='2024-25' AND gradelevel='All Grades'",
            select="districtcode, all_students, low_income, english_language_learners, students_with_disabilities",
            limit=500,
        )
    except Exception as e:
        logger.error("Failed to load district demographics data: %s", e)
        return pd.DataFrame()

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

    try:
        results = client.get(
            DATASET_IDS["teachers"],
            where="organizationlevel='LEA' AND schoolyear='2024-25' AND demographiccategory='All'",
            select="leacode, avgyearsexperience, ma_percent, teachercount",
            limit=500,
        )
    except Exception as e:
        logger.error("Failed to load district staffing data: %s", e)
        return pd.DataFrame()

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


@st.cache_data(ttl=86400, show_spinner="Loading spending categories...")
def _load_spending_categories_data() -> pd.DataFrame:
    """Load spending category percentages from expenditures_by_program.csv, pivoted by category."""
    if not F196_CATEGORIES_PATH.exists():
        return pd.DataFrame()

    df = pd.read_csv(F196_CATEGORIES_PATH)
    df['district_code'] = df['district_code'].astype(str)
    df['amount'] = pd.to_numeric(df['amount'], errors='coerce')

    # Calculate total per district for percentage
    totals = df.groupby('district_code')['amount'].sum().rename('total')
    df = df.merge(totals, on='district_code')
    df['pct'] = (df['amount'] / df['total'] * 100).round(1)

    # Map category names to column keys
    category_map = {
        'Basic Education': 'pct_spending_basic_ed',
        'Special Education': 'pct_spending_sped',
        'Vocational/CTE': 'pct_spending_cte',
        'Compensatory Education': 'pct_spending_compensatory',
        'Districtwide Support': 'pct_spending_support',
        'Transportation': 'pct_spending_transportation',
        'Food Services': 'pct_spending_food',
    }

    # Filter to categories we want and pivot
    df = df[df['category'].isin(category_map.keys())]
    df['col_key'] = df['category'].map(category_map)

    pivot = df.pivot_table(
        index='district_code',
        columns='col_key',
        values='pct',
        aggfunc='first',
    ).reset_index()

    return pivot


# -------------------------------------------------------------------------
# School-Level Data Loaders
# -------------------------------------------------------------------------

@st.cache_data(ttl=86400, show_spinner="Loading school assessment data...")
def _load_school_assessment_data() -> pd.DataFrame:
    """Load all school-level assessment data in one query."""
    client = _get_socrata_client()

    results = _paginated_get(
        client,
        DATASET_IDS["assessment_2024_25"],
        where="organizationlevel='School' AND schoolyear='2024-25' AND gradelevel='All Grades' AND studentgroup='All Students' AND (testadministration='SBAC' OR testadministration='WCAS')",
        select="districtcode, districtname, schoolcode, schoolname, county, esdname, testsubject, percentlevel3, percentlevel4",
    )

    if not results:
        return pd.DataFrame()

    df = pd.DataFrame(results)

    rows = []
    for _, row in df.iterrows():
        try:
            level3 = float(row.get('percentlevel3', 0) or 0)
            level4 = float(row.get('percentlevel4', 0) or 0)
            if level3 <= 1:
                level3 *= 100
            if level4 <= 1:
                level4 *= 100
            proficiency = level3 + level4
        except (ValueError, TypeError):
            proficiency = None

        rows.append({
            'school_code': row.get('schoolcode'),
            'school_name': row.get('schoolname'),
            'district_code': row.get('districtcode'),
            'district_name': row.get('districtname'),
            'county': row.get('county'),
            'esdname': row.get('esdname'),
            'subject': row.get('testsubject'),
            'proficiency': proficiency,
        })

    df = pd.DataFrame(rows)
    if df.empty:
        return pd.DataFrame()

    pivot = df.pivot_table(
        index=['school_code', 'school_name', 'district_code', 'district_name', 'county', 'esdname'],
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


@st.cache_data(ttl=86400, show_spinner="Loading school demographics data...")
def _load_school_demographics_data() -> pd.DataFrame:
    """Load all school-level demographics data in one query."""
    client = _get_socrata_client()

    results = _paginated_get(
        client,
        DATASET_IDS["enrollment"],
        where="organizationlevel='School' AND schoolyear='2024-25' AND gradelevel='All Grades'",
        select="schoolcode, all_students, low_income, english_language_learners, students_with_disabilities",
    )

    if not results:
        return pd.DataFrame()

    df = pd.DataFrame(results)
    df = df.rename(columns={'schoolcode': 'school_code'})

    for col in ['all_students', 'low_income', 'english_language_learners', 'students_with_disabilities']:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    df['pct_low_income'] = (df['low_income'] / df['all_students'] * 100).round(1)
    df['pct_ell'] = (df['english_language_learners'] / df['all_students'] * 100).round(1)
    df['pct_sped'] = (df['students_with_disabilities'] / df['all_students'] * 100).round(1)
    df = df.rename(columns={'all_students': 'enrollment'})

    return df[['school_code', 'enrollment', 'pct_low_income', 'pct_ell', 'pct_sped']]


@st.cache_data(ttl=86400, show_spinner="Loading school staffing data...")
def _load_school_staffing_data() -> pd.DataFrame:
    """Load all school-level staffing data in one query."""
    client = _get_socrata_client()

    results = _paginated_get(
        client,
        DATASET_IDS["teachers"],
        where="organizationlevel='School' AND schoolyear='2024-25' AND demographiccategory='All'",
        select="schoolcode, avgyearsexperience, ma_percent, teachercount",
    )

    if not results:
        return pd.DataFrame()

    df = pd.DataFrame(results)
    df = df.rename(columns={
        'schoolcode': 'school_code',
        'avgyearsexperience': 'teacher_experience',
        'ma_percent': 'pct_teachers_masters',
        'teachercount': 'teacher_count',
    })

    df['teacher_experience'] = pd.to_numeric(df['teacher_experience'], errors='coerce')
    df['pct_teachers_masters'] = pd.to_numeric(df['pct_teachers_masters'], errors='coerce')
    df['teacher_count'] = pd.to_numeric(df['teacher_count'], errors='coerce')

    df.loc[df['pct_teachers_masters'] <= 1, 'pct_teachers_masters'] *= 100

    return df[['school_code', 'teacher_experience', 'pct_teachers_masters', 'teacher_count']]


@st.cache_data(ttl=86400, show_spinner=False)
def get_all_school_data() -> pd.DataFrame:
    """
    Load and combine all school-level data into a single DataFrame.

    Excludes spending (district-only) and graduation (district-only).
    Runs loaders in parallel via ThreadPoolExecutor for faster cold-cache loads.
    Returns DataFrame with columns for each metric plus school/district info.
    """
    with ThreadPoolExecutor(max_workers=3) as executor:
        assessment_future = executor.submit(_load_school_assessment_data)
        demographics_future = executor.submit(_load_school_demographics_data)
        staffing_future = executor.submit(_load_school_staffing_data)

    assessment = assessment_future.result()
    demographics = demographics_future.result()
    staffing = staffing_future.result()

    if assessment.empty:
        return pd.DataFrame()

    # Start with assessment as base (has school and district names)
    df = assessment.copy()

    if not demographics.empty:
        df = df.merge(demographics, on='school_code', how='left')

    if not staffing.empty:
        df = df.merge(staffing, on='school_code', how='left')

    # Calculate student-teacher ratio
    if 'enrollment' in df.columns and 'teacher_count' in df.columns:
        df['student_teacher_ratio'] = (df['enrollment'] / df['teacher_count']).round(1)

    # Ensure numeric columns
    numeric_cols = [
        'enrollment', 'ela_proficiency', 'math_proficiency', 'science_proficiency',
        'pct_low_income', 'pct_ell', 'pct_sped', 'teacher_experience',
        'pct_teachers_masters', 'student_teacher_ratio'
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    return df


# -------------------------------------------------------------------------
# District-Level Combined Data
# -------------------------------------------------------------------------

@st.cache_data(ttl=86400, show_spinner=False)
def get_all_district_data() -> pd.DataFrame:
    """
    Load and combine all district-level data into a single DataFrame.

    Uses batch queries (5 total API calls) instead of per-district queries.
    Runs loaders in parallel via ThreadPoolExecutor for faster cold-cache loads.
    Returns DataFrame with columns for each metric plus district info.
    """
    # Load each data source in parallel
    with ThreadPoolExecutor(max_workers=6) as executor:
        spending_future = executor.submit(_load_spending_data)
        assessment_future = executor.submit(_load_assessment_data)
        graduation_future = executor.submit(_load_graduation_data)
        demographics_future = executor.submit(_load_demographics_data)
        staffing_future = executor.submit(_load_staffing_data)
        spending_cat_future = executor.submit(_load_spending_categories_data)

    spending = spending_future.result()
    assessment = assessment_future.result()
    graduation = graduation_future.result()
    demographics = demographics_future.result()
    staffing = staffing_future.result()
    spending_categories = spending_cat_future.result()

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

    # Merge spending categories
    if not spending_categories.empty:
        df = df.merge(spending_categories, on='district_code', how='left')

    # Calculate student-teacher ratio from enrollment and teacher_count
    if 'enrollment' in df.columns and 'teacher_count' in df.columns:
        df['student_teacher_ratio'] = (df['enrollment'] / df['teacher_count']).round(1)

    # Ensure numeric columns
    numeric_cols = [
        'per_pupil_expenditure', 'enrollment', 'ela_proficiency', 'math_proficiency',
        'science_proficiency', 'graduation_rate_4yr', 'pct_low_income', 'pct_ell',
        'pct_sped', 'teacher_experience', 'pct_teachers_masters', 'student_teacher_ratio',
        'pct_spending_basic_ed', 'pct_spending_sped', 'pct_spending_cte',
        'pct_spending_compensatory', 'pct_spending_support', 'pct_spending_transportation',
        'pct_spending_food',
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
