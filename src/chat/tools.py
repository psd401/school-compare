"""Tool definitions for Gemini function calling."""

from typing import Any
from google.genai import types

from src.data.client import get_client

# Tool schemas (generic format)
TOOL_SCHEMAS = [
    {
        "name": "search_schools",
        "description": "Search for Washington state public schools by name. Returns matching schools with their districts and locations.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query for school name (partial match supported)",
                }
            },
            "required": ["query"],
        },
    },
    {
        "name": "search_districts",
        "description": "Search for Washington state school districts by name. Returns matching districts with their locations.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query for district name (partial match supported)",
                }
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_assessment_data",
        "description": "Get state assessment results (SBA ELA, SBA Math, WCAS Science) for a school or district. Returns proficiency rates and score level distributions.",
        "input_schema": {
            "type": "object",
            "properties": {
                "organization_id": {
                    "type": "string",
                    "description": "The school code or district code to get data for",
                },
                "organization_type": {
                    "type": "string",
                    "enum": ["School", "District"],
                    "description": "Whether the ID is for a school or district",
                },
                "school_year": {
                    "type": "string",
                    "description": "School year in format YYYY-YY (e.g., 2023-24)",
                    "default": "2023-24",
                },
                "subject": {
                    "type": "string",
                    "enum": ["ELA", "Math", "Science"],
                    "description": "Test subject to get data for. If not specified, returns all subjects.",
                },
                "student_group": {
                    "type": "string",
                    "description": "Student subgroup (e.g., 'All Students', 'Low-Income', 'English Language Learners', 'Students with Disabilities', 'Hispanic/Latino of any race(s)', 'Black/African American', 'Asian', 'White'). Defaults to 'All Students'.",
                    "default": "All Students",
                },
                "grade_level": {
                    "type": "string",
                    "description": "Grade level (e.g., 'All Grades', '3rd Grade', '4th Grade', '5th Grade', '6th Grade', '7th Grade', '8th Grade', '10th Grade', '11th Grade'). Defaults to 'All Grades'.",
                    "default": "All Grades",
                },
            },
            "required": ["organization_id", "organization_type"],
        },
    },
    {
        "name": "get_demographics",
        "description": "Get student enrollment demographics for a school or district. Returns breakdowns by race/ethnicity and program participation (Special Education, English Language Learners, Low-Income).",
        "input_schema": {
            "type": "object",
            "properties": {
                "organization_id": {
                    "type": "string",
                    "description": "The school code or district code to get data for",
                },
                "organization_type": {
                    "type": "string",
                    "enum": ["School", "District"],
                    "description": "Whether the ID is for a school or district",
                },
                "school_year": {
                    "type": "string",
                    "description": "School year in format YYYY-YY (e.g., 2024-25)",
                    "default": "2024-25",
                },
            },
            "required": ["organization_id", "organization_type"],
        },
    },
    {
        "name": "get_graduation_data",
        "description": "Get graduation rates for a school or district. Returns four-year and five-year adjusted cohort graduation rates.",
        "input_schema": {
            "type": "object",
            "properties": {
                "organization_id": {
                    "type": "string",
                    "description": "The school code or district code to get data for",
                },
                "organization_type": {
                    "type": "string",
                    "enum": ["School", "District"],
                    "description": "Whether the ID is for a school or district",
                },
                "school_year": {
                    "type": "string",
                    "description": "School year in format YYYY-YY (e.g., 2023-24)",
                    "default": "2023-24",
                },
            },
            "required": ["organization_id", "organization_type"],
        },
    },
    {
        "name": "get_staffing_data",
        "description": "Get teacher and staffing information for a school or district. Returns teacher count, average years of experience, percent with masters degrees, and student-teacher ratio.",
        "input_schema": {
            "type": "object",
            "properties": {
                "organization_id": {
                    "type": "string",
                    "description": "The school code or district code to get data for",
                },
                "organization_type": {
                    "type": "string",
                    "enum": ["School", "District"],
                    "description": "Whether the ID is for a school or district",
                },
                "school_year": {
                    "type": "string",
                    "description": "School year in format YYYY-YY (e.g., 2023-24)",
                    "default": "2023-24",
                },
            },
            "required": ["organization_id", "organization_type"],
        },
    },
    {
        "name": "get_spending_data",
        "description": "Get per-pupil expenditure and financial data for a school district. Returns per-pupil spending, total expenditure, and enrollment from F-196 reports. NOTE: Spending data is only available at the DISTRICT level, not for individual schools.",
        "input_schema": {
            "type": "object",
            "properties": {
                "district_code": {
                    "type": "string",
                    "description": "The district code to get spending data for (e.g., '17001' for Seattle)",
                },
                "school_year": {
                    "type": "string",
                    "description": "School year in short format YY-YY (e.g., '24-25' or '23-24'). Available years: 14-15 through 24-25.",
                    "default": "24-25",
                },
                "include_trend": {
                    "type": "boolean",
                    "description": "If true, include 10-year spending trend data",
                    "default": False,
                },
                "include_categories": {
                    "type": "boolean",
                    "description": "If true, include spending breakdown by program category (e.g., Basic Education, Special Education, CTE, etc.)",
                    "default": False,
                },
            },
            "required": ["district_code"],
        },
    },
    {
        "name": "analyze_correlation",
        "description": "Analyze the correlation between two district-level metrics across all Washington districts. Returns correlation statistics and top/bottom districts. Useful for questions like 'Is there a relationship between spending and test scores?'",
        "input_schema": {
            "type": "object",
            "properties": {
                "x_metric": {
                    "type": "string",
                    "enum": [
                        "per_pupil_expenditure",
                        "ela_proficiency",
                        "math_proficiency",
                        "science_proficiency",
                        "graduation_rate_4yr",
                        "pct_low_income",
                        "pct_ell",
                        "pct_sped",
                        "teacher_experience",
                        "pct_teachers_masters",
                        "student_teacher_ratio",
                        "enrollment",
                        "pct_spending_basic_ed",
                        "pct_spending_sped",
                        "pct_spending_cte",
                        "pct_spending_compensatory",
                        "pct_spending_support",
                        "pct_spending_transportation",
                        "pct_spending_food",
                    ],
                    "description": "Metric for the x-axis (independent variable)",
                },
                "y_metric": {
                    "type": "string",
                    "enum": [
                        "per_pupil_expenditure",
                        "ela_proficiency",
                        "math_proficiency",
                        "science_proficiency",
                        "graduation_rate_4yr",
                        "pct_low_income",
                        "pct_ell",
                        "pct_sped",
                        "teacher_experience",
                        "pct_teachers_masters",
                        "student_teacher_ratio",
                        "enrollment",
                        "pct_spending_basic_ed",
                        "pct_spending_sped",
                        "pct_spending_cte",
                        "pct_spending_compensatory",
                        "pct_spending_support",
                        "pct_spending_transportation",
                        "pct_spending_food",
                    ],
                    "description": "Metric for the y-axis (dependent variable)",
                },
                "highlight_district": {
                    "type": "string",
                    "description": "Optional district code to highlight in the analysis",
                },
            },
            "required": ["x_metric", "y_metric"],
        },
    },
]


