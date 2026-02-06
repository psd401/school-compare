"""Correlation analysis page for exploring relationships between metrics."""

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
    with st.spinner("Loading school data..."):
        df = get_all_school_data()
    entity_name_col = "school_name"
    entity_code_col = "school_code"
else:
    with st.spinner("Loading district data..."):
        df = get_all_district_data()
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

# Sidebar controls
st.sidebar.header("Chart Configuration")

# X-axis metric
x_metric = st.sidebar.selectbox(
    "X-Axis Metric",
    options=metric_options,
    format_func=get_metric_label,
    index=metric_options.index(default_x) if default_x in metric_options else 0,
)

# Y-axis metric
y_metric = st.sidebar.selectbox(
    "Y-Axis Metric",
    options=metric_options,
    format_func=get_metric_label,
    index=metric_options.index(default_y) if default_y in metric_options else 1,
)

# Highlight filter
st.sidebar.header(f"Highlight {analysis_level}s")

if is_school:
    # For school view: highlight by district
    districts = df[["district_code", "district_name"]].drop_duplicates().sort_values("district_name")
    district_options = districts["district_code"].tolist()
    district_names = dict(zip(districts["district_code"], districts["district_name"]))

    highlight_district = st.sidebar.selectbox(
        "Highlight schools from district:",
        options=[""] + district_options,
        format_func=lambda x: "None" if x == "" else district_names.get(x, x),
    )

    # Schools in the selected district become highlighted
    if highlight_district:
        highlight_codes = df.loc[
            df["district_code"] == highlight_district, "school_code"
        ].tolist()
    else:
        highlight_codes = None
else:
    # For district view: multi-select districts
    districts = df[["district_code", "district_name"]].drop_duplicates().sort_values("district_name")
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
    df=df,
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

# Data summary
col1, col2, col3 = st.columns(3)

valid_data = df[[x_metric, y_metric]].dropna()

with col1:
    st.metric(f"{analysis_level}s with Data", len(valid_data))

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
