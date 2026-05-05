import json
import os
import pytest
from pathlib import Path
from unittest.mock import patch


def test_default_config_path_is_in_home(tmp_path):
    with patch("zendesk_mcp.config.Path.home", return_value=tmp_path):
        from zendesk_mcp.config import config_path
        result = config_path()
    assert str(result).endswith(".config/zendesk-mcp/config.json")


def test_load_config_returns_empty_dict_when_file_missing(tmp_path):
    from zendesk_mcp.config import load_config
    result = load_config(tmp_path / "nonexistent.json")
    assert result == {}


def test_load_config_reads_existing_file(tmp_path):
    cfg_file = tmp_path / "config.json"
    cfg_file.write_text(json.dumps({
        "subdomain": "example",
        "oauth_token": "tok123",
        "attachment_cache_dir": "~/.cache/zendesk-mcp/attachments",
    }))
    from zendesk_mcp.config import load_config
    result = load_config(cfg_file)
    assert result["subdomain"] == "example"
    assert result["oauth_token"] == "tok123"


def test_save_config_creates_file_with_correct_permissions(tmp_path):
    cfg_file = tmp_path / "subdir" / "config.json"
    from zendesk_mcp.config import save_config
    save_config({"subdomain": "example", "oauth_token": "tok"}, cfg_file)
    assert cfg_file.exists()
    data = json.loads(cfg_file.read_text())
    assert data["subdomain"] == "example"
    mode = oct(cfg_file.stat().st_mode)[-3:]
    assert mode == "600"


def test_attachment_cache_dir_includes_ticket_id(tmp_path):
    cfg_file = tmp_path / "config.json"
    cfg_file.write_text(json.dumps({
        "attachment_cache_dir": str(tmp_path / "attachments"),
    }))
    from zendesk_mcp.config import attachment_cache_dir
    result = attachment_cache_dir(12345, cfg_file)
    assert str(result).endswith("attachments/12345")
