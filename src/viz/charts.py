"""Plotly chart generators for school comparison visualizations."""

from typing import Optional
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src.data.models import AssessmentData, DemographicData, GraduationData, StaffingData, SpendingCategory


# Color palette for consistent styling
COLORS = {
    "primary": "#1f77b4",
    "secondary": "#ff7f0e",
    "success": "#2ca02c",
    "warning": "#d62728",
    "level1": "#d62728",  # Below Basic - red
    "level2": "#ff7f0e",  # Basic - orange
    "level3": "#2ca02c",  # Proficient - green
    "level4": "#1f77b4",  # Advanced - blue
    "suppressed": "#999999",
}

# Color sequence for comparing multiple entities
ENTITY_COLORS = px.colors.qualitative.Set2


def create_achievement_comparison(
    data: dict[str, list[AssessmentData]],
    subjects: Optional[list[str]] = None,
) -> go.Figure:
    """
    Create grouped bar chart comparing achievement across organizations.

    Args:
        data: Dict mapping organization name to list of AssessmentData
        subjects: List of subjects to include (default: ELA, Math, Science)
    """
    if subjects is None:
        subjects = ["ELA", "Math", "Science"]

    # Prepare data for plotting
    rows = []
    for org_name, assessments in data.items():
        for a in assessments:
            if a.test_subject in subjects and a.grade_level == "All Grades":
                rows.append(
                    {
                        "Organization": org_name,
                        "Subject": a.test_subject,
                        "Proficiency Rate": a.proficiency_rate or 0,
                        "Suppressed": a.is_suppressed,
                    }
                )

    if not rows:
        return _empty_chart("No assessment data available")

    df = pd.DataFrame(rows)

    fig = px.bar(
        df,
        x="Subject",
        y="Proficiency Rate",
        color="Organization",
        barmode="group",
        color_discrete_sequence=ENTITY_COLORS,
        title="Achievement Comparison: Percent Meeting Standard",
    )

    # Add suppression indicators
    for i, row in df.iterrows():
        if row["Suppressed"]:
            # Add asterisk annotation for suppressed data
            fig.add_annotation(
                x=row["Subject"],
                y=row["Proficiency Rate"] + 2,
                text="*",
                showarrow=False,
                font=dict(size=16, color=COLORS["suppressed"]),
            )

    fig.update_layout(
        yaxis_title="% Meeting Standard",
        yaxis_range=[0, 100],
        legend_title="",
        hovermode="x unified",
    )

    return fig


def create_score_distribution(
    data: dict[str, list[AssessmentData]],
    subject: str = "ELA",
) -> go.Figure:
    """
    Create stacked bar chart showing score level distribution.

    Args:
        data: Dict mapping organization name to list of AssessmentData
        subject: Test subject to display
    """
    rows = []
    for org_name, assessments in data.items():
        for a in assessments:
            if a.test_subject == subject and a.grade_level == "All Grades":
                rows.append(
                    {
                        "Organization": org_name,
                        "Level 1 (Below Basic)": a.percent_level_1 or 0,
                        "Level 2 (Basic)": a.percent_level_2 or 0,
                        "Level 3 (Proficient)": a.percent_level_3 or 0,
                        "Level 4 (Advanced)": a.percent_level_4 or 0,
                        "Suppressed": a.is_suppressed,
                    }
                )

    if not rows:
        return _empty_chart(f"No {subject} score distribution data available")

    df = pd.DataFrame(rows)

    fig = go.Figure()

    levels = [
        ("Level 1 (Below Basic)", COLORS["level1"]),
        ("Level 2 (Basic)", COLORS["level2"]),
        ("Level 3 (Proficient)", COLORS["level3"]),
        ("Level 4 (Advanced)", COLORS["level4"]),
    ]

    for level_name, color in levels:
        fig.add_trace(
            go.Bar(
                name=level_name,
                x=df["Organization"],
                y=df[level_name],
                marker_color=color,
                hovertemplate="%{x}<br>%{fullData.name}: %{y:.1f}%<extra></extra>",
            )
        )

    fig.update_layout(
        barmode="stack",
        title=f"{subject} Score Distribution by Performance Level",
        yaxis_title="Percentage of Students",
        yaxis_range=[0, 100],
        legend_title="Performance Level",
        hovermode="x unified",
    )

    return fig


