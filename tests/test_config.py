import json
import os
import stat
import sys
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


posix_only = pytest.mark.skipif(sys.platform == "win32", reason="POSIX file modes")


def test_save_then_load_round_trips(tmp_path):
    from zendesk_mcp.config import load_config, save_config
    path = tmp_path / "zendesk-mcp" / "config.json"
    save_config({"subdomain": "acme", "oauth_token": "tok"}, path)
    assert load_config(path) == {"subdomain": "acme", "oauth_token": "tok"}


@posix_only
def test_saved_file_is_owner_only_even_under_a_permissive_umask(tmp_path):
    from zendesk_mcp.config import save_config
    path = tmp_path / "config.json"
    old = os.umask(0)
    try:
        save_config({"oauth_token": "tok"}, path)
    finally:
        os.umask(old)
    assert stat.S_IMODE(path.stat().st_mode) == 0o600


@posix_only
def test_save_tightens_an_existing_world_readable_file(tmp_path):
    from zendesk_mcp.config import save_config
    path = tmp_path / "config.json"
    path.write_text("{}")
    path.chmod(0o644)
    save_config({"oauth_token": "tok"}, path)
    assert stat.S_IMODE(path.stat().st_mode) == 0o600


@posix_only
def test_new_config_directory_is_owner_only(tmp_path):
    from zendesk_mcp.config import save_config
    path = tmp_path / "fresh" / "config.json"
    save_config({"oauth_token": "tok"}, path)
    assert stat.S_IMODE(path.parent.stat().st_mode) == 0o700


def test_save_leaves_no_temp_files_behind(tmp_path):
    from zendesk_mcp.config import save_config
    path = tmp_path / "config.json"
    save_config({"a": 1}, path)
    save_config({"a": 2}, path)
    assert sorted(p.name for p in tmp_path.iterdir()) == ["config.json"]


def test_failed_write_keeps_the_previous_config_intact(tmp_path, monkeypatch):
    from zendesk_mcp import config
    path = tmp_path / "config.json"
    config.save_config({"oauth_token": "good"}, path)

    def boom(*_a, **_k):
        raise OSError("disk full")

    monkeypatch.setattr(config.os, "replace", boom)
    with pytest.raises(OSError):
        config.save_config({"oauth_token": "partial"}, path)

    assert json.loads(path.read_text()) == {"oauth_token": "good"}
    assert sorted(p.name for p in tmp_path.iterdir()) == ["config.json"]
