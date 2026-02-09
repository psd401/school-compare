"""Tests for data resilience improvements — error handling, pagination, validation, lookups."""

from unittest.mock import patch, MagicMock, PropertyMock
import pandas as pd
import pytest
import requests

from src.data.client import OSPIClient, _safe_int
from src.data.combined import _paginated_get


# ---------------------------------------------------------------------------
# Item 1: API error handling in _query()
# ---------------------------------------------------------------------------

class TestQueryErrorHandling:
    """Verify _query() returns [] on API errors instead of crashing."""

    @patch.object(OSPIClient, "client", new_callable=PropertyMock)
    def test_returns_empty_on_network_error(self, mock_client_prop):
        mock_socrata = MagicMock()
        mock_socrata.get.side_effect = requests.exceptions.ConnectionError("timeout")
        mock_client_prop.return_value = mock_socrata

        client = OSPIClient()
        result = client._query("fake-dataset-id")
        assert result == []

    @patch.object(OSPIClient, "client", new_callable=PropertyMock)
    def test_returns_empty_on_generic_exception(self, mock_client_prop):
        mock_socrata = MagicMock()
        mock_socrata.get.side_effect = Exception("Socrata 404")
        mock_client_prop.return_value = mock_socrata

        client = OSPIClient()
        result = client._query("fake-dataset-id")
        assert result == []

    @patch.object(OSPIClient, "client", new_callable=PropertyMock)
    def test_returns_data_on_success(self, mock_client_prop):
        mock_socrata = MagicMock()
        mock_socrata.get.return_value = [{"id": "1"}]
        mock_client_prop.return_value = mock_socrata

        client = OSPIClient()
        result = client._query("fake-dataset-id")
        assert result == [{"id": "1"}]


# ---------------------------------------------------------------------------
# Item 3: Zero-division fix in demographics
# ---------------------------------------------------------------------------

class TestZeroDivisionFix:
    """Verify percent_of_total is None when enrollment is 0."""

    @patch.object(OSPIClient, "_query")
    def test_zero_enrollment_returns_none_percent(self, mock_query):
        mock_query.return_value = [{
            "districtcode": "27400",
            "districtname": "Test District",
            "schoolyear": "2024-25",
            "all_students": "0",
            "white": "0",
            "asian": "0",
            "low_income": "0",
            "female": "0",
        }]

        client = OSPIClient()
        # Bypass Streamlit cache for testing
        result = OSPIClient.get_demographics.__wrapped__(
            client, "27400", "District", "2024-25"
        )

        for demo in result:
            assert demo.percent_of_total is None

    @patch.object(OSPIClient, "_query")
    def test_none_enrollment_returns_none_percent(self, mock_query):
        mock_query.return_value = [{
            "districtcode": "27400",
            "districtname": "Test District",
            "schoolyear": "2024-25",
            "all_students": None,
            "white": "100",
        }]

        client = OSPIClient()
        result = OSPIClient.get_demographics.__wrapped__(
            client, "27400", "District", "2024-25"
        )

        for demo in result:
            assert demo.percent_of_total is None

    @patch.object(OSPIClient, "_query")
    def test_valid_enrollment_calculates_percent(self, mock_query):
        mock_query.return_value = [{
            "districtcode": "27400",
            "districtname": "Test District",
            "schoolyear": "2024-25",
            "all_students": "1000",
            "white": "500",
        }]

        client = OSPIClient()
        result = OSPIClient.get_demographics.__wrapped__(
            client, "27400", "District", "2024-25"
        )

        white = [d for d in result if d.student_group == "White"]
        assert len(white) == 1
        assert white[0].percent_of_total == 50.0


# ---------------------------------------------------------------------------
# Item 5: Dynamic F-196 year range detection
# ---------------------------------------------------------------------------

class TestDynamicYearRange:
    """Verify spending trend dynamically detects year columns from CSV."""

    @patch("src.data.client.F196_DATA_PATH")
    @patch("pandas.read_csv")
    def test_detects_extra_year_column(self, mock_read_csv, mock_path):
        mock_path.exists.return_value = True
        # CSV with an extra year column beyond the old hardcoded range
        df = pd.DataFrame({
            "district_code": ["27400"],
            "per_pupil_23-24": [12000.0],
            "per_pupil_24-25": [12500.0],
            "per_pupil_25-26": [13000.0],
        })
        mock_read_csv.return_value = df

        client = OSPIClient()
        result = OSPIClient.get_spending_trend.__wrapped__(client, "27400")

        assert "23-24" in result
        assert "24-25" in result
        assert "25-26" in result
        assert result["25-26"] == 13000.0

    @patch("src.data.client.F196_DATA_PATH")
    @patch("pandas.read_csv")
    def test_no_matching_columns_returns_empty(self, mock_read_csv, mock_path):
        mock_path.exists.return_value = True
        df = pd.DataFrame({
            "district_code": ["27400"],
            "some_other_column": [100],
        })
        mock_read_csv.return_value = df

        client = OSPIClient()
        result = OSPIClient.get_spending_trend.__wrapped__(client, "27400")

        assert result == {}