def create_demographics_chart(
    data: dict[str, list[DemographicData]],
    group_type: str = "Race/Ethnicity",
) -> go.Figure:
    """
    Create bar chart comparing demographic composition.

    Args:
        data: Dict mapping organization name to list of DemographicData
        group_type: Type of demographic grouping to display
    """
    rows = []
    for org_name, demographics in data.items():
        for d in demographics:
            if d.student_group_type == group_type:
                rows.append(
                    {
                        "Organization": org_name,
                        "Group": d.student_group,
                        "Percentage": d.percent_of_total or 0,
                        "Count": d.headcount or 0,
                    }
                )

    if not rows:
        return _empty_chart(f"No {group_type} demographic data available")

    df = pd.DataFrame(rows)

    fig = px.bar(
        df,
        x="Group",
        y="Percentage",
        color="Organization",
        barmode="group",
        color_discrete_sequence=ENTITY_COLORS,
        title=f"Student Demographics: {group_type}",
        hover_data=["Count"],
    )

    fig.update_layout(
        xaxis_title="",
        yaxis_title="% of Students",
        yaxis_range=[0, max(df["Percentage"].max() * 1.1, 10)],
        legend_title="",
        xaxis_tickangle=-45,
    )

    return fig


def create_program_demographics_chart(
    data: dict[str, list[DemographicData]],
) -> go.Figure:
    """
    Create bar chart comparing program participation (SPED, ELL, FRL).

    Args:
        data: Dict mapping organization name to list of DemographicData
    """
    program_groups = [
        "Students with Disabilities",
        "English Language Learners",
        "Low-Income",
    ]

    rows = []
    for org_name, demographics in data.items():
        for d in demographics:
            if d.student_group in program_groups:
                rows.append(
                    {
                        "Organization": org_name,
                        "Program": d.student_group,
                        "Percentage": d.percent_of_total or 0,
                        "Count": d.headcount or 0,
                    }
                )

    if not rows:
        return _empty_chart("No program participation data available")

    df = pd.DataFrame(rows)

    fig = px.bar(
        df,
        x="Program",
        y="Percentage",
        color="Organization",
        barmode="group",
        color_discrete_sequence=ENTITY_COLORS,
        title="Program Participation Rates",
        hover_data=["Count"],
    )

    fig.update_layout(
        xaxis_title="",
        yaxis_title="% of Students",
        legend_title="",
    )

    return fig


def create_trend_chart(
    data: dict[str, dict[str, float]],
    metric_name: str = "Proficiency Rate",
) -> go.Figure:
    """
    Create line chart showing metric trends over time.

    Args:
        data: Dict mapping organization name to dict of year -> value
        metric_name: Name of the metric being displayed
    """
    if not data:
        return _empty_chart("No trend data available")

    fig = go.Figure()

    for i, (org_name, yearly_data) in enumerate(data.items()):
        years = sorted(yearly_data.keys())
        values = [yearly_data[y] for y in years]

        fig.add_trace(
            go.Scatter(
                x=years,
                y=values,
                name=org_name,
                mode="lines+markers",
                line=dict(color=ENTITY_COLORS[i % len(ENTITY_COLORS)]),
                hovertemplate="%{x}<br>%{y:.1f}%<extra>%{fullData.name}</extra>",
            )
        )

    fig.update_layout(
        title=f"{metric_name} Trends",
        xaxis_title="School Year",
        yaxis_title=metric_name,
        legend_title="",
        hovermode="x unified",
    )

    return fig


def create_graduation_chart(
    data: dict[str, list[GraduationData]],
    cohort: str = "Four Year",
) -> go.Figure:
    """
    Create bar chart comparing graduation rates.

    Args:
        data: Dict mapping organization name to list of GraduationData
        cohort: "Four Year" or "Five Year" cohort
    """
    rows = []
    for org_name, graduation in data.items():
        for g in graduation:
            if g.cohort == cohort and g.student_group == "All Students":
                rows.append(
                    {
                        "Organization": org_name,
                        "Graduation Rate": g.graduation_rate or 0,
                        "Suppressed": g.is_suppressed,
                    }
                )

    if not rows:
        return _empty_chart(f"No {cohort} graduation data available")

    df = pd.DataFrame(rows)

    fig = px.bar(
        df,
        x="Organization",
        y="Graduation Rate",
        color="Organization",
        color_discrete_sequence=ENTITY_COLORS,
        title=f"{cohort} Adjusted Cohort Graduation Rate",
    )

    fig.update_layout(
        yaxis_title="Graduation Rate (%)",
        yaxis_range=[0, 100],
        showlegend=False,
    )

    return fig


