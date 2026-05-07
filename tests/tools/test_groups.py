import json
from unittest.mock import patch, MagicMock
from zendesk_mcp.client import ConfigError


@patch("zendesk_mcp.tools.groups.httpx.get")
@patch("zendesk_mcp.tools.groups.get_oauth_session")
def test_get_groups_filters_deleted(mock_oauth, mock_httpx_get):
    mock_oauth.return_value = ("acme", "tok")
    response = MagicMock()
    response.json.return_value = {
        "groups": [
            {"id": 1, "name": "Support", "deleted": False},
            {"id": 2, "name": "Old group", "deleted": True},
            {"id": 3, "name": "Billing"},
        ]
    }
    response.raise_for_status = MagicMock()
    mock_httpx_get.return_value = response

    from zendesk_mcp.tools.groups import _get_groups_data
    result = _get_groups_data()

    args, kwargs = mock_httpx_get.call_args
    assert "acme.zendesk.com/api/v2/groups.json" in args[0]
    parsed = json.loads(result)
    assert len(parsed) == 2
    assert parsed[0] == {"id": 1, "name": "Support"}
    assert all(g["id"] != 2 for g in parsed)


@patch("zendesk_mcp.tools.groups.httpx.get")
@patch("zendesk_mcp.tools.groups.get_oauth_session")
def test_get_group_users_returns_members(mock_oauth, mock_httpx_get):
    mock_oauth.return_value = ("acme", "tok")
    response = MagicMock()
    response.json.return_value = {
        "users": [
            {"id": 10, "name": "Agent A", "email": "a@example.com"},
            {"id": 11, "name": "Agent B", "email": "b@example.com"},
        ]
    }
    response.raise_for_status = MagicMock()
    mock_httpx_get.return_value = response

    from zendesk_mcp.tools.groups import _get_group_users_data
    result = _get_group_users_data(5)

    args, kwargs = mock_httpx_get.call_args
    assert "acme.zendesk.com/api/v2/groups/5/users.json" in args[0]
    parsed = json.loads(result)
    assert len(parsed) == 2
    assert parsed[0] == {"id": 10, "name": "Agent A", "email": "a@example.com"}


@patch("zendesk_mcp.tools.groups.get_oauth_session")
def test_get_groups_returns_config_error(mock_oauth):
    mock_oauth.side_effect = ConfigError("Zendesk not configured. Run: zendesk-mcp setup")
    from zendesk_mcp.tools.groups import _get_groups_data
    result = _get_groups_data()
    assert "zendesk-mcp setup" in result


@patch("zendesk_mcp.tools.groups.httpx.get")
@patch("zendesk_mcp.tools.groups.get_oauth_session")
def test_get_group_users_returns_not_found(mock_oauth, mock_httpx_get):
    mock_oauth.return_value = ("acme", "tok")
    mock_httpx_get.side_effect = Exception("404 Not Found")
    from zendesk_mcp.tools.groups import _get_group_users_data
    result = _get_group_users_data(999)
    assert "999" in result
    assert "not found" in result.lower()
