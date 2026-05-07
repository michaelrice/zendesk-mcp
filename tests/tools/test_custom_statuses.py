import json
from unittest.mock import patch, MagicMock
from zendesk_mcp.client import ConfigError


@patch("zendesk_mcp.tools.custom_statuses.httpx.get")
@patch("zendesk_mcp.tools.custom_statuses.get_oauth_session")
def test_list_custom_statuses_happy_path(mock_oauth, mock_httpx_get):
    mock_oauth.return_value = ("acme", "tok")
    response = MagicMock()
    response.json.return_value = {
        "custom_statuses": [
            {"id": 1, "agent_label": "Waiting on vendor", "end_user_label": "In progress",
             "status_category": "pending", "active": True, "default": False},
            {"id": 2, "agent_label": "Needs review", "end_user_label": "Under review",
             "status_category": "open", "active": True, "default": True},
        ]
    }
    response.raise_for_status = MagicMock()
    mock_httpx_get.return_value = response

    from zendesk_mcp.tools.custom_statuses import _list_custom_statuses_data
    result = _list_custom_statuses_data()

    args, kwargs = mock_httpx_get.call_args
    assert "acme.zendesk.com/api/v2/custom_statuses" in args[0]
    assert args[0].endswith("/custom_statuses")

    parsed = json.loads(result)
    assert len(parsed) == 2
    assert parsed[0]["id"] == 1
    assert parsed[0]["agent_label"] == "Waiting on vendor"
    assert parsed[0]["status_category"] == "pending"
    assert parsed[0]["active"] is True
    assert parsed[0]["default"] is False


@patch("zendesk_mcp.tools.custom_statuses.get_oauth_session")
def test_list_custom_statuses_returns_config_error(mock_oauth):
    mock_oauth.side_effect = ConfigError("Zendesk not configured. Run: zendesk-mcp setup")
    from zendesk_mcp.tools.custom_statuses import _list_custom_statuses_data
    result = _list_custom_statuses_data()
    assert "zendesk-mcp setup" in result