def create_staffing_chart(
    data: dict[str, list[StaffingData]],
) -> go.Figure:
    """
    Create radar chart comparing staffing metrics.

    Args:
        data: Dict mapping organization name to list of StaffingData
    """
    # Prepare normalized data for radar chart
    metrics = ["Student-Teacher Ratio", "Avg Years Experience", "% with Masters"]

    rows = []
    for org_name, staffing in data.items():
        if staffing:
            s = staffing[0]  # Take first record
            rows.append(
                {
                    "Organization": org_name,
                    "Student-Teacher Ratio": s.student_teacher_ratio or 0,
                    "Avg Years Experience": s.avg_years_experience or 0,
                    "% with Masters": s.percent_with_masters or 0,
                }
            )

    if not rows:
        return _empty_chart("No staffing data available")

    df = pd.DataFrame(rows)

    # Create grouped bar chart (more readable than radar for comparison)
    fig = make_subplots(
        rows=1,
        cols=3,
        subplot_titles=metrics,
    )

    for i, org_name in enumerate(df["Organization"]):
        row = df[df["Organization"] == org_name].iloc[0]
        color = ENTITY_COLORS[i % len(ENTITY_COLORS)]

        for j, metric in enumerate(metrics):
            fig.add_trace(
                go.Bar(
                    x=[org_name],
                    y=[row[metric]],
                    name=org_name if j == 0 else None,
                    marker_color=color,
                    showlegend=(j == 0),
                    hovertemplate=f"{org_name}<br>{metric}: %{{y:.1f}}<extra></extra>",
                ),
                row=1,
                col=j + 1,
            )

    fig.update_layout(
        title="Staffing Comparison",
        barmode="group",
        legend_title="",
    )

    return fig


def create_spending_chart(
    data: dict[str, float],
    metric_name: str = "Per-Pupil Expenditure",
) -> go.Figure:
    """
    Create bar chart comparing spending metrics.

    Args:
        data: Dict mapping organization name to spending value
        metric_name: Name of the spending metric
    """
    if not data:
        return _empty_chart("No spending data available")

    df = pd.DataFrame(
        [{"Organization": k, metric_name: v} for k, v in data.items()]
    )

    fig = px.bar(
        df,
        x="Organization",
        y=metric_name,
        color="Organization",
        color_discrete_sequence=ENTITY_COLORS,
        title=f"{metric_name} Comparison",
    )

    fig.update_layout(
        yaxis_title=f"{metric_name} ($)",
        yaxis_tickprefix="$",
        yaxis_tickformat=",",
        showlegend=False,
    )

    return fig


def create_spending_trend_chart(
    data: dict[str, dict[str, float]],
) -> go.Figure:
    """
    Create line chart showing per-pupil expenditure trends over time.

    Args:
        data: Dict mapping organization name to dict of year -> per-pupil amount
    """
    if not data:
        return _empty_chart("No spending trend data available")

    fig = go.Figure()

    for i, (org_name, yearly_data) in enumerate(data.items()):
        years = sorted(yearly_data.keys())
        values = [yearly_data[y] for y in years]

        fig.add_trace(
            go.Scatter(
                x=years,
                y=values,
                name=org_name,
                mode="lines+markers",
                line=dict(color=ENTITY_COLORS[i % len(ENTITY_COLORS)]),
                hovertemplate="%{x}<br>$%{y:,.0f}<extra>%{fullData.name}</extra>",
            )
        )

    fig.update_layout(
        title="Per-Pupil Expenditure Trends (F-196)",
        xaxis_title="School Year",
        yaxis_title="Per-Pupil Expenditure ($)",
        yaxis_tickprefix="$",
        yaxis_tickformat=",",
        legend_title="",
        hovermode="x unified",
    )

    return fig


