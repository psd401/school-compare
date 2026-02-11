"""
Explorer Page - Deep dive into a single school or district.
"""

import streamlit as st
import pandas as pd

from config.settings import get_settings
from src.data.client import get_client
from src.viz.charts import (
    create_score_distribution,
    create_demographics_chart,
    create_program_demographics_chart,
    create_spending_trend_chart,
    create_spending_breakdown_chart,
    create_enrollment_trend_chart,
    create_trend_chart,
    create_subgroup_proficiency_chart,
    create_equity_gap_chart,
    create_grade_breakdown_chart,
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

    # Read URL query params for deep-linking
    params = st.query_params
    url_type = params.get("type", None)
    url_id = params.get("id", None)
    url_year = params.get("year", None)

    # Entity selection in main area
    col1, col2 = st.columns([1, 2])

    with col1:
        default_type_index = 1 if url_type == "School" else 0
        org_type = st.radio(
            "Organization Type:",
            options=["District", "School"],
            horizontal=True,
            index=default_type_index,
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
    elif url_id:
        # Auto-load entity from URL params when no active search
        if org_type == "District":
            selected_entity = client.get_district_by_code(url_id)
        else:
            selected_entity = client.get_school_by_code(url_id)

    if not selected_entity:
        st.info("Search for a school or district above to explore its data.")
        return

    # Update URL params for deep-linking
    st.query_params["type"] = org_type
    st.query_params["id"] = selected_entity.organization_id

    st.divider()

    # Display entity header
    st.header(selected_entity.display_name)

    if hasattr(selected_entity, "county") and selected_entity.county:
        st.caption(f"📍 {selected_entity.county} County • {selected_entity.esd_name}")

    # Year selector
    available_years = client.get_available_years()
    if not available_years:
        available_years = ["2023-24"]
    default_year_index = 0
    if url_year and url_year in available_years:
        default_year_index = available_years.index(url_year)
    school_year = st.selectbox(
        "School Year:",
        options=available_years,
        index=default_year_index,
        key="explorer_year",
    )
    st.query_params["year"] = school_year

    # Subgroup and grade level selectors for assessment data
    settings = get_settings()
    sub_col1, sub_col2, sub_col3 = st.columns([2, 2, 1])
    with sub_col1:
        show_all_groups = st.checkbox("Show all subgroups", value=False, key="explorer_show_all")
        group_options = settings.STUDENT_GROUPS_CORE + (settings.STUDENT_GROUPS_EXTENDED if show_all_groups else [])
        student_group = st.selectbox(
            "Student Group:",
            options=group_options,
            index=0,
            key="explorer_student_group",
        )
    with sub_col2:
        grade_level = st.selectbox(
            "Grade Level:",
            options=settings.GRADE_LEVELS,
            index=0,
            key="explorer_grade_level",
        )

    # Load all data
    org_id = selected_entity.organization_id
    org_level = org_type
    spending_year = school_year[2:]  # "2023-24" -> "23-24"

    with st.status(f"Loading {selected_entity.display_name} data...", expanded=True) as status:
        st.write("Loading assessment data...")
        assessment_data = client.get_assessment_data(
            organization_id=org_id,
            organization_level=org_level,
            school_year=school_year,
            student_group=student_group,
            grade_level=grade_level,
        )

        st.write("Loading demographics...")
        demographic_data = client.get_demographics(
            organization_id=org_id,
            organization_level=org_level,
            school_year=school_year,
        )

        st.write("Loading graduation data...")
        graduation_data = client.get_graduation_data(
            organization_id=org_id,
            organization_level=org_level,
            school_year=school_year,
        )

        st.write("Loading staffing data...")
        staffing_data = client.get_staffing_data(
            organization_id=org_id,
            organization_level=org_level,
            school_year=school_year,
        )

        # Spending data (district level only)
        spending_data = None
        spending_trend = None
        enrollment_trend = None
        if org_level == "District":
            st.write("Loading spending data...")
            spending_data = client.get_spending_data(org_id, spending_year)
            spending_trend = client.get_spending_trend(org_id)
            enrollment_trend = client.get_enrollment_trend(org_id)

        status.update(label="Data loaded!", state="complete", expanded=False)

    # Overview metrics in cards
    subgroup_label = f" ({student_group})" if student_group != "All Students" else ""
    grade_label = f" — {grade_level}" if grade_level != "All Grades" else ""
    st.subheader(f"Overview{subgroup_label}{grade_label}")

    metrics_col1, metrics_col2, metrics_col3, metrics_col4 = st.columns(4)

    # Find ELA and Math proficiency
    ela_prof = None
    math_prof = None
    for a in assessment_data:
        if a.test_subject == "ELA" and a.grade_level == grade_level:
            ela_prof = a.proficiency_rate
        elif a.test_subject == "Math" and a.grade_level == grade_level:
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
            if g.cohort == "Four Year" and g.student_group == "All Students":
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
            if a.grade_level == grade_level:
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
            summary_df = pd.DataFrame(summary_data)
            st.dataframe(summary_df, width="stretch")
            st.download_button(
                "Download assessment data (CSV)",
                summary_df.to_csv(index=False),
                file_name=f"{selected_entity.display_name}_assessment_{school_year}.csv",
                mime="text/csv",
            )
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
        st.plotly_chart(fig, width="stretch")
        st.caption("*Hover over chart and click the camera icon to download as PNG*")

        # Subgroup Analysis
        if st.toggle("Show Subgroup Analysis", key="explorer_subgroup_analysis"):
            st.markdown("#### Subgroup Proficiency Analysis")
            subgroup_subject = st.selectbox(
                "Subject:",
                options=["ELA", "Math", "Science"],
                key="explorer_subgroup_subject",
            )

            subgroup_data = {}
            with st.spinner("Loading subgroup data..."):
                for group in settings.STUDENT_GROUPS_CORE:
                    group_assessments = client.get_assessment_data(
                        organization_id=org_id,
                        organization_level=org_level,
                        school_year=school_year,
                        test_subject=subgroup_subject,
                        student_group=group,
                        grade_level=grade_level,
                    )
                    for a in group_assessments:
                        if a.proficiency_rate is not None:
                            subgroup_data[group] = a.proficiency_rate
                            break

            if len(subgroup_data) >= 2:
                sg_tab1, sg_tab2 = st.tabs(["Proficiency Rates", "Equity Gaps"])
                with sg_tab1:
                    fig = create_subgroup_proficiency_chart(
                        subgroup_data,
                        subject=subgroup_subject,
                        org_name=selected_entity.display_name,
                    )
                    st.plotly_chart(fig, width="stretch")
                with sg_tab2:
                    fig = create_equity_gap_chart(
                        {selected_entity.display_name: subgroup_data},
                        subject=subgroup_subject,
                    )
                    st.plotly_chart(fig, width="stretch")
                suppressed_groups = [g for g in settings.STUDENT_GROUPS_CORE if g not in subgroup_data]
                if suppressed_groups:
                    st.caption(f"Data suppressed for: {', '.join(suppressed_groups)}")
            else:
                st.info("Insufficient subgroup data available (most groups suppressed).")

        # Grade-Level Breakdown
        if st.toggle("Show Grade-Level Breakdown", key="explorer_grade_breakdown"):
            st.markdown("#### Proficiency by Grade Level")

            grade_data = []
            with st.spinner("Loading grade-level data..."):
                for grade in settings.GRADE_LEVELS[1:]:  # Skip "All Grades"
                    for subj in ["ELA", "Math", "Science"]:
                        grade_assessments = client.get_assessment_data(
                            organization_id=org_id,
                            organization_level=org_level,
                            school_year=school_year,
                            test_subject=subj,
                            student_group=student_group,
                            grade_level=grade,
                        )
                        for a in grade_assessments:
                            if a.proficiency_rate is not None:
                                grade_data.append({
                                    "grade": grade,
                                    "subject": subj,
                                    "proficiency": a.proficiency_rate,
                                })
                                break

            grades_with_data = set(d["grade"] for d in grade_data)
            if len(grades_with_data) >= 2:
                fig = create_grade_breakdown_chart(
                    grade_data,
                    org_name=selected_entity.display_name,
                )
                st.plotly_chart(fig, width="stretch")
                st.caption("Science is only tested in grades 5, 8, and 11.")
            else:
                st.info("Fewer than 2 grades have assessment data available.")

        # Year-over-year trend
        if st.toggle("Show Assessment Trend", key="explorer_assessment_trend"):
            st.markdown("#### Assessment Proficiency Trend")
            trend_years = available_years[:5]  # Last 5 years (already sorted desc)
            trend_data = {}
            for subj in ["ELA", "Math", "Science"]:
                yearly_vals = {}
                for yr in reversed(trend_years):  # chronological order
                    yr_data = client.get_assessment_data(
                        organization_id=org_id,
                        organization_level=org_level,
                        school_year=yr,
                        test_subject=subj,
                        student_group=student_group,
                        grade_level=grade_level,
                    )
                    for a in yr_data:
                        if a.proficiency_rate is not None:
                            yearly_vals[yr] = a.proficiency_rate
                if yearly_vals:
                    trend_data[subj] = yearly_vals
            if trend_data:
                fig = create_trend_chart(trend_data, metric_name="% Meeting Standard")
                st.plotly_chart(fig, width="stretch")
                st.caption("*Hover over chart and click the camera icon to download as PNG*")
            else:
                st.info("No multi-year trend data available.")
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
            st.plotly_chart(fig, width="stretch")
            st.caption("*Hover over chart and click the camera icon to download as PNG*")

        with demo_col2:
            fig = create_program_demographics_chart(
                {selected_entity.display_name: demographic_data}
            )
            st.plotly_chart(fig, width="stretch")
            st.caption("*Hover over chart and click the camera icon to download as PNG*")

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
            enrollment_df = pd.DataFrame(enrollment_rows)
            st.dataframe(enrollment_df, width="stretch")
            st.download_button(
                "Download enrollment data (CSV)",
                enrollment_df.to_csv(index=False),
                file_name=f"{selected_entity.display_name}_enrollment_{school_year}.csv",
                mime="text/csv",
            )
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
            st.dataframe(grad_rows, width="stretch")

            # Graduation trend
            if st.toggle("Show Graduation Trend", key="explorer_grad_trend"):
                st.markdown("#### Graduation Rate Trend")
                trend_years = available_years[:5]
                grad_trend = {"Four Year": {}, "Five Year": {}}
                for yr in reversed(trend_years):
                    yr_grad = client.get_graduation_data(
                        organization_id=org_id,
                        organization_level=org_level,
                        school_year=yr,
                    )
                    for g in yr_grad:
                        if g.student_group == "All Students" and g.graduation_rate is not None:
                            if g.cohort in grad_trend:
                                grad_trend[g.cohort][yr] = g.graduation_rate
                # Remove empty cohorts
                grad_trend = {k: v for k, v in grad_trend.items() if v}
                if grad_trend:
                    fig = create_trend_chart(grad_trend, metric_name="Graduation Rate (%)")
                    st.plotly_chart(fig, width="stretch")
                    st.caption("*Hover over chart and click the camera icon to download as PNG*")
                else:
                    st.info("No multi-year graduation data available.")
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
                st.plotly_chart(fig, width="stretch")
                st.caption("*Hover over chart and click the camera icon to download as PNG*")

            # Enrollment trend chart
            if enrollment_trend:
                st.markdown("#### 10-Year Enrollment Trend")
                fig = create_enrollment_trend_chart({selected_entity.display_name: enrollment_trend})
                st.plotly_chart(fig, width="stretch")
                st.caption("*Hover over chart and click the camera icon to download as PNG*")

            # Spending category breakdown
            spending_categories = client.get_spending_by_category(org_id)
            if spending_categories:
                st.markdown("#### Spending by Program Category")
                fig = create_spending_breakdown_chart(
                    spending_categories,
                    district_name=selected_entity.display_name,
                )
                st.plotly_chart(fig, width="stretch")
                st.caption("*Hover over chart and click the camera icon to download as PNG*")

            st.caption("Source: OSPI F-196 Financial Reporting Data")
        else:
            st.info("No spending data available for this district.")


if __name__ == "__main__":
    main()
