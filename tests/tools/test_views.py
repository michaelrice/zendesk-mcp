import json
from unittest.mock import patch, MagicMock
from zendesk_mcp.client import ConfigError


def _make_view(view_id: int, title: str):
    v = MagicMock()
    v.id = view_id
    v.title = title
    return v


def _make_ticket(ticket_id: int):
    t = MagicMock()
    t.id = ticket_id
    t.subject = f"Ticket {ticket_id}"
    t.status = "open"
    t.priority = "normal"
    t.assignee_id = 10
    t.requester_id = 20
    t.organization_id = 30
    t.group_id = 5
    t.created_at = "2026-05-01T00:00:00Z"
    t.updated_at = "2026-05-02T00:00:00Z"
    t.tags = ["a", "b"]
    return t


@patch("zendesk_mcp.tools.views.get_client")
def test_list_views_returns_id_and_title(mock_get_client):
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    mock_client.views.active.return_value = [_make_view(1, "All open"), _make_view(2, "Pending")]

    from zendesk_mcp.tools.views import _list_views_data
    result = _list_views_data()
    parsed = json.loads(result)

    assert len(parsed) == 2
    assert parsed[0] == {"id": 1, "title": "All open"}
    assert parsed[1] == {"id": 2, "title": "Pending"}


@patch("zendesk_mcp.tools.views.httpx.get")
@patch("zendesk_mcp.tools.views.get_oauth_session")
def test_get_view_returns_conditions(mock_oauth, mock_httpx_get):
    mock_oauth.return_value = ("acme", "tok")
    response = MagicMock()
    response.json.return_value = {
        "view": {
            "id": 42,
            "title": "My View",
            "active": True,
            "conditions": {"all": [{"field": "status", "operator": "is", "value": "open"}], "any": []},
            "execution": {"columns": [], "group_by": None, "sort_by": "created_at"},
        }
    }
    response.raise_for_status = MagicMock()
    mock_httpx_get.return_value = response

    from zendesk_mcp.tools.views import _get_view_data
    result = _get_view_data(42)
    parsed = json.loads(result)

    args, kwargs = mock_httpx_get.call_args
    assert "acme.zendesk.com/api/v2/views/42.json" in args[0]
    assert kwargs["headers"]["Authorization"] == "Bearer tok"
    assert parsed["id"] == 42
    assert parsed["title"] == "My View"
    assert parsed["active"] is True
    assert "conditions" in parsed
    assert "execution" in parsed


@patch("zendesk_mcp.tools.views.get_client")
def test_get_view_tickets_returns_essential_fields(mock_get_client):
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    mock_client.views.tickets.return_value = [_make_ticket(100), _make_ticket(101)]

    from zendesk_mcp.tools.views import _get_view_tickets_data
    result = _get_view_tickets_data(7)
    parsed = json.loads(result)

    mock_client.views.tickets.assert_called_once_with(7)
    assert len(parsed) == 2
    assert parsed[0]["id"] == 100
    assert parsed[0]["subject"] == "Ticket 100"
    assert "status" in parsed[0]
    assert "tags" in parsed[0]


@patch("zendesk_mcp.tools.views.get_client")
def test_list_views_returns_config_error(mock_get_client):
    mock_get_client.side_effect = ConfigError("Zendesk not configured. Run: zendesk-mcp setup")
    from zendesk_mcp.tools.views import _list_views_data
    result = _list_views_data()
    assert "zendesk-mcp setup" in result


@patch("zendesk_mcp.tools.views.httpx.get")
@patch("zendesk_mcp.tools.views.get_oauth_session")
def test_get_view_returns_not_found(mock_oauth, mock_httpx_get):
    mock_oauth.return_value = ("acme", "tok")
    mock_httpx_get.side_effect = Exception("404 Not Found")
    from zendesk_mcp.tools.views import _get_view_data
    result = _get_view_data(999)
    assert "999" in result
    assert "not found" in result.lower()