def create_equity_gap_chart(
    data: dict[str, dict[str, float]],
    reference_group: str = "All Students",
    subject: str = "ELA",
) -> go.Figure:
    """
    Create diverging bar chart showing equity gaps between subgroups.

    Args:
        data: Dict mapping organization name to dict of group -> proficiency
        reference_group: Group to compare against
        subject: Test subject
    """
    rows = []
    for org_name, groups in data.items():
        ref_value = groups.get(reference_group, 0)
        for group, value in groups.items():
            if group != reference_group:
                gap = value - ref_value
                rows.append(
                    {
                        "Organization": org_name,
                        "Student Group": group,
                        "Gap (pp)": gap,
                    }
                )

    if not rows:
        return _empty_chart("No equity gap data available")

    df = pd.DataFrame(rows)

    fig = px.bar(
        df,
        x="Gap (pp)",
        y="Student Group",
        color="Organization",
        orientation="h",
        barmode="group",
        color_discrete_sequence=ENTITY_COLORS,
        title=f"{subject} Achievement Gaps vs. {reference_group}",
    )

    fig.add_vline(x=0, line_dash="dash", line_color="gray")

    fig.update_layout(
        xaxis_title="Gap (percentage points)",
        yaxis_title="",
        legend_title="",
    )

    return fig


def create_spending_breakdown_chart(
    categories: list[SpendingCategory],
    district_name: str = "",
) -> go.Figure:
    """
    Create a bar chart showing spending breakdown by program category.

    Args:
        categories: List of SpendingCategory objects
        district_name: Name of the district for the title
    """
    if not categories:
        return _empty_chart("No spending category data available")

    rows = [
        {
            "Category": c.category,
            "Amount": c.amount or 0,
            "Percent": c.percent_of_total or 0,
        }
        for c in categories
    ]

    df = pd.DataFrame(rows).sort_values("Amount", ascending=True)

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=df["Amount"],
            y=df["Category"],
            orientation="h",
            marker_color=COLORS["primary"],
            text=df.apply(
                lambda r: f"${r['Amount']:,.0f} ({r['Percent']:.1f}%)", axis=1
            ),
            textposition="auto",
            hovertemplate=(
                "<b>%{y}</b><br>"
                "Amount: $%{x:,.0f}<br>"
                "<extra></extra>"
            ),
        )
    )

    title = "Spending by Program Category"
    if district_name:
        title = f"{district_name} — {title}"

    fig.update_layout(
        title=title,
        xaxis_title="Expenditure ($)",
        xaxis_tickprefix="$",
        xaxis_tickformat=",",
        yaxis_title="",
        height=max(400, len(rows) * 40 + 100),
        margin=dict(l=200),
    )

    return fig


