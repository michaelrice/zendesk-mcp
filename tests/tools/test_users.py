import json
from unittest.mock import patch, MagicMock
from zendesk_mcp.client import ConfigError


@patch("zendesk_mcp.tools.users.httpx.get")
@patch("zendesk_mcp.tools.users.get_oauth_session")
def test_search_users_happy_path(mock_oauth, mock_httpx_get):
    mock_oauth.return_value = ("acme", "tok")
    response = MagicMock()
    response.json.return_value = {
        "users": [
            {"id": 1, "name": "Alice Smith", "email": "alice@example.com", "role": "agent"},
            {"id": 2, "name": "Bob Jones", "email": "bob@example.com", "role": "admin"},
        ]
    }
    response.raise_for_status = MagicMock()
    mock_httpx_get.return_value = response

    from zendesk_mcp.tools.users import _search_users_data
    result = _search_users_data("alice")

    args, kwargs = mock_httpx_get.call_args
    assert "acme.zendesk.com/api/v2/users/search.json" in args[0]
    assert kwargs["params"]["query"] == "alice"
    assert kwargs["headers"]["Authorization"] == "Bearer tok"

    parsed = json.loads(result)
    assert len(parsed) == 2
    assert parsed[0] == {"id": 1, "name": "Alice Smith", "email": "alice@example.com", "role": "agent"}


@patch("zendesk_mcp.tools.users.httpx.get")
@patch("zendesk_mcp.tools.users.get_oauth_session")
def test_search_users_empty_result(mock_oauth, mock_httpx_get):
    mock_oauth.return_value = ("acme", "tok")
    response = MagicMock()
    response.json.return_value = {"users": []}
    response.raise_for_status = MagicMock()
    mock_httpx_get.return_value = response

    from zendesk_mcp.tools.users import _search_users_data
    result = _search_users_data("nobody")
    parsed = json.loads(result)
    assert parsed == []


@patch("zendesk_mcp.tools.users.get_oauth_session")
def test_search_users_returns_config_error(mock_oauth):
    mock_oauth.side_effect = ConfigError("Zendesk not configured. Run: zendesk-mcp setup")
    from zendesk_mcp.tools.users import _search_users_data
    result = _search_users_data("test")
    assert "zendesk-mcp setup" in result
