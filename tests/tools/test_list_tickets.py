import json
from unittest.mock import patch, MagicMock
from zendesk_mcp.client import ConfigError


@patch("zendesk_mcp.tools.list_tickets.httpx.get")
@patch("zendesk_mcp.tools.list_tickets.get_oauth_session")
def test_get_tickets_happy_path(mock_oauth, mock_httpx_get):
    mock_oauth.return_value = ("acme", "tok")
    response = MagicMock()
    response.json.return_value = {
        "tickets": [
            {"id": 1, "subject": "a", "status": "open", "priority": "low", "description": "d1",
             "created_at": "2026-05-01T00:00:00Z", "updated_at": "2026-05-02T00:00:00Z",
             "requester_id": 10, "assignee_id": 20},
            {"id": 2, "subject": "b", "status": "new", "priority": "high", "description": "d2",
             "created_at": "2026-05-03T00:00:00Z", "updated_at": "2026-05-04T00:00:00Z",
             "requester_id": 11, "assignee_id": None},
        ],
        "next_page": "https://acme.zendesk.com/api/v2/tickets.json?page=2",
        "previous_page": None,
    }
    response.raise_for_status = MagicMock()
    mock_httpx_get.return_value = response

    from zendesk_mcp.tools.list_tickets import _get_tickets_data
    result = _get_tickets_data(page=1, per_page=25, sort_by="created_at", sort_order="desc")

    args, kwargs = mock_httpx_get.call_args
    assert "acme.zendesk.com/api/v2/tickets.json" in args[0]
    assert kwargs["params"]["page"] == 1
    assert kwargs["params"]["per_page"] == 25
    assert kwargs["params"]["sort_by"] == "created_at"
    assert kwargs["params"]["sort_order"] == "desc"
    assert kwargs["headers"]["Authorization"] == "Bearer tok"

    parsed = json.loads(result)
    assert parsed["page"] == 1
    assert parsed["per_page"] == 25
    assert parsed["count"] == 2
    assert parsed["has_more"] is True
    assert parsed["next_page"] == 2
    assert parsed["previous_page"] is None
    assert len(parsed["tickets"]) == 2
    assert parsed["tickets"][0]["id"] == 1


@patch("zendesk_mcp.tools.list_tickets.httpx.get")
@patch("zendesk_mcp.tools.list_tickets.get_oauth_session")
def test_get_tickets_caps_per_page(mock_oauth, mock_httpx_get):
    mock_oauth.return_value = ("acme", "tok")
    response = MagicMock()
    response.json.return_value = {"tickets": [], "next_page": None, "previous_page": None}
    response.raise_for_status = MagicMock()
    mock_httpx_get.return_value = response

    from zendesk_mcp.tools.list_tickets import _get_tickets_data
    _get_tickets_data(page=1, per_page=999)
    assert mock_httpx_get.call_args.kwargs["params"]["per_page"] == 100


@patch("zendesk_mcp.tools.list_tickets.httpx.get")
def test_get_tickets_rejects_invalid_sort_by(mock_httpx_get):
    from zendesk_mcp.tools.list_tickets import _get_tickets_data
    result = _get_tickets_data(sort_by="banana")
    assert "invalid sort_by" in result.lower()
    assert "banana" in result
    mock_httpx_get.assert_not_called()


@patch("zendesk_mcp.tools.list_tickets.httpx.get")
def test_get_tickets_rejects_invalid_sort_order(mock_httpx_get):
    from zendesk_mcp.tools.list_tickets import _get_tickets_data
    result = _get_tickets_data(sort_order="sideways")
    assert "invalid sort_order" in result.lower()
    mock_httpx_get.assert_not_called()


@patch("zendesk_mcp.tools.list_tickets.httpx.get")
@patch("zendesk_mcp.tools.list_tickets.get_oauth_session")
def test_get_tickets_returns_previous_page_when_paginated(mock_oauth, mock_httpx_get):
    mock_oauth.return_value = ("acme", "tok")
    response = MagicMock()
    response.json.return_value = {
        "tickets": [],
        "next_page": None,
        "previous_page": "https://acme.zendesk.com/api/v2/tickets.json?page=1",
    }
    response.raise_for_status = MagicMock()
    mock_httpx_get.return_value = response

    from zendesk_mcp.tools.list_tickets import _get_tickets_data
    result = _get_tickets_data(page=2)
    parsed = json.loads(result)
    assert parsed["previous_page"] == 1
    assert parsed["has_more"] is False


@patch("zendesk_mcp.tools.list_tickets.get_oauth_session")
def test_get_tickets_returns_config_error_message_when_unconfigured(mock_oauth):
    mock_oauth.side_effect = ConfigError("Zendesk not configured. Run: zendesk-mcp setup")
    from zendesk_mcp.tools.list_tickets import _get_tickets_data
    result = _get_tickets_data()
    assert "zendesk-mcp setup" in result
