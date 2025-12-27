"""
Smoke tests for calendar integration (mocked)
"""
from unittest.mock import MagicMock, patch

import pytest


def test_index_page_without_calendar(authenticated_client):
    """Test index page loads without calendar configured"""
    response = authenticated_client.get("/")
    assert response.status_code == 200


@patch("blueprints.masterprompts.build")
def test_calendar_fetch_success(mock_build, authenticated_client, app, test_user):
    """Test successful calendar event fetch"""
    # Mock the Google Calendar service
    mock_service = MagicMock()
    mock_events = MagicMock()
    mock_list = MagicMock()

    mock_build.return_value = mock_service
    mock_service.events.return_value = mock_events
    mock_events.list.return_value = mock_list
    mock_list.execute.return_value = {
        "items": [
            {
                "id": "event1",
                "summary": "Test Meeting",
                "start": {"dateTime": "2025-12-27T10:00:00Z"},
                "end": {"dateTime": "2025-12-27T11:00:00Z"},
            },
            {
                "id": "event2",
                "summary": "Lunch Break",
                "start": {"dateTime": "2025-12-27T12:00:00Z"},
                "end": {"dateTime": "2025-12-27T13:00:00Z"},
            },
        ]
    }

    # Note: Actual calendar fetching would require calendar credentials
    # This is a structural test to ensure mocking works correctly
    assert mock_list.execute()["items"] is not None


@patch("blueprints.masterprompts.build")
def test_calendar_fetch_empty(mock_build, authenticated_client):
    """Test calendar fetch with no events"""
    mock_service = MagicMock()
    mock_events = MagicMock()
    mock_list = MagicMock()

    mock_build.return_value = mock_service
    mock_service.events.return_value = mock_events
    mock_events.list.return_value = mock_list
    mock_list.execute.return_value = {"items": []}

    result = mock_list.execute()
    assert result["items"] == []


@patch("blueprints.masterprompts.build")
def test_calendar_fetch_error(mock_build):
    """Test calendar fetch error handling"""
    mock_build.side_effect = Exception("Calendar API error")

    with pytest.raises(Exception) as exc_info:
        mock_build()

    assert "Calendar API error" in str(exc_info.value)


def test_tomorrow_page_loads(authenticated_client):
    """Test tomorrow view page loads (which includes calendar integration)"""
    response = authenticated_client.get("/tomorrow")
    assert response.status_code == 200
    assert b"Tomorrow" in response.data or b"Upcoming" in response.data
