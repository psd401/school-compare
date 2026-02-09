"""
Washington School Comparison Tool

Compare Washington state schools and districts across demographics,
achievement, staffing, and spending metrics.
"""

import logging
import threading

import streamlit as st

from config.settings import DATASET_IDS
from src.data.client import get_client
from src.data.combined import get_all_district_data, get_all_school_data

logger = logging.getLogger(__name__)

st.set_page_config(
    page_title="WA School Compare",
    page_icon="🏫",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_data(ttl=86400, show_spinner=False)
def _get_homepage_stats():
    """Fetch live counts for homepage display, with hardcoded fallbacks."""
    try:
        client = get_client()
        districts = client._query(
            DATASET_IDS["enrollment"],
            select="COUNT(DISTINCT districtcode) as cnt",
            where="organizationlevel='District' AND schoolyear='2024-25' AND gradelevel='All Grades'",
            limit=1,
        )
        district_count = int(districts[0]["cnt"]) if districts else 295

        schools = client._query(
            DATASET_IDS["enrollment"],
            select="COUNT(DISTINCT schoolcode) as cnt",
            where="organizationlevel='School' AND schoolyear='2024-25' AND gradelevel='All Grades'",
            limit=1,
        )
        school_count = int(schools[0]["cnt"]) if schools else 2400

        enrollment = client._query(
            DATASET_IDS["enrollment"],
            select="SUM(all_students) as total",
            where="organizationlevel='District' AND schoolyear='2024-25' AND gradelevel='All Grades'",
            limit=1,
        )
        total_students = int(float(enrollment[0]["total"])) if enrollment else 1100000

        return district_count, school_count, total_students
    except Exception as e:
        logger.warning("Failed to fetch homepage stats, using fallbacks: %s", e)
        return 295, 2400, 1100000


def main():
    # Cache warming — trigger background data loading on first visit
    if "cache_warmed" not in st.session_state:
        st.session_state.cache_warmed = True

        def _warm():
            try:
                get_all_district_data()
                get_all_school_data()
            except Exception as e:
                logger.warning("Cache warming failed: %s", e)

        threading.Thread(target=_warm, daemon=True).start()

    # Dataset validation — cached 24h, shows sidebar warning if any fail
    try:
        client = get_client()
        dataset_status = client.validate_datasets()
        invalid = [name for name, valid in dataset_status.items() if not valid]
        if invalid:
            st.sidebar.warning(f"Data sources unavailable: {', '.join(invalid)}. Some features may not work.")
    except Exception as e:
        logger.warning("Dataset validation failed: %s", e)

    st.title("Washington School Comparison Tool")

    st.markdown(
        """
        Compare Washington state schools and districts across key metrics:

        - **Achievement**: SBA ELA, Math, and WCAS Science proficiency rates
        - **Demographics**: Student enrollment by race/ethnicity, program participation
        - **Graduation**: Four and five-year adjusted cohort graduation rates
        - **Staffing**: Teacher experience, qualifications, student-teacher ratios

        ### Getting Started

        Use the sidebar to navigate between pages:

        1. **Comparison** - Compare up to 5 schools or districts side-by-side
        2. **Explorer** - Deep dive into a single school or district
        3. **Chat** - Ask questions about Washington school data using AI

        ---

        **Data Source**: [Washington State Report Card](https://reportcard.ospi.k12.wa.us)
        via [data.wa.gov](https://data.wa.gov)
        """
    )

    # Quick stats in columns
    district_count, school_count, total_students = _get_homepage_stats()
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(label="Districts", value=f"{district_count:,}")
        st.caption("Public school districts")

    with col2:
        st.metric(label="Schools", value=f"{school_count:,}")
        st.caption("Public schools")

    with col3:
        st.metric(label="Students", value=f"{total_students / 1_000_000:.1f}M+")
        st.caption("K-12 enrollment")

    st.markdown("---")

    st.info(
        "💡 **Tip**: Suppressed data (marked with *) indicates small sample sizes "
        "where data is hidden to protect student privacy."
    )


if __name__ == "__main__":
    main()
