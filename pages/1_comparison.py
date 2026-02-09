"""
Comparison Page - Compare schools/districts side-by-side.
"""

import pandas as pd
import streamlit as st

from config.settings import get_settings
from src.data.client import get_client
from src.data.models import AssessmentData, DemographicData, GraduationData, StaffingData, SpendingData
from src.viz.charts import (
    create_achievement_comparison,
    create_score_distribution,
    create_demographics_chart,
    create_program_demographics_chart,
    create_graduation_chart,
    create_staffing_chart,
    create_spending_chart,
    create_spending_trend_chart,
    create_multi_entity_trend_chart,
    add_suppression_footnote,
)

st.set_page_config(
    page_title="Compare Schools - WA School Compare",
    page_icon="📊",
    layout="wide",
)


def main():
    st.title("📊 School & District Comparison")
    st.markdown("Compare up to 5 schools or districts across key metrics.")

    client = get_client()

    # Initialize session state
    if "selected_entities" not in st.session_state:
        st.session_state.selected_entities = []

    # Sidebar for entity selection
    with st.sidebar:
        st.header("Select Schools/Districts")

        # Organization type selector
        org_type = st.radio(
            "Compare:",
            options=["Districts", "Schools"],
            horizontal=True,
        )

        # Search input
        search_query = st.text_input(
            f"Search {org_type.lower()}:",
            placeholder=f"Enter {org_type.lower()[:-1]} name...",
        )

        # Search results
        if search_query and len(search_query) >= 2:
            with st.spinner("Searching..."):
                if org_type == "Districts":
                    results = client.search_districts(search_query, limit=20)
                    options = {d.display_name: d for d in results}
                else:
                    results = client.search_schools(search_query, limit=20)
                    options = {s.display_name: s for s in results}

            if options:
                selected = st.selectbox(
                    "Select to add:",
                    options=[""] + list(options.keys()),
                    key="search_results",
                )

                if selected and st.button("Add to Comparison"):
                    entity = options[selected]
                    entity_info = {
                        "id": entity.organization_id,
                        "name": entity.display_name,
                        "type": "District" if org_type == "Districts" else "School",
                    }
                    if len(st.session_state.selected_entities) < 5:
                        if entity_info not in st.session_state.selected_entities:
                            st.session_state.selected_entities.append(entity_info)
                            st.rerun()
                        else:
                            st.warning("Already added!")
                    else:
                        st.warning("Maximum 5 entities for comparison.")
            else:
                st.info("No results found.")

        # Show selected entities
        st.divider()
        st.subheader("Selected for Comparison")
        selected_count = len(st.session_state.selected_entities)
        st.caption(f"{selected_count}/5 selected")
        if selected_count >= 5:
            st.info("Comparing more than 5 entities makes charts hard to read. Remove one to add another.")

        if st.session_state.selected_entities:
            for i, entity in enumerate(st.session_state.selected_entities):
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.write(f"{i+1}. {entity['name']}")
                with col2:
                    if st.button("✕", key=f"remove_{i}"):
                        st.session_state.selected_entities.pop(i)
                        st.rerun()

            if st.button("Clear All"):
                st.session_state.selected_entities = []
                st.rerun()
        else:
            st.info("Search and add schools or districts above.")

    # Main content area
    if not st.session_state.selected_entities:
        st.info("👈 Use the sidebar to search and select schools or districts to compare.")
        return

    # Year and subgroup selectors
    settings = get_settings()
    ctrl_col1, ctrl_col2, ctrl_col3, ctrl_col4 = st.columns([1, 2, 2, 1])
    with ctrl_col1:
        available_years = client.get_available_years()
        school_year = st.selectbox(
            "School Year:",
            options=available_years if available_years else ["2023-24"],
            index=0,
        )
    with ctrl_col2:
        show_all_groups = st.checkbox("Show all subgroups", value=False, key="comp_show_all")
        group_options = settings.STUDENT_GROUPS_CORE + (settings.STUDENT_GROUPS_EXTENDED if show_all_groups else [])
        student_group = st.selectbox(
            "Student Group:",
            options=group_options,
            index=0,
            key="comp_student_group",
        )
    with ctrl_col3:
        grade_level = st.selectbox(
            "Grade Level:",
            options=settings.GRADE_LEVELS,
            index=0,
            key="comp_grade_level",
        )

    # Convert school year format for spending data (2023-24 -> 23-24)
    spending_year = school_year[2:]  # "2023-24" -> "23-24"

    # Load data for all selected entities
    assessment_data: dict[str, list[AssessmentData]] = {}
    demographic_data: dict[str, list[DemographicData]] = {}
    graduation_data: dict[str, list[GraduationData]] = {}
    staffing_data: dict[str, list[StaffingData]] = {}
    spending_data: dict[str, SpendingData] = {}
    spending_trends: dict[str, dict[str, float]] = {}

    with st.status("Loading comparison data...", expanded=True) as status:
        for entity in st.session_state.selected_entities:
            org_level = entity["type"]
            org_id = entity["id"]
            name = entity["name"]
            st.write(f"Loading {name}...")

            # Get assessment data
            assessment_data[name] = client.get_assessment_data(
                organization_id=org_id,
                organization_level=org_level,
                school_year=school_year,
                student_group=student_group,
                grade_level=grade_level,
            )

            # Get demographic data
            demographic_data[name] = client.get_demographics(
                organization_id=org_id,
                organization_level=org_level,
                school_year=school_year,
            )

            # Get graduation data
            graduation_data[name] = client.get_graduation_data(
                organization_id=org_id,
                organization_level=org_level,
                school_year=school_year,
            )

            # Get staffing data
            staffing_data[name] = client.get_staffing_data(
                organization_id=org_id,
                organization_level=org_level,
                school_year=school_year,
            )

            # Get spending data (district level only)
            if org_level == "District":
                spending = client.get_spending_data(org_id, spending_year)
                if spending:
                    spending_data[name] = spending
                trend = client.get_spending_trend(org_id)
                if trend:
                    spending_trends[name] = trend

        status.update(label="Data loaded!", state="complete", expanded=False)

    # Create tabs for different metric categories
    tabs = st.tabs(["Achievement", "Score Distribution", "Demographics", "Graduation", "Staffing", "Spending", "Trends"])

    # Achievement Tab
    with tabs[0]:
        st.subheader("Achievement Comparison")

        if any(assessment_data.values()):
            fig = create_achievement_comparison(assessment_data)
            st.plotly_chart(fig, width="stretch")
            st.caption("*Hover over chart and click the camera icon to download as PNG*")
            st.caption(add_suppression_footnote())
        else:
            st.warning("No assessment data available for the selected entities.")

    # Score Distribution Tab
    with tabs[1]:
        st.subheader("Score Distribution by Performance Level")

        subject = st.selectbox(
            "Subject:",
            options=["ELA", "Math", "Science"],
            key="dist_subject",
        )

        if any(assessment_data.values()):
            fig = create_score_distribution(assessment_data, subject=subject)
            st.plotly_chart(fig, width="stretch")
            st.caption("*Hover over chart and click the camera icon to download as PNG*")
        else:
            st.warning("No score distribution data available.")

    # Demographics Tab
    with tabs[2]:
        st.subheader("Student Demographics")

        demo_col1, demo_col2 = st.columns(2)

        with demo_col1:
            if any(demographic_data.values()):
                fig = create_demographics_chart(demographic_data, group_type="Race/Ethnicity")
                st.plotly_chart(fig, width="stretch")
                st.caption("*Hover over chart and click the camera icon to download as PNG*")
            else:
                st.warning("No race/ethnicity data available.")

        with demo_col2:
            if any(demographic_data.values()):
                fig = create_program_demographics_chart(demographic_data)
                st.plotly_chart(fig, width="stretch")
                st.caption("*Hover over chart and click the camera icon to download as PNG*")
            else:
                st.warning("No program participation data available.")

    # Graduation Tab
    with tabs[3]:
        st.subheader("Graduation Rates")

        cohort = st.radio(
            "Cohort:",
            options=["Four Year", "Five Year"],
            horizontal=True,
            key="grad_cohort",
        )

        if any(graduation_data.values()):
            fig = create_graduation_chart(graduation_data, cohort=cohort)
            st.plotly_chart(fig, width="stretch")
            st.caption("*Hover over chart and click the camera icon to download as PNG*")
            st.caption(add_suppression_footnote())
        else:
            st.warning("No graduation data available for the selected entities.")

    # Staffing Tab
    with tabs[4]:
        st.subheader("Staffing Metrics")

        if any(staffing_data.values()):
            fig = create_staffing_chart(staffing_data)
            st.plotly_chart(fig, width="stretch")
            st.caption("*Hover over chart and click the camera icon to download as PNG*")

            # Also show raw data in table
            st.markdown("#### Staffing Details")
            staff_rows = []
            for name, data in staffing_data.items():
                if data:
                    s = data[0]
                    staff_rows.append(
                        {
                            "Organization": name,
                            "Teacher Count": s.teacher_count,
                            "Avg Years Experience": s.avg_years_experience,
                            "% with Masters": s.percent_with_masters,
                            "Student-Teacher Ratio": s.student_teacher_ratio,
                        }
                    )
            if staff_rows:
                staff_df = pd.DataFrame(staff_rows)
                st.dataframe(staff_df, width="stretch")
                st.download_button(
                    "Download staffing data (CSV)",
                    staff_df.to_csv(index=False),
                    file_name=f"staffing_comparison_{school_year}.csv",
                    mime="text/csv",
                )
        else:
            st.warning("No staffing data available for the selected entities.")

    # Spending Tab
    with tabs[5]:
        st.subheader("Per-Pupil Expenditure")

        # Check if any schools are selected (spending only available for districts)
        has_schools = any(e["type"] == "School" for e in st.session_state.selected_entities)
        if has_schools:
            st.info("💡 Spending data is only available at the district level. School-level spending is not reported separately.")

        if spending_data:
            # Current year comparison
            per_pupil_comparison = {
                name: data.per_pupil_expenditure
                for name, data in spending_data.items()
                if data.per_pupil_expenditure
            }

            if per_pupil_comparison:
                fig = create_spending_chart(per_pupil_comparison)
                st.plotly_chart(fig, width="stretch")
                st.caption("*Hover over chart and click the camera icon to download as PNG*")

            # Spending details table
            st.markdown("#### Spending Details")
            spending_rows = []
            for name, data in spending_data.items():
                spending_rows.append(
                    {
                        "District": name,
                        "Per-Pupil Expenditure": f"${data.per_pupil_expenditure:,.0f}" if data.per_pupil_expenditure else "N/A",
                        "Total Expenditure": f"${data.total_expenditure:,.0f}" if data.total_expenditure else "N/A",
                        "Enrollment": f"{data.enrollment:,}" if data.enrollment else "N/A",
                        "School Year": f"20{data.school_year}",
                    }
                )
            if spending_rows:
                spending_df = pd.DataFrame(spending_rows)
                st.dataframe(spending_df, width="stretch")
                st.download_button(
                    "Download spending data (CSV)",
                    spending_df.to_csv(index=False),
                    file_name=f"spending_comparison_{school_year}.csv",
                    mime="text/csv",
                )

            # Trend chart
            if spending_trends:
                st.markdown("#### 10-Year Spending Trends")
                fig = create_spending_trend_chart(spending_trends)
                st.plotly_chart(fig, width="stretch")
                st.caption("*Hover over chart and click the camera icon to download as PNG*")

            st.caption("Source: OSPI F-196 Financial Reporting Data")
        else:
            if has_schools:
                st.warning("Select districts to view spending data.")
            else:
                st.warning("No spending data available for the selected districts.")

    # Trends Tab
    with tabs[6]:
        st.subheader("Year-Over-Year Trends")

        trend_subject = st.selectbox(
            "Subject:",
            options=["ELA", "Math", "Science"],
            key="trend_subject",
        )

        trend_years = available_years[:5]  # Last 5 years, already desc
        if len(trend_years) < 2:
            st.warning("Need at least 2 years of data for trend analysis.")
        else:
            trend_data = {}
            with st.status("Loading trend data...", expanded=True) as trend_status:
                for entity in st.session_state.selected_entities:
                    name = entity["name"]
                    st.write(f"Loading {name}...")
                    yearly_vals = {}
                    for yr in reversed(trend_years):
                        yr_assessment = client.get_assessment_data(
                            organization_id=entity["id"],
                            organization_level=entity["type"],
                            school_year=yr,
                            test_subject=trend_subject,
                            student_group=student_group,
                            grade_level=grade_level,
                        )
                        for a in yr_assessment:
                            if a.proficiency_rate is not None:
                                yearly_vals[yr] = a.proficiency_rate
                    if yearly_vals:
                        trend_data[name] = yearly_vals
                trend_status.update(label="Trend data loaded!", state="complete", expanded=False)

            if trend_data:
                fig = create_multi_entity_trend_chart(
                    trend_data,
                    metric_name="% Meeting Standard",
                    subject=trend_subject,
                )
                st.plotly_chart(fig, width="stretch")
                st.caption("*Hover over chart and click the camera icon to download as PNG*")
                st.caption(add_suppression_footnote())
            else:
                st.warning(f"No multi-year {trend_subject} data available for the selected entities.")


if __name__ == "__main__":
    main()