def execute_tool(tool_name: str, tool_input: dict[str, Any]) -> str:
    """Execute a tool and return the result as a string."""
    client = get_client()

    if tool_name == "search_schools":
        results = client.search_schools(tool_input["query"], limit=10)
        if not results:
            return "No schools found matching that query."

        output = f"Found {len(results)} schools:\n\n"
        for s in results:
            output += f"- **{s.school_name}** (Code: {s.school_code})\n"
            output += f"  District: {s.district_name}, County: {s.county}\n\n"
        return output

    elif tool_name == "search_districts":
        results = client.search_districts(tool_input["query"], limit=10)
        if not results:
            return "No districts found matching that query."

        output = f"Found {len(results)} districts:\n\n"
        for d in results:
            output += f"- **{d.district_name}** (Code: {d.district_code})\n"
            output += f"  County: {d.county}, ESD: {d.esd_name}\n\n"
        return output

    elif tool_name == "get_assessment_data":
        org_id = tool_input["organization_id"]
        org_type = tool_input["organization_type"]
        year = tool_input.get("school_year", "2023-24")
        subject = tool_input.get("subject")
        student_group = tool_input.get("student_group", "All Students")
        grade_level = tool_input.get("grade_level", "All Grades")

        results = client.get_assessment_data(
            organization_id=org_id,
            organization_level=org_type,
            school_year=year,
            test_subject=subject,
            student_group=student_group,
            grade_level=grade_level,
        )

        if not results:
            return f"No assessment data found for {org_type} {org_id} in {year}."

        output = f"**Assessment Data for {year}**\n\n"
        for a in results:
            suppressed = " (suppressed*)" if a.is_suppressed else ""
            output += f"**{a.test_subject}**{suppressed}\n"
            if a.proficiency_rate is not None:
                output += f"- Proficiency Rate: {a.proficiency_rate:.1f}%\n"
            if a.count_expected:
                output += f"- Students Tested: {a.count_expected:,}\n"
            if a.percent_level_1 is not None:
                output += f"- Level 1 (Below Basic): {a.percent_level_1:.1f}%\n"
                output += f"- Level 2 (Basic): {a.percent_level_2:.1f}%\n"
                output += f"- Level 3 (Proficient): {a.percent_level_3:.1f}%\n"
                output += f"- Level 4 (Advanced): {a.percent_level_4:.1f}%\n"
            output += "\n"

        if any(a.is_suppressed for a in results):
            output += "\n*Data suppressed to protect student privacy (n<10)"

        return output

    elif tool_name == "get_demographics":
        org_id = tool_input["organization_id"]
        org_type = tool_input["organization_type"]
        year = tool_input.get("school_year", "2024-25")

        results = client.get_demographics(
            organization_id=org_id,
            organization_level=org_type,
            school_year=year,
        )

        if not results:
            return f"No demographic data found for {org_type} {org_id} in {year}."

        output = f"**Demographics for {year}**\n\n"

        # Group by type
        race_ethnicity = [d for d in results if d.student_group_type == "Race/Ethnicity"]
        programs = [d for d in results if d.student_group_type == "Program"]

        if race_ethnicity:
            output += "**Race/Ethnicity:**\n"
            for d in race_ethnicity:
                pct = f"{d.percent_of_total:.1f}%" if d.percent_of_total else "N/A"
                count = f" ({d.headcount:,} students)" if d.headcount else ""
                output += f"- {d.student_group}: {pct}{count}\n"
            output += "\n"

        if programs:
            output += "**Program Participation:**\n"
            for d in programs:
                if d.student_group in ["Students with Disabilities", "English Language Learners", "Low-Income"]:
                    pct = f"{d.percent_of_total:.1f}%" if d.percent_of_total else "N/A"
                    count = f" ({d.headcount:,} students)" if d.headcount else ""
                    output += f"- {d.student_group}: {pct}{count}\n"

        return output

    elif tool_name == "get_graduation_data":
        org_id = tool_input["organization_id"]
        org_type = tool_input["organization_type"]
        year = tool_input.get("school_year", "2023-24")

        results = client.get_graduation_data(
            organization_id=org_id,
            organization_level=org_type,
            school_year=year,
        )

        if not results:
            return f"No graduation data found for {org_type} {org_id} in {year}."

        output = f"**Graduation Rates for {year}**\n\n"
        for g in results:
            if g.student_group == "All Students":
                suppressed = " (suppressed*)" if g.is_suppressed else ""
                rate = f"{g.graduation_rate:.1f}%" if g.graduation_rate else "N/A"
                output += f"- {g.cohort} Cohort: {rate}{suppressed}\n"

        if any(g.is_suppressed for g in results):
            output += "\n*Data suppressed to protect student privacy (n<10)"

        return output

    elif tool_name == "get_staffing_data":
        org_id = tool_input["organization_id"]
        org_type = tool_input["organization_type"]
        year = tool_input.get("school_year", "2023-24")

        results = client.get_staffing_data(
            organization_id=org_id,
            organization_level=org_type,
            school_year=year,
        )

        if not results:
            return f"No staffing data found for {org_type} {org_id} in {year}."

        s = results[0]
        output = f"**Staffing Data for {year}**\n\n"
        output += f"- Teacher Count: {s.teacher_count or 'N/A'}\n"
        output += f"- Average Years Experience: {f'{s.avg_years_experience:.1f}' if s.avg_years_experience else 'N/A'}\n"
        output += f"- Percent with Masters: {f'{s.percent_with_masters:.1f}%' if s.percent_with_masters else 'N/A'}\n"
        output += f"- Student-Teacher Ratio: {f'{s.student_teacher_ratio:.1f}:1' if s.student_teacher_ratio else 'N/A'}\n"

        return output

    elif tool_name == "get_spending_data":
        district_code = tool_input["district_code"]
        year = tool_input.get("school_year", "24-25")
        include_trend = tool_input.get("include_trend", False)

        spending = client.get_spending_data(district_code, year)

        if not spending:
            return f"No spending data found for district {district_code} in 20{year}. Note: Spending data is only available at the district level (not individual schools) from F-196 financial reports."

        output = f"**Per-Pupil Expenditure for 20{year}**\n\n"
        output += f"- District: {spending.district_name}\n"
        output += f"- Per-Pupil Expenditure: ${spending.per_pupil_expenditure:,.0f}\n" if spending.per_pupil_expenditure else "- Per-Pupil Expenditure: N/A\n"
        output += f"- Total Expenditure: ${spending.total_expenditure:,.0f}\n" if spending.total_expenditure else "- Total Expenditure: N/A\n"
        output += f"- Enrollment: {spending.enrollment:,} students\n" if spending.enrollment else "- Enrollment: N/A\n"

        if include_trend:
            trend = client.get_spending_trend(district_code)
            if trend:
                output += "\n**10-Year Spending Trend (Per-Pupil):**\n"
                for yr, amount in sorted(trend.items()):
                    output += f"- 20{yr}: ${amount:,.0f}\n"

        include_categories = tool_input.get("include_categories", False)
        if include_categories:
            categories = client.get_spending_by_category(district_code)
            if categories:
                output += "\n**Spending by Program Category:**\n"
                for cat in categories:
                    amt = f"${cat.amount:,.0f}" if cat.amount else "N/A"
                    pct = f" ({cat.percent_of_total:.1f}%)" if cat.percent_of_total else ""
                    output += f"- {cat.category}: {amt}{pct}\n"

        output += "\n*Source: OSPI F-196 Financial Reporting Data*"
        return output

    elif tool_name == "analyze_correlation":
        from src.data.combined import get_all_district_data, get_metric_label, format_metric_value
        import numpy as np

        x_metric = tool_input["x_metric"]
        y_metric = tool_input["y_metric"]
        highlight_code = tool_input.get("highlight_district")

        df = get_all_district_data()
        if df.empty:
            return "No district data available for correlation analysis."

        # Filter to rows with both metrics
        valid = df[["district_code", "district_name", x_metric, y_metric, "enrollment"]].dropna(subset=[x_metric, y_metric])

        if len(valid) < 3:
            return f"Not enough districts with both {get_metric_label(x_metric)} and {get_metric_label(y_metric)} data for correlation analysis."

        # Calculate correlation
        x_vals = valid[x_metric].astype(float).values
        y_vals = valid[y_metric].astype(float).values
        corr = np.corrcoef(x_vals, y_vals)[0, 1]

        # Linear regression for R²
        z = np.polyfit(x_vals, y_vals, 1)
        p = np.poly1d(z)
        y_pred = p(x_vals)
        ss_res = np.sum((y_vals - y_pred) ** 2)
        ss_tot = np.sum((y_vals - np.mean(y_vals)) ** 2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0

        x_label = get_metric_label(x_metric)
        y_label = get_metric_label(y_metric)

        output = f"**Correlation Analysis: {y_label} vs {x_label}**\n\n"
        output += f"- Districts analyzed: {len(valid)}\n"
        output += f"- Correlation (r): {corr:.3f}\n"
        output += f"- R-squared: {r_squared:.3f}\n\n"

        # Interpret correlation
        abs_corr = abs(corr)
        if abs_corr < 0.1:
            strength = "negligible"
        elif abs_corr < 0.3:
            strength = "weak"
        elif abs_corr < 0.5:
            strength = "moderate"
        elif abs_corr < 0.7:
            strength = "moderately strong"
        else:
            strength = "strong"

        direction = "positive" if corr > 0 else "negative"
        output += f"**Interpretation:** There is a {strength} {direction} correlation between {x_label.lower()} and {y_label.lower()}.\n\n"

        # Top 5 by y-metric
        top5 = valid.nlargest(5, y_metric)
        output += f"**Top 5 districts by {y_label}:**\n"
        for _, row in top5.iterrows():
            y_val = format_metric_value(y_metric, row[y_metric])
            x_val = format_metric_value(x_metric, row[x_metric])
            output += f"- {row['district_name']}: {y_val}, {x_val}\n"

        # Highlight specific district if requested
        if highlight_code:
            highlighted = valid[valid["district_code"] == highlight_code]
            if not highlighted.empty:
                h = highlighted.iloc[0]
                output += f"\n**Highlighted District: {h['district_name']}**\n"
                output += f"- {x_label}: {format_metric_value(x_metric, h[x_metric])}\n"
                output += f"- {y_label}: {format_metric_value(y_metric, h[y_metric])}\n"
                enrollment = int(h['enrollment']) if h['enrollment'] and not np.isnan(h['enrollment']) else 0
                output += f"- Enrollment: {enrollment:,}\n"
            else:
                output += f"\n*Note: District {highlight_code} not found in data with both metrics.*\n"

        output += "\n*Tip: Use the Correlations page in the app for an interactive scatter plot.*"
        return output

    else:
        return f"Unknown tool: {tool_name}"


# Export for convenience
AVAILABLE_TOOLS = TOOL_SCHEMAS


def _convert_to_gemini_declaration(schema: dict) -> dict:
    """Convert a tool schema to a dict suitable for types.FunctionDeclaration."""
    return {
        "name": schema["name"],
        "description": schema["description"],
        "parameters_json_schema": schema["input_schema"],
    }


# Build google.genai Tool object with all function declarations
GEMINI_TOOLS = types.Tool(
    function_declarations=[_convert_to_gemini_declaration(s) for s in TOOL_SCHEMAS]
)
