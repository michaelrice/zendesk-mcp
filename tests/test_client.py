import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock


def test_get_client_raises_config_error_when_token_missing(tmp_path):
    cfg_file = tmp_path / "config.json"
    cfg_file.write_text(json.dumps({"subdomain": "example"}))
    from zendesk_mcp.client import get_client, ConfigError
    with pytest.raises(ConfigError, match="Run: zendesk-mcp setup"):
        get_client(cfg_file)


def test_get_client_raises_config_error_when_subdomain_missing(tmp_path):
    cfg_file = tmp_path / "config.json"
    cfg_file.write_text(json.dumps({"oauth_token": "tok"}))
    from zendesk_mcp.client import get_client, ConfigError
    with pytest.raises(ConfigError, match="Run: zendesk-mcp setup"):
        get_client(cfg_file)


def test_get_client_returns_zenpy_instance(tmp_path):
    cfg_file = tmp_path / "config.json"
    cfg_file.write_text(json.dumps({
        "subdomain": "example",
        "oauth_token": "tok123",
    }))
    with patch("zendesk_mcp.client.Zenpy") as mock_zenpy:
        mock_instance = MagicMock()
        mock_zenpy.return_value = mock_instance
        from zendesk_mcp.client import get_client
        result = get_client(cfg_file)
        mock_zenpy.assert_called_once_with(subdomain="example", oauth_token="tok123")
        assert result is mock_instance


def test_get_oauth_session_returns_subdomain_and_token(tmp_path):
    cfg_file = tmp_path / "config.json"
    cfg_file.write_text(json.dumps({"subdomain": "acme", "oauth_token": "tok123"}))
    with patch("zendesk_mcp.client.load_config", return_value={"subdomain": "acme", "oauth_token": "tok123"}):
        from zendesk_mcp.client import get_oauth_session
        subdomain, token = get_oauth_session()
        assert subdomain == "acme"
        assert token == "tok123"


def test_get_oauth_session_raises_config_error_when_missing_token():
    with patch("zendesk_mcp.client.load_config", return_value={"subdomain": "acme"}):
        from zendesk_mcp.client import get_oauth_session, ConfigError
        with pytest.raises(ConfigError, match="Run: zendesk-mcp setup"):
            get_oauth_session()


def test_get_oauth_session_raises_config_error_when_missing_subdomain():
    with patch("zendesk_mcp.client.load_config", return_value={"oauth_token": "tok"}):
        from zendesk_mcp.client import get_oauth_session, ConfigError
        with pytest.raises(ConfigError, match="Run: zendesk-mcp setup"):
            get_oauth_session()
