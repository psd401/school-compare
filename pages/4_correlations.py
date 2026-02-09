"""Correlation analysis page for exploring relationships between metrics."""

import pandas as pd
import streamlit as st

from src.data.combined import (
    get_all_district_data,
    get_all_school_data,
    get_metric_label,
    get_metric_format,
    METRICS,
    SCHOOL_METRICS,
)
from src.viz.charts import create_correlation_scatter


st.set_page_config(
    page_title="Correlations | WA School Compare",
    page_icon="📊",
    layout="wide",
)

st.title("📊 Metric Correlations")
st.markdown(
    "Explore relationships between metrics. "
    "Select metrics for each axis and optionally highlight specific entities."
)

# Analysis level toggle
analysis_level = st.radio(
    "Analysis Level",
    options=["District", "School"],
    horizontal=True,
    help="District includes all 12 metrics (including spending & graduation). "
    "School includes 10 metrics (excludes spending & graduation which are district-only).",
)

is_school = analysis_level == "School"
active_metrics = SCHOOL_METRICS if is_school else METRICS

# Load data based on level
if is_school:
    with st.status("Loading school data...", expanded=True) as status:
        df = get_all_school_data()
        status.update(label="School data loaded!", state="complete", expanded=False)
    entity_name_col = "school_name"
    entity_code_col = "school_code"
else:
    with st.status("Loading district data...", expanded=True) as status:
        df = get_all_district_data()
        status.update(label="District data loaded!", state="complete", expanded=False)
    entity_name_col = "district_name"
    entity_code_col = "district_code"

if df.empty:
    st.error(f"No {analysis_level.lower()} data available. Please check data sources.")
    st.stop()

# Group metrics by category for better UX
categories = {}
for key, info in active_metrics.items():
    cat = info["category"]
    if cat not in categories:
        categories[cat] = []
    categories[cat].append((key, info["label"]))

# Build options list with category headers
def get_metric_options():
    options = []
    cat_order = ["Spending", "Achievement", "Graduation", "Demographics", "Staffing", "Size"]
    for cat in cat_order:
        if cat in categories:
            for key, label in categories[cat]:
                options.append(key)
    return options

metric_options = get_metric_options()

# Default selections
default_x = "per_pupil_expenditure" if not is_school else "pct_low_income"
default_y = "ela_proficiency"

# Initialize session state for metric selection (used by suggested analysis buttons)
if "x_metric" not in st.session_state:
    st.session_state.x_metric = default_x
if "y_metric" not in st.session_state:
    st.session_state.y_metric = default_y

# Ensure session state values are valid for current metric options
if st.session_state.x_metric not in metric_options:
    st.session_state.x_metric = metric_options[0]
if st.session_state.y_metric not in metric_options:
    st.session_state.y_metric = metric_options[1] if len(metric_options) > 1 else metric_options[0]

# Sidebar controls
st.sidebar.header("Chart Configuration")

# X-axis metric
x_metric = st.sidebar.selectbox(
    "X-Axis Metric",
    options=metric_options,
    format_func=get_metric_label,
    key="x_metric",
)

# Y-axis metric
y_metric = st.sidebar.selectbox(
    "Y-Axis Metric",
    options=metric_options,
    format_func=get_metric_label,
    key="y_metric",
)

# ---- Filters ----
st.sidebar.header("Filters")

total_count = len(df)
filtered_df = df.copy()

# ESD filter
esd_options = sorted(df["esdname"].dropna().unique().tolist()) if "esdname" in df.columns else []
selected_esds = st.sidebar.multiselect("ESD", options=esd_options)
if selected_esds:
    filtered_df = filtered_df[filtered_df["esdname"].isin(selected_esds)]

# County filter (cascaded from ESD selection)
county_options = sorted(filtered_df["county"].dropna().unique().tolist()) if "county" in filtered_df.columns else []
selected_counties = st.sidebar.multiselect("County", options=county_options)
if selected_counties:
    filtered_df = filtered_df[filtered_df["county"].isin(selected_counties)]

# Enrollment filter
if "enrollment" in filtered_df.columns:
    enroll_min = int(df["enrollment"].min(skipna=True)) if df["enrollment"].notna().any() else 0
    enroll_max = int(df["enrollment"].max(skipna=True)) if df["enrollment"].notna().any() else 0
    col_min, col_max = st.sidebar.columns(2)
    with col_min:
        enrollment_lo = st.number_input("Enrollment min", min_value=enroll_min, max_value=enroll_max, value=enroll_min)
    with col_max:
        enrollment_hi = st.number_input("Enrollment max", min_value=enroll_min, max_value=enroll_max, value=enroll_max)
    filtered_df = filtered_df[
        ((filtered_df["enrollment"] >= enrollment_lo) & (filtered_df["enrollment"] <= enrollment_hi))
        | filtered_df["enrollment"].isna()
    ]

# District filter (school view only)
if is_school:
    dist_opts = (
        filtered_df[["district_code", "district_name"]]
        .drop_duplicates()
        .sort_values("district_name")
    )
    dist_codes = dist_opts["district_code"].tolist()
    dist_names = dict(zip(dist_opts["district_code"], dist_opts["district_name"]))
    selected_districts = st.sidebar.multiselect(
        "District",
        options=dist_codes,
        format_func=lambda x: dist_names.get(x, x),
    )
    if selected_districts:
        filtered_df = filtered_df[filtered_df["district_code"].isin(selected_districts)]

