import json
from unittest.mock import patch, MagicMock, call
from zendesk_mcp.client import ConfigError


def _make_macro(macro_id: int, title: str, active: bool = True):
    m = MagicMock()
    m.id = macro_id
    m.title = title
    m.description = f"Does {title}"
    m.active = active
    action1 = MagicMock()
    action1.field = "status"
    action1.value = "solved"
    m.actions = [action1]
    return m


@patch("zendesk_mcp.tools.macros.get_client")
def test_list_macros_returns_active_only(mock_get_client):
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    mock_client.macros.return_value = [
        _make_macro(1, "Solve it", active=True),
        _make_macro(2, "Old macro", active=False),
    ]

    from zendesk_mcp.tools.macros import _list_macros_data
    result = _list_macros_data()
    parsed = json.loads(result)

    assert len(parsed) == 1
    assert parsed[0]["id"] == 1
    assert parsed[0]["title"] == "Solve it"
    assert parsed[0]["actions"] == [{"field": "status", "value": "solved"}]


@patch("zendesk_mcp.tools.macros.httpx.get")
@patch("zendesk_mcp.tools.macros.get_oauth_session")
def test_preview_macro_returns_result_payload(mock_oauth, mock_httpx_get):
    mock_oauth.return_value = ("acme", "tok")
    response = MagicMock()
    response.json.return_value = {
        "result": {
            "ticket": {"status": "solved"},
            "comment": {"body": "Resolved!", "public": True},
        }
    }
    response.raise_for_status = MagicMock()
    mock_httpx_get.return_value = response

    from zendesk_mcp.tools.macros import _preview_macro_data
    result = _preview_macro_data(55)

    args, kwargs = mock_httpx_get.call_args
    assert "acme.zendesk.com/api/v2/macros/55/apply.json" in args[0]
    parsed = json.loads(result)
    assert "ticket" in parsed
    assert parsed["comment"]["body"] == "Resolved!"


@patch("zendesk_mcp.tools.macros.get_client")
@patch("zendesk_mcp.tools.macros.httpx.get")
@patch("zendesk_mcp.tools.macros.get_oauth_session")
def test_apply_macro_applies_changes_and_posts_comment(mock_oauth, mock_httpx_get, mock_get_client):
    mock_oauth.return_value = ("acme", "tok")

    preview_response = MagicMock()
    preview_response.json.return_value = {
        "result": {
            "ticket": {"status": "solved", "id": 10, "url": "...", "created_at": "2026-01-01", "updated_at": "2026-01-02"},
            "comment": {"body": "All done!", "public": True},
        }
    }
    preview_response.raise_for_status = MagicMock()
    mock_httpx_get.return_value = preview_response

    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    loaded = MagicMock()
    refreshed = MagicMock()
    refreshed.id = 10
    refreshed.status = "solved"
    refreshed.tags = ["done"]
    mock_client.tickets.side_effect = [loaded, refreshed]

    from zendesk_mcp.tools.macros import _apply_macro_data
    result = _apply_macro_data(10, 55)

    args, kwargs = mock_httpx_get.call_args
    assert "acme.zendesk.com/api/v2/tickets/10/macros/55/apply.json" in args[0]

    assert loaded.status == "solved"
    assert mock_client.tickets.update.call_count == 2
    parsed = json.loads(result)
    assert parsed["id"] == 10
    assert parsed["status"] == "solved"
    assert parsed["applied_changes"] == {"status": "solved"}
    assert parsed["comment_added"] is True


@patch("zendesk_mcp.tools.macros.get_client")
@patch("zendesk_mcp.tools.macros.httpx.get")
@patch("zendesk_mcp.tools.macros.get_oauth_session")
def test_apply_macro_empty_result_returns_success(mock_oauth, mock_httpx_get, mock_get_client):
    mock_oauth.return_value = ("acme", "tok")
    preview_response = MagicMock()
    preview_response.json.return_value = {"result": {}}
    preview_response.raise_for_status = MagicMock()
    mock_httpx_get.return_value = preview_response

    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    refreshed = MagicMock()
    refreshed.id = 10
    refreshed.status = "open"
    refreshed.tags = []
    mock_client.tickets.return_value = refreshed

    from zendesk_mcp.tools.macros import _apply_macro_data
    result = _apply_macro_data(10, 55)

    mock_client.tickets.update.assert_not_called()
    parsed = json.loads(result)
    assert parsed["applied_changes"] == {}
    assert parsed["comment_added"] is False


@patch("zendesk_mcp.tools.macros.get_client")
@patch("zendesk_mcp.tools.macros.httpx.get")
@patch("zendesk_mcp.tools.macros.get_oauth_session")
def test_apply_macro_ticket_changes_only_no_comment(mock_oauth, mock_httpx_get, mock_get_client):
    mock_oauth.return_value = ("acme", "tok")
    preview_response = MagicMock()
    preview_response.json.return_value = {
        "result": {"ticket": {"priority": "high"}}
    }
    preview_response.raise_for_status = MagicMock()
    mock_httpx_get.return_value = preview_response

    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    loaded = MagicMock()
    refreshed = MagicMock()
    refreshed.id = 10
    refreshed.status = "open"
    refreshed.tags = []
    mock_client.tickets.side_effect = [loaded, refreshed]

    from zendesk_mcp.tools.macros import _apply_macro_data
    result = _apply_macro_data(10, 55)

    assert loaded.priority == "high"
    assert mock_client.tickets.update.call_count == 1
    parsed = json.loads(result)
    assert parsed["applied_changes"] == {"priority": "high"}
    assert parsed["comment_added"] is False


@patch("zendesk_mcp.tools.macros.get_client")
@patch("zendesk_mcp.tools.macros.httpx.get")
@patch("zendesk_mcp.tools.macros.get_oauth_session")
def test_apply_macro_comment_only_no_ticket_changes(mock_oauth, mock_httpx_get, mock_get_client):
    mock_oauth.return_value = ("acme", "tok")
    preview_response = MagicMock()
    preview_response.json.return_value = {
        "result": {"comment": {"body": "FYI", "public": False}}
    }
    preview_response.raise_for_status = MagicMock()
    mock_httpx_get.return_value = preview_response

    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    refreshed = MagicMock()
    refreshed.id = 10
    refreshed.status = "open"
    refreshed.tags = []
    mock_client.tickets.return_value = refreshed

    from zendesk_mcp.tools.macros import _apply_macro_data
    result = _apply_macro_data(10, 55)

    assert mock_client.tickets.update.call_count == 1
    parsed = json.loads(result)
    assert parsed["applied_changes"] == {}
    assert parsed["comment_added"] is True


@patch("zendesk_mcp.tools.macros.get_client")
def test_list_macros_returns_config_error(mock_get_client):
    mock_get_client.side_effect = ConfigError("Zendesk not configured. Run: zendesk-mcp setup")
    from zendesk_mcp.tools.macros import _list_macros_data
    result = _list_macros_data()
    assert "zendesk-mcp setup" in result
