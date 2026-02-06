"""Tests for chat tool execution — output formatting, edge cases."""

import pytest
from unittest.mock import patch, MagicMock

from src.data.models import (
    School,
    District,
    AssessmentData,
    GraduationData,
    StaffingData,
    SpendingData,
    DemographicData,
)
from src.chat.tools import execute_tool, TOOL_SCHEMAS, GEMINI_TOOLS, _convert_to_gemini_schema


class TestToolSchemas:
    def test_all_schemas_have_required_fields(self):
        for schema in TOOL_SCHEMAS:
            assert "name" in schema
            assert "description" in schema
            assert "input_schema" in schema
            assert "properties" in schema["input_schema"]
            assert "required" in schema["input_schema"]

    def test_expected_tool_count(self):
        assert len(TOOL_SCHEMAS) == 8

    def test_tool_names(self):
        names = {s["name"] for s in TOOL_SCHEMAS}
        expected = {
            "search_schools",
            "search_districts",
            "get_assessment_data",
            "get_demographics",
            "get_graduation_data",
            "get_staffing_data",
            "get_spending_data",
            "analyze_correlation",
        }
        assert names == expected


class TestGeminiToolConversion:
    def test_converts_all_tools(self):
        assert len(GEMINI_TOOLS) == len(TOOL_SCHEMAS)

    def test_converted_tool_has_name(self):
        converted = _convert_to_gemini_schema(TOOL_SCHEMAS[0])
        assert "name" in converted
        assert converted["name"] == TOOL_SCHEMAS[0]["name"]

    def test_converted_tool_has_parameters(self):
        converted = _convert_to_gemini_schema(TOOL_SCHEMAS[0])
        assert "parameters" in converted
        assert converted["parameters"]["type"] == "OBJECT"

    def test_enum_preserved(self):
        # get_assessment_data has enum for organization_type
        schema = next(s for s in TOOL_SCHEMAS if s["name"] == "get_assessment_data")
        converted = _convert_to_gemini_schema(schema)
        org_type = converted["parameters"]["properties"]["organization_type"]
        assert "enum" in org_type
        assert "School" in org_type["enum"]
        assert "District" in org_type["enum"]


