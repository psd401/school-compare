"""
Washington School Comparison Tool

Compare Washington state schools and districts across demographics,
achievement, staffing, and spending metrics.
"""

import streamlit as st

st.set_page_config(
    page_title="WA School Compare",
    page_icon="🏫",
    layout="wide",
    initial_sidebar_state="expanded",
)


def main():
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
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(label="Districts", value="295")
        st.caption("Public school districts")

    with col2:
        st.metric(label="Schools", value="2,400+")
        st.caption("Public schools")

    with col3:
        st.metric(label="Students", value="1.1M+")
        st.caption("K-12 enrollment")

    st.markdown("---")

    st.info(
        "💡 **Tip**: Suppressed data (marked with *) indicates small sample sizes "
        "where data is hidden to protect student privacy."
    )


if __name__ == "__main__":
    main()