def create_correlation_scatter(
    df: pd.DataFrame,
    x_metric: str,
    y_metric: str,
    x_label: str,
    y_label: str,
    highlight_districts: Optional[list[str]] = None,
    x_format: str = "{}",
    y_format: str = "{}",
    entity_name_col: str = "district_name",
    entity_code_col: str = "district_code",
) -> go.Figure:
    """
    Create scatter plot for correlating two metrics across entities.

    Args:
        df: DataFrame with entity code, entity name, enrollment, and metric columns
        x_metric: Column name for x-axis metric
        y_metric: Column name for y-axis metric
        x_label: Display label for x-axis
        y_label: Display label for y-axis
        highlight_districts: List of entity codes to highlight
        x_format: Format string for x-axis values in tooltip
        y_format: Format string for y-axis values in tooltip
        entity_name_col: Column name for entity display names
        entity_code_col: Column name for entity codes (used for highlighting)
    """
    # Filter to rows with both metrics present
    required_cols = [entity_code_col, entity_name_col, x_metric, y_metric]
    if "enrollment" in df.columns:
        required_cols.append("enrollment")
    plot_df = df[required_cols].dropna(subset=[x_metric, y_metric]).copy()

    # Ensure enrollment column exists for tooltip
    if "enrollment" not in plot_df.columns:
        plot_df["enrollment"] = None

    if plot_df.empty:
        return _empty_chart("No data available for selected metrics")

    # Create highlight column
    if highlight_districts:
        plot_df["highlighted"] = plot_df[entity_code_col].isin(highlight_districts)
    else:
        plot_df["highlighted"] = False

    # Format tooltip values
    def format_val(val, fmt):
        try:
            return fmt.format(val)
        except Exception:
            return str(val)

    plot_df["x_display"] = plot_df[x_metric].apply(lambda v: format_val(v, x_format))
    plot_df["y_display"] = plot_df[y_metric].apply(lambda v: format_val(v, y_format))

    # Create figure
    fig = go.Figure()

    # Determine trace name based on entity type
    trace_name = "Schools" if entity_name_col == "school_name" else "Districts"

    # Non-highlighted points
    non_highlight = plot_df[~plot_df["highlighted"]]
    if not non_highlight.empty:
        fig.add_trace(go.Scatter(
            x=non_highlight[x_metric],
            y=non_highlight[y_metric],
            mode="markers",
            marker=dict(
                size=8,
                color=COLORS["primary"],
                opacity=0.5,
            ),
            text=non_highlight[entity_name_col],
            customdata=non_highlight[["enrollment", "x_display", "y_display"]].values,
            hovertemplate=(
                "<b>%{text}</b><br>"
                f"{x_label}: %{{customdata[1]}}<br>"
                f"{y_label}: %{{customdata[2]}}<br>"
                "Enrollment: %{customdata[0]:,}<extra></extra>"
            ),
            name=trace_name,
        ))

    # Highlighted points
    highlight = plot_df[plot_df["highlighted"]]
    if not highlight.empty:
        fig.add_trace(go.Scatter(
            x=highlight[x_metric],
            y=highlight[y_metric],
            mode="markers+text",
            marker=dict(
                size=14,
                color=COLORS["warning"],
                line=dict(width=2, color="white"),
            ),
            text=highlight[entity_name_col],
            textposition="top center",
            customdata=highlight[["enrollment", "x_display", "y_display"]].values,
            hovertemplate=(
                "<b>%{text}</b><br>"
                f"{x_label}: %{{customdata[1]}}<br>"
                f"{y_label}: %{{customdata[2]}}<br>"
                "Enrollment: %{customdata[0]:,}<extra></extra>"
            ),
            name="Highlighted",
        ))

    # Add trendline
    if len(plot_df) > 2:
        import numpy as np
        x_vals = plot_df[x_metric].values
        y_vals = plot_df[y_metric].values
        z = np.polyfit(x_vals, y_vals, 1)
        p = np.poly1d(z)
        x_line = np.linspace(x_vals.min(), x_vals.max(), 100)

        # Calculate R-squared
        y_pred = p(x_vals)
        ss_res = np.sum((y_vals - y_pred) ** 2)
        ss_tot = np.sum((y_vals - np.mean(y_vals)) ** 2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0

        fig.add_trace(go.Scatter(
            x=x_line,
            y=p(x_line),
            mode="lines",
            line=dict(color="gray", dash="dash", width=1),
            name=f"Trend (R²={r_squared:.3f})",
            hoverinfo="skip",
        ))

    fig.update_layout(
        title=f"{y_label} vs {x_label}",
        xaxis_title=x_label,
        yaxis_title=y_label,
        hovermode="closest",
        legend=dict(
            yanchor="top",
            y=0.99,
            xanchor="left",
            x=0.01,
        ),
        height=600,
    )

    # Format axes based on metric type
    if "$" in x_format:
        fig.update_xaxes(tickprefix="$", tickformat=",")
    if "$" in y_format:
        fig.update_yaxes(tickprefix="$", tickformat=",")
    if "%" in x_format:
        fig.update_xaxes(ticksuffix="%")
    if "%" in y_format:
        fig.update_yaxes(ticksuffix="%")

    return fig


def _empty_chart(message: str) -> go.Figure:
    """Create an empty chart with a message."""
    fig = go.Figure()
    fig.add_annotation(
        text=message,
        xref="paper",
        yref="paper",
        x=0.5,
        y=0.5,
        showarrow=False,
        font=dict(size=16, color="gray"),
    )
    fig.update_layout(
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        height=300,
    )
    return fig


def add_suppression_footnote() -> str:
    """Return footnote text for suppressed data."""
    return "\\* Data suppressed to protect student privacy (n<10)"