class TestExecuteTool:
    @patch("src.chat.tools.get_client")
    def test_search_schools_no_results(self, mock_get_client):
        mock_client = MagicMock()
        mock_client.search_schools.return_value = []
        mock_get_client.return_value = mock_client

        result = execute_tool("search_schools", {"query": "zzz_nonexistent"})
        assert "No schools found" in result

    @patch("src.chat.tools.get_client")
    def test_search_schools_with_results(self, mock_get_client):
        mock_client = MagicMock()
        mock_client.search_schools.return_value = [
            School(
                school_code="1234",
                school_name="Lincoln High",
                district_code="17001",
                district_name="Seattle SD",
                county="King",
            )
        ]
        mock_get_client.return_value = mock_client

        result = execute_tool("search_schools", {"query": "Lincoln"})
        assert "Lincoln High" in result
        assert "1234" in result
        assert "Seattle SD" in result

    @patch("src.chat.tools.get_client")
    def test_search_districts_no_results(self, mock_get_client):
        mock_client = MagicMock()
        mock_client.search_districts.return_value = []
        mock_get_client.return_value = mock_client

        result = execute_tool("search_districts", {"query": "zzz"})
        assert "No districts found" in result

    @patch("src.chat.tools.get_client")
    def test_search_districts_with_results(self, mock_get_client):
        mock_client = MagicMock()
        mock_client.search_districts.return_value = [
            District(
                district_code="17001",
                district_name="Seattle SD",
                county="King",
                esd_name="Puget Sound ESD",
            )
        ]
        mock_get_client.return_value = mock_client

        result = execute_tool("search_districts", {"query": "Seattle"})
        assert "Seattle SD" in result
        assert "17001" in result

    @patch("src.chat.tools.get_client")
    def test_assessment_no_results(self, mock_get_client):
        mock_client = MagicMock()
        mock_client.get_assessment_data.return_value = []
        mock_get_client.return_value = mock_client

        result = execute_tool("get_assessment_data", {
            "organization_id": "99999",
            "organization_type": "District",
        })
        assert "No assessment data found" in result

    @patch("src.chat.tools.get_client")
    def test_assessment_with_results(self, mock_get_client):
        mock_client = MagicMock()
        mock_client.get_assessment_data.return_value = [
            AssessmentData(
                organization_id="17001",
                organization_name="Seattle SD",
                school_year="2023-24",
                test_subject="ELA",
                grade_level="All Grades",
                student_group="All Students",
                student_group_type="All",
                percent_met_standard=55.0,
                percent_level_1=10.0,
                percent_level_2=20.0,
                percent_level_3=30.0,
                percent_level_4=25.0,
                count_expected=5000,
            )
        ]
        mock_get_client.return_value = mock_client

        result = execute_tool("get_assessment_data", {
            "organization_id": "17001",
            "organization_type": "District",
        })
        assert "ELA" in result
        assert "55.0%" in result
        assert "5,000" in result

    @patch("src.chat.tools.get_client")
    def test_assessment_suppressed_data(self, mock_get_client):
        mock_client = MagicMock()
        mock_client.get_assessment_data.return_value = [
            AssessmentData(
                organization_id="17001",
                organization_name="Seattle SD",
                school_year="2023-24",
                test_subject="ELA",
                grade_level="All Grades",
                student_group="All Students",
                student_group_type="All",
                is_suppressed=True,
            )
        ]
        mock_get_client.return_value = mock_client

        result = execute_tool("get_assessment_data", {
            "organization_id": "17001",
            "organization_type": "District",
        })
        assert "suppressed" in result

    @patch("src.chat.tools.get_client")
    def test_demographics_no_results(self, mock_get_client):
        mock_client = MagicMock()
        mock_client.get_demographics.return_value = []
        mock_get_client.return_value = mock_client

        result = execute_tool("get_demographics", {
            "organization_id": "99999",
            "organization_type": "District",
        })
        assert "No demographic data found" in result

    @patch("src.chat.tools.get_client")
    def test_demographics_with_results(self, mock_get_client):
        mock_client = MagicMock()
        mock_client.get_demographics.return_value = [
            DemographicData(
                organization_id="17001",
                organization_name="Seattle SD",
                school_year="2024-25",
                student_group="White",
                student_group_type="Race/Ethnicity",
                headcount=5000,
                percent_of_total=45.2,
            ),
            DemographicData(
                organization_id="17001",
                organization_name="Seattle SD",
                school_year="2024-25",
                student_group="Low-Income",
                student_group_type="Program",
                headcount=3000,
                percent_of_total=27.1,
            ),
        ]
        mock_get_client.return_value = mock_client

        result = execute_tool("get_demographics", {
            "organization_id": "17001",
            "organization_type": "District",
        })
        assert "White" in result
        assert "45.2%" in result
        assert "Low-Income" in result

    @patch("src.chat.tools.get_client")
    def test_graduation_no_results(self, mock_get_client):
        mock_client = MagicMock()
        mock_client.get_graduation_data.return_value = []
        mock_get_client.return_value = mock_client

        result = execute_tool("get_graduation_data", {
            "organization_id": "99999",
            "organization_type": "District",
        })
        assert "No graduation data found" in result

    @patch("src.chat.tools.get_client")
    def test_graduation_with_results(self, mock_get_client):
        mock_client = MagicMock()
        mock_client.get_graduation_data.return_value = [
            GraduationData(
                organization_id="17001",
                organization_name="Seattle SD",
                school_year="2023-24",
                student_group="All Students",
                cohort="Four-Year",
                graduation_rate=85.5,
            )
        ]
        mock_get_client.return_value = mock_client

        result = execute_tool("get_graduation_data", {
            "organization_id": "17001",
            "organization_type": "District",
        })
        assert "85.5%" in result
        assert "Four-Year" in result

    @patch("src.chat.tools.get_client")
    def test_staffing_no_results(self, mock_get_client):
        mock_client = MagicMock()
        mock_client.get_staffing_data.return_value = []
        mock_get_client.return_value = mock_client

        result = execute_tool("get_staffing_data", {
            "organization_id": "99999",
            "organization_type": "District",
        })
        assert "No staffing data found" in result

    @patch("src.chat.tools.get_client")
    def test_staffing_with_results(self, mock_get_client):
        mock_client = MagicMock()
        mock_client.get_staffing_data.return_value = [
            StaffingData(
                organization_id="17001",
                organization_name="Seattle SD",
                school_year="2024-25",
                teacher_count=500,
                avg_years_experience=12.3,
                percent_with_masters=65.0,
                student_teacher_ratio=18.5,
            )
        ]
        mock_get_client.return_value = mock_client

        result = execute_tool("get_staffing_data", {
            "organization_id": "17001",
            "organization_type": "District",
        })
        assert "500" in result
        assert "12.3" in result
        assert "65.0%" in result
        assert "18.5:1" in result

    @patch("src.chat.tools.get_client")
    def test_spending_no_results(self, mock_get_client):
        mock_client = MagicMock()
        mock_client.get_spending_data.return_value = None
        mock_get_client.return_value = mock_client

        result = execute_tool("get_spending_data", {"district_code": "99999"})
        assert "No spending data found" in result

    @patch("src.chat.tools.get_client")
    def test_spending_with_results(self, mock_get_client):
        mock_client = MagicMock()
        mock_client.get_spending_data.return_value = SpendingData(
            district_code="17001",
            district_name="Seattle SD",
            school_year="24-25",
            per_pupil_expenditure=15000.0,
            total_expenditure=750000000.0,
            enrollment=50000,
        )
        mock_get_client.return_value = mock_client

        result = execute_tool("get_spending_data", {"district_code": "17001"})
        assert "Seattle SD" in result
        assert "$15,000" in result
        assert "50,000" in result

    @patch("src.chat.tools.get_client")
    def test_spending_with_trend(self, mock_get_client):
        mock_client = MagicMock()
        mock_client.get_spending_data.return_value = SpendingData(
            district_code="17001",
            district_name="Seattle SD",
            school_year="24-25",
            per_pupil_expenditure=15000.0,
        )
        mock_client.get_spending_trend.return_value = {
            "22-23": 13000.0,
            "23-24": 14000.0,
            "24-25": 15000.0,
        }
        mock_get_client.return_value = mock_client

        result = execute_tool("get_spending_data", {
            "district_code": "17001",
            "include_trend": True,
        })
        assert "Spending Trend" in result
        assert "$13,000" in result
        assert "$14,000" in result
        assert "$15,000" in result

    def test_unknown_tool(self):
        result = execute_tool("nonexistent_tool", {})
        assert "Unknown tool" in result
