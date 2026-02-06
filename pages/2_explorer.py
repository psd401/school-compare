"""
Explorer Page - Deep dive into a single school or district.
"""

import streamlit as st
import pandas as pd

from src.data.client import get_client
from src.viz.charts import (
    create_score_distribution,
    create_demographics_chart,
    create_program_demographics_chart,
    create_spending_trend_chart,
    add_suppression_footnote,
)

st.set_page_config(
    page_title="Explore School - WA School Compare",
    page_icon="🔍",
    layout="wide",
)


def main():
    st.title("🔍 School & District Explorer")
    st.markdown("Deep dive into metrics for a single school or district.")

    client = get_client()

    # Entity selection in main area
    col1, col2 = st.columns([1, 2])

    with col1:
        org_type = st.radio(
            "Organization Type:",
            options=["District", "School"],
            horizontal=True,
        )

    with col2:
        search_query = st.text_input(
            f"Search {org_type.lower()}s:",
            placeholder=f"Enter {org_type.lower()} name...",
        )

    # Search and select
    selected_entity = None

    if search_query and len(search_query) >= 2:
        with st.spinner("Searching..."):
            if org_type == "District":
                results = client.search_districts(search_query, limit=20)
                options = {d.display_name: d for d in results}
            else:
                results = client.search_schools(search_query, limit=20)
                options = {s.display_name: s for s in results}

        if options:
            selected_name = st.selectbox(
                "Select:",
                options=list(options.keys()),
            )
            selected_entity = options.get(selected_name)
        else:
            st.warning("No results found.")

    if not selected_entity:
        st.info("Search for a school or district above to explore its data.")
        return

    st.divider()

    # Display entity header
    st.header(selected_entity.display_name)

    if hasattr(selected_entity, "county") and selected_entity.county:
        st.caption(f"📍 {selected_entity.county} County • {selected_entity.esd_name}")

    # Year selector
    school_year = st.selectbox(
        "School Year:",
        options=["2023-24", "2022-23", "2021-22"],
        index=0,
        key="explorer_year",
    )

    # Load all data
    org_id = selected_entity.organization_id
    org_level = org_type
    spending_year = school_year[2:]  # "2023-24" -> "23-24"

    with st.spinner("Loading data..."):
        assessment_data = client.get_assessment_data(
            organization_id=org_id,
            organization_level=org_level,
            school_year=school_year,
            student_group="All Students",
            grade_level="All Grades",
        )

        demographic_data = client.get_demographics(
            organization_id=org_id,
            organization_level=org_level,
            school_year=school_year,
        )

        graduation_data = client.get_graduation_data(
            organization_id=org_id,
            organization_level=org_level,
            school_year=school_year,
        )

        staffing_data = client.get_staffing_data(
            organization_id=org_id,
            organization_level=org_level,
            school_year=school_year,
        )

        # Spending data (district level only)
        spending_data = None
        spending_trend = None
        if org_level == "District":
            spending_data = client.get_spending_data(org_id, spending_year)
            spending_trend = client.get_spending_trend(org_id)

    # Overview metrics in cards
    st.subheader("Overview")

    metrics_col1, metrics_col2, metrics_col3, metrics_col4 = st.columns(4)

    # Find ELA and Math proficiency
    ela_prof = None
    math_prof = None
    for a in assessment_data:
        if a.test_subject == "ELA" and a.grade_level == "All Grades":
            ela_prof = a.proficiency_rate
        elif a.test_subject == "Math" and a.grade_level == "All Grades":
            math_prof = a.proficiency_rate

    with metrics_col1:
        if ela_prof is not None:
            st.metric("ELA Proficiency", f"{ela_prof:.1f}%")
        else:
            st.metric("ELA Proficiency", "N/A")

    with metrics_col2:
        if math_prof is not None:
            st.metric("Math Proficiency", f"{math_prof:.1f}%")
        else:
            st.metric("Math Proficiency", "N/A")

    with metrics_col3:
        # Find graduation rate
        grad_rate = None
        for g in graduation_data:
            if g.cohort == "Four-Year" and g.student_group == "All Students":
                grad_rate = g.graduation_rate
                break
        if grad_rate is not None:
            st.metric("Graduation Rate", f"{grad_rate:.1f}%")
        else:
            st.metric("Graduation Rate", "N/A")

    with metrics_col4:
        # Find student-teacher ratio
        if staffing_data:
            ratio = staffing_data[0].student_teacher_ratio
            if ratio:
                st.metric("Student-Teacher Ratio", f"{ratio:.1f}:1")
            else:
                st.metric("Student-Teacher Ratio", "N/A")
        else:
            st.metric("Student-Teacher Ratio", "N/A")

    # Detailed sections
    st.divider()

    # Achievement Section
    st.subheader("📈 Achievement")

    if assessment_data:
        # Summary table
        summary_data = []
        for a in assessment_data:
            if a.grade_level == "All Grades":
                summary_data.append(
                    {
                        "Subject": a.test_subject,
                        "% Meeting Standard": f"{a.proficiency_rate:.1f}%" if a.proficiency_rate else "N/A",
                        "Level 1": f"{a.percent_level_1:.1f}%" if a.percent_level_1 else "N/A",
                        "Level 2": f"{a.percent_level_2:.1f}%" if a.percent_level_2 else "N/A",
                        "Level 3": f"{a.percent_level_3:.1f}%" if a.percent_level_3 else "N/A",
                        "Level 4": f"{a.percent_level_4:.1f}%" if a.percent_level_4 else "N/A",
                        "Students Tested": a.count_expected if a.count_expected else "N/A",
                        "Suppressed": "Yes" if a.is_suppressed else "No",
                    }
                )

        if summary_data:
            st.dataframe(summary_data, use_container_width=True)
            st.caption(add_suppression_footnote())

        # Score distribution chart
        st.markdown("#### Score Distribution")
        subject = st.selectbox(
            "Subject:",
            options=["ELA", "Math", "Science"],
            key="explorer_subject",
        )
        fig = create_score_distribution(
            {selected_entity.display_name: assessment_data},
            subject=subject,
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No assessment data available.")

    # Demographics Section
    st.divider()
    st.subheader("👥 Demographics")

    if demographic_data:
        demo_col1, demo_col2 = st.columns(2)

        with demo_col1:
            fig = create_demographics_chart(
                {selected_entity.display_name: demographic_data},
                group_type="Race/Ethnicity",
            )
            st.plotly_chart(fig, use_container_width=True)

        with demo_col2:
            fig = create_program_demographics_chart(
                {selected_entity.display_name: demographic_data}
            )
            st.plotly_chart(fig, use_container_width=True)

        # Enrollment table
        st.markdown("#### Enrollment Details")
        enrollment_rows = []
        for d in demographic_data:
            if d.student_group_type in ["Race/Ethnicity", "Program"]:
                enrollment_rows.append(
                    {
                        "Category": d.student_group_type,
                        "Group": d.student_group,
                        "Headcount": d.headcount,
                        "% of Total": f"{d.percent_of_total:.1f}%" if d.percent_of_total else "N/A",
                    }
                )
        if enrollment_rows:
            df = pd.DataFrame(enrollment_rows)
            st.dataframe(df, use_container_width=True)
    else:
        st.info("No demographic data available.")

    # Graduation Section
    st.divider()
    st.subheader("🎓 Graduation")

    if graduation_data:
        grad_rows = []
        for g in graduation_data:
            if g.student_group == "All Students":
                grad_rows.append(
                    {
                        "Cohort": g.cohort,
                        "Graduation Rate": f"{g.graduation_rate:.1f}%" if g.graduation_rate else "N/A",
                        "Suppressed": "Yes" if g.is_suppressed else "No",
                    }
                )
        if grad_rows:
            st.dataframe(grad_rows, use_container_width=True)
    else:
        st.info("No graduation data available.")

    # Staffing Section
    st.divider()
    st.subheader("👨‍🏫 Staffing")

    if staffing_data:
        s = staffing_data[0]
        staff_col1, staff_col2, staff_col3, staff_col4 = st.columns(4)

        with staff_col1:
            st.metric("Teacher Count", s.teacher_count or "N/A")

        with staff_col2:
            st.metric(
                "Avg Years Experience",
                f"{s.avg_years_experience:.1f}" if s.avg_years_experience else "N/A",
            )

        with staff_col3:
            st.metric(
                "% with Masters",
                f"{s.percent_with_masters:.1f}%" if s.percent_with_masters else "N/A",
            )

        with staff_col4:
            st.metric(
                "Student-Teacher Ratio",
                f"{s.student_teacher_ratio:.1f}:1" if s.student_teacher_ratio else "N/A",
            )
    else:
        st.info("No staffing data available.")

    # Spending Section (District only)
    if org_level == "District":
        st.divider()
        st.subheader("💰 Spending")

        if spending_data:
            spend_col1, spend_col2, spend_col3 = st.columns(3)

            with spend_col1:
                st.metric(
                    "Per-Pupil Expenditure",
                    f"${spending_data.per_pupil_expenditure:,.0f}" if spending_data.per_pupil_expenditure else "N/A",
                )

            with spend_col2:
                st.metric(
                    "Total Expenditure",
                    f"${spending_data.total_expenditure:,.0f}" if spending_data.total_expenditure else "N/A",
                )

            with spend_col3:
                st.metric(
                    "Enrollment (F-196)",
                    f"{spending_data.enrollment:,}" if spending_data.enrollment else "N/A",
                )

            # Spending trend chart
            if spending_trend:
                st.markdown("#### 10-Year Spending Trend")
                fig = create_spending_trend_chart({selected_entity.display_name: spending_trend})
                st.plotly_chart(fig, use_container_width=True)

            st.caption("Source: OSPI F-196 Financial Reporting Data")
        else:
            st.info("No spending data available for this district.")


if __name__ == "__main__":
    main()
