import json
from unittest.mock import patch, MagicMock
from zendesk_mcp.client import ConfigError


@patch("zendesk_mcp.tools.organizations.httpx.get")
@patch("zendesk_mcp.tools.organizations.get_oauth_session")
def test_get_organization_returns_custom_fields(mock_oauth, mock_httpx_get):
    mock_oauth.return_value = ("acme", "tok")
    response = MagicMock()
    response.json.return_value = {
        "organization": {
            "id": 100,
            "name": "Acme Corp",
            "organization_fields": {"tier": "enterprise", "region": "us-west"},
            "tags": ["premium", "vip"],
            "created_at": "2026-01-01T00:00:00Z",
            "updated_at": "2026-05-01T00:00:00Z",
        }
    }
    response.raise_for_status = MagicMock()
    mock_httpx_get.return_value = response

    from zendesk_mcp.tools.organizations import _get_organization_data
    result = _get_organization_data(100)

    args, kwargs = mock_httpx_get.call_args
    assert "acme.zendesk.com/api/v2/organizations/100.json" in args[0]
    parsed = json.loads(result)
    assert parsed["id"] == 100
    assert parsed["name"] == "Acme Corp"
    assert parsed["organization_fields"]["tier"] == "enterprise"
    assert "premium" in parsed["tags"]


@patch("zendesk_mcp.tools.organizations.get_oauth_session")
def test_get_organization_returns_config_error(mock_oauth):
    mock_oauth.side_effect = ConfigError("Zendesk not configured. Run: zendesk-mcp setup")
    from zendesk_mcp.tools.organizations import _get_organization_data
    result = _get_organization_data(1)
    assert "zendesk-mcp setup" in result


@patch("zendesk_mcp.tools.organizations.httpx.get")
@patch("zendesk_mcp.tools.organizations.get_oauth_session")
def test_get_organization_returns_not_found(mock_oauth, mock_httpx_get):
    mock_oauth.return_value = ("acme", "tok")
    mock_httpx_get.side_effect = Exception("404 Not Found")
    from zendesk_mcp.tools.organizations import _get_organization_data
    result = _get_organization_data(999)
    assert "999" in result
    assert "not found" in result.lower()