# ---- Highlight ----
st.sidebar.header(f"Highlight {analysis_level}s")

if is_school:
    # For school view: highlight by district
    districts = filtered_df[["district_code", "district_name"]].drop_duplicates().sort_values("district_name")
    district_options = districts["district_code"].tolist()
    district_names = dict(zip(districts["district_code"], districts["district_name"]))

    highlight_district = st.sidebar.selectbox(
        "Highlight schools from district:",
        options=[""] + district_options,
        format_func=lambda x: "None" if x == "" else district_names.get(x, x),
    )

    # Schools in the selected district become highlighted
    if highlight_district:
        highlight_codes = filtered_df.loc[
            filtered_df["district_code"] == highlight_district, "school_code"
        ].tolist()
    else:
        highlight_codes = None
else:
    # For district view: multi-select districts
    districts = filtered_df[["district_code", "district_name"]].drop_duplicates().sort_values("district_name")
    district_options = districts["district_code"].tolist()
    district_names = dict(zip(districts["district_code"], districts["district_name"]))

    highlight_codes = st.sidebar.multiselect(
        "Select districts to highlight",
        options=district_options,
        format_func=lambda x: district_names.get(x, x),
        max_selections=10,
    )
    highlight_codes = highlight_codes if highlight_codes else None

# Create and display chart
x_label = get_metric_label(x_metric)
y_label = get_metric_label(y_metric)
x_format = get_metric_format(x_metric)
y_format = get_metric_format(y_metric)

fig = create_correlation_scatter(
    df=filtered_df,
    x_metric=x_metric,
    y_metric=y_metric,
    x_label=x_label,
    y_label=y_label,
    highlight_districts=highlight_codes,
    x_format=x_format,
    y_format=y_format,
    entity_name_col=entity_name_col,
    entity_code_col=entity_code_col,
)

st.plotly_chart(fig, width="stretch")
st.caption("*Hover over chart and click the camera icon to download as PNG*")

# CSV export
st.download_button(
    "Download filtered data (CSV)",
    filtered_df.to_csv(index=False),
    file_name=f"correlations_{analysis_level.lower()}_{x_metric}_vs_{y_metric}.csv",
    mime="text/csv",
)

# Data summary
col1, col2, col3 = st.columns(3)

# Guard against missing metric columns (API data may not have loaded)
if x_metric in filtered_df.columns and y_metric in filtered_df.columns:
    valid_data = filtered_df[[x_metric, y_metric]].dropna()
else:
    valid_data = pd.DataFrame()

filtered_count = len(valid_data)
is_filtered = filtered_count < total_count
count_label = f"{filtered_count} / {total_count}" if is_filtered else str(filtered_count)

with col1:
    st.metric(f"{analysis_level}s with Data", count_label)

with col2:
    if not valid_data.empty:
        corr = valid_data[x_metric].corr(valid_data[y_metric])
        st.metric("Correlation (r)", f"{corr:.3f}")

with col3:
    if highlight_codes:
        st.metric("Highlighted", len(highlight_codes))

# Interpretation guidance
with st.expander("Understanding the Chart"):
    entity = "school" if is_school else "district"
    st.markdown(f"""
    **Reading the scatter plot:**
    - Each point represents a Washington {entity}
    - Hover over points to see details
    - The dashed line shows the overall trend (linear regression)
    - R² indicates how well the trend line fits the data (0-1, higher = stronger relationship)

    **Correlation values:**
    - **r near 0**: Little or no relationship
    - **r near 0.3**: Weak relationship
    - **r near 0.5**: Moderate relationship
    - **r near 0.7+**: Strong relationship
    - **Positive r**: Metrics increase together
    - **Negative r**: One increases as other decreases

    **Note:** Correlation does not imply causation. Many factors influence educational outcomes.
    """)

# Suggested analyses
st.markdown("#### Suggested Analyses")
st.caption("Click a button to load a pre-configured metric pairing.")

SUGGESTED_ANALYSES = [
    ("per_pupil_expenditure", "ela_proficiency", "Spending vs ELA", "Resource impact on achievement"),
    ("pct_low_income", "math_proficiency", "Poverty vs Math", "Poverty/achievement relationship"),
    ("teacher_experience", "ela_proficiency", "Experience vs ELA", "Staff quality impact"),
    ("pct_ell", "science_proficiency", "ELL vs Science", "Language barrier effects"),
    ("student_teacher_ratio", "math_proficiency", "Class Size vs Math", "Class size impact"),
]

suggestion_cols = st.columns(len(SUGGESTED_ANALYSES))
for idx, (sx, sy, label, rationale) in enumerate(SUGGESTED_ANALYSES):
    with suggestion_cols[idx]:
        # Only show if both metrics are available at current analysis level
        if sx in metric_options and sy in metric_options:
            if st.button(label, key=f"suggest_{idx}", help=rationale):
                st.session_state.x_metric = sx
                st.session_state.y_metric = sy
                st.rerun()

# Data source note
if is_school:
    st.caption(
        "Data sources: Assessment, demographics, staffing from WA Report Card via data.wa.gov. "
        "School-level data. Spending and graduation data are only available at the district level."
    )
else:
    st.caption(
        "Data sources: Assessment, demographics, graduation, staffing from WA Report Card via data.wa.gov. "
        "Spending from OSPI F-196 Financial Reports. District-level data only."
    )