# ---------------------------------------------------------------------------
# Item 8: Pagination
# ---------------------------------------------------------------------------

class TestPagination:
    """Verify _paginated_get fetches all pages correctly."""

    def test_single_page(self):
        mock_client = MagicMock()
        # Return fewer results than batch_size = last page
        mock_client.get.return_value = [{"id": i} for i in range(5)]

        result = _paginated_get(mock_client, "dataset-id", batch_size=10)

        assert len(result) == 5
        mock_client.get.assert_called_once()

    def test_multiple_pages(self):
        mock_client = MagicMock()
        # First call: full batch (10), second call: partial (3)
        mock_client.get.side_effect = [
            [{"id": i} for i in range(10)],
            [{"id": i} for i in range(10, 13)],
        ]

        result = _paginated_get(mock_client, "dataset-id", batch_size=10)

        assert len(result) == 13
        assert mock_client.get.call_count == 2

    def test_respects_max_total(self):
        mock_client = MagicMock()
        # Always returns full batch — should stop at max_total
        mock_client.get.return_value = [{"id": i} for i in range(10)]

        result = _paginated_get(mock_client, "dataset-id", batch_size=10, max_total=25)

        # Should fetch 3 batches (0-9, 10-19, 20-29 capped at 25)
        assert mock_client.get.call_count == 3

    def test_handles_exception_mid_pagination(self):
        mock_client = MagicMock()
        mock_client.get.side_effect = [
            [{"id": i} for i in range(10)],
            Exception("API error on page 2"),
        ]

        result = _paginated_get(mock_client, "dataset-id", batch_size=10)

        # Should return first page results, not crash
        assert len(result) == 10

    def test_empty_first_page(self):
        mock_client = MagicMock()
        mock_client.get.return_value = []

        result = _paginated_get(mock_client, "dataset-id", batch_size=10)

        assert result == []
        mock_client.get.assert_called_once()


# ---------------------------------------------------------------------------
# Item 10: Dataset validation
# ---------------------------------------------------------------------------

class TestDatasetValidation:
    """Verify validate_datasets() returns correct status per dataset."""

    @patch.object(OSPIClient, "client", new_callable=PropertyMock)
    def test_all_valid(self, mock_client_prop):
        mock_socrata = MagicMock()
        mock_socrata.get.return_value = [{"id": "1"}]
        mock_client_prop.return_value = mock_socrata

        client = OSPIClient()
        result = OSPIClient.validate_datasets.__wrapped__(client)

        assert all(v is True for v in result.values())

    @patch.object(OSPIClient, "client", new_callable=PropertyMock)
    def test_one_invalid(self, mock_client_prop):
        mock_socrata = MagicMock()
        call_count = [0]

        def side_effect(dataset_id, **kwargs):
            call_count[0] += 1
            # Fail on the second dataset
            if call_count[0] == 2:
                raise Exception("Dataset not found")
            return [{"id": "1"}]

        mock_socrata.get.side_effect = side_effect
        mock_client_prop.return_value = mock_socrata

        client = OSPIClient()
        result = OSPIClient.validate_datasets.__wrapped__(client)

        assert False in result.values()
        assert True in result.values()


# ---------------------------------------------------------------------------
# Item 15: Entity lookup by code
# ---------------------------------------------------------------------------

class TestEntityLookupByCode:
    """Verify get_district_by_code and get_school_by_code return correct models."""

    @patch.object(OSPIClient, "_query")
    def test_get_district_by_code_found(self, mock_query):
        mock_query.return_value = [{
            "districtcode": "27400",
            "districtname": "Peninsula SD",
            "county": "Pierce",
            "esdname": "ESD 121",
        }]

        client = OSPIClient()
        result = OSPIClient.get_district_by_code.__wrapped__(client, "27400")

        assert result is not None
        assert result.district_code == "27400"
        assert result.district_name == "Peninsula SD"
        assert result.county == "Pierce"

    @patch.object(OSPIClient, "_query")
    def test_get_district_by_code_not_found(self, mock_query):
        mock_query.return_value = []

        client = OSPIClient()
        result = OSPIClient.get_district_by_code.__wrapped__(client, "99999")

        assert result is None

    @patch.object(OSPIClient, "_query")
    def test_get_school_by_code_found(self, mock_query):
        mock_query.return_value = [{
            "schoolcode": "3456",
            "schoolname": "Gig Harbor HS",
            "districtcode": "27400",
            "districtname": "Peninsula SD",
            "county": "Pierce",
            "esdname": "ESD 121",
        }]

        client = OSPIClient()
        result = OSPIClient.get_school_by_code.__wrapped__(client, "3456")

        assert result is not None
        assert result.school_code == "3456"
        assert result.school_name == "Gig Harbor HS"
        assert result.district_code == "27400"

    @patch.object(OSPIClient, "_query")
    def test_get_school_by_code_not_found(self, mock_query):
        mock_query.return_value = []

        client = OSPIClient()
        result = OSPIClient.get_school_by_code.__wrapped__(client, "99999")

        assert result is None
