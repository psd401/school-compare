"""Correlation analysis page for exploring relationships between metrics."""

import streamlit as st

from src.data.combined import (
    get_all_district_data,
    get_metric_label,
    get_metric_format,
    METRICS,
)
from src.viz.charts import create_correlation_scatter


st.set_page_config(
    page_title="Correlations | WA School Compare",
    page_icon="📊",
    layout="wide",
)

st.title("📊 Metric Correlations")
st.markdown(
    "Explore relationships between district-level metrics. "
    "Select metrics for each axis and optionally highlight specific districts."
)

# Load district data
with st.spinner("Loading district data..."):
    df = get_all_district_data()

if df.empty:
    st.error("No district data available. Please check data sources.")
    st.stop()

# Group metrics by category for better UX
categories = {}
for key, info in METRICS.items():
    cat = info["category"]
    if cat not in categories:
        categories[cat] = []
    categories[cat].append((key, info["label"]))

# Build options list with category headers
def get_metric_options():
    options = []
    for cat in ["Spending", "Achievement", "Graduation", "Demographics", "Staffing", "Size"]:
        if cat in categories:
            for key, label in categories[cat]:
                options.append(key)
    return options

metric_options = get_metric_options()

# Sidebar controls
st.sidebar.header("Chart Configuration")

# X-axis metric
x_metric = st.sidebar.selectbox(
    "X-Axis Metric",
    options=metric_options,
    format_func=get_metric_label,
    index=metric_options.index("per_pupil_expenditure") if "per_pupil_expenditure" in metric_options else 0,
)

# Y-axis metric
y_metric = st.sidebar.selectbox(
    "Y-Axis Metric",
    options=metric_options,
    format_func=get_metric_label,
    index=metric_options.index("ela_proficiency") if "ela_proficiency" in metric_options else 1,
)

# District highlight filter
st.sidebar.header("Highlight Districts")

# Get list of districts for multiselect
districts = df[["district_code", "district_name"]].drop_duplicates().sort_values("district_name")
district_options = districts["district_code"].tolist()
district_names = dict(zip(districts["district_code"], districts["district_name"]))

highlight_districts = st.sidebar.multiselect(
    "Select districts to highlight",
    options=district_options,
    format_func=lambda x: district_names.get(x, x),
    max_selections=10,
)

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
    highlight_districts=highlight_districts if highlight_districts else None,
    x_format=x_format,
    y_format=y_format,
)

st.plotly_chart(fig, use_container_width=True)

# Data summary
col1, col2, col3 = st.columns(3)

valid_data = df[[x_metric, y_metric]].dropna()

with col1:
    st.metric("Districts with Data", len(valid_data))

with col2:
    if not valid_data.empty:
        corr = valid_data[x_metric].corr(valid_data[y_metric])
        st.metric("Correlation (r)", f"{corr:.3f}")

with col3:
    if highlight_districts:
        st.metric("Highlighted", len(highlight_districts))

# Interpretation guidance
with st.expander("Understanding the Chart"):
    st.markdown("""
    **Reading the scatter plot:**
    - Each point represents a Washington school district
    - Hover over points to see district details
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
st.caption(
    "Data sources: Assessment, demographics, graduation, staffing from WA Report Card via data.wa.gov. "
    "Spending from OSPI F-196 Financial Reports. District-level data only."
)
