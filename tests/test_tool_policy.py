import asyncio

import pytest

from zendesk_mcp.tool_policy import WRITE_TOOLS, disabled_tools


def _registered_names(cfg=None, env=None):
    from zendesk_mcp.server import FastMCP, register_all
    from unittest.mock import patch

    srv = FastMCP("zendesk-mcp-policy-test")
    with patch("zendesk_mcp.tool_policy.load_config", return_value=cfg or {}), \
         patch.dict("os.environ", env or {}, clear=False):
        register_all(srv)
    return {t.name for t in asyncio.run(srv.list_tools())}


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    monkeypatch.delenv("ZENDESK_MCP_READ_ONLY", raising=False)
    monkeypatch.delenv("ZENDESK_MCP_DISABLED_TOOLS", raising=False)


def test_default_registers_everything_including_write_tools():
    names = _registered_names()
    assert WRITE_TOOLS <= names
    assert "zendesk_get_ticket" in names


def test_read_only_config_removes_every_write_tool_and_keeps_reads():
    names = _registered_names(cfg={"read_only": True})
    assert not (WRITE_TOOLS & names)
    assert {"zendesk_get_ticket", "zendesk_search_tickets", "zendesk_get_comments"} <= names


def test_read_only_env_removes_write_tools():
    names = _registered_names(env={"ZENDESK_MCP_READ_ONLY": "true"})
    assert not (WRITE_TOOLS & names)


@pytest.mark.parametrize("value", ["false", "0", "", "no"])
def test_read_only_falsey_values_leave_tools_enabled(value):
    assert WRITE_TOOLS <= _registered_names(env={"ZENDESK_MCP_READ_ONLY": value})


def test_disabled_tools_removes_only_the_named_tools():
    names = _registered_names(cfg={"disabled_tools": ["zendesk_post_comment"]})
    assert "zendesk_post_comment" not in names
    assert "zendesk_post_internal_note" in names
    assert "zendesk_update_ticket" in names


def test_disabled_tools_env_is_comma_separated_and_merges_with_config():
    names = _registered_names(
        cfg={"disabled_tools": ["zendesk_post_comment"]},
        env={"ZENDESK_MCP_DISABLED_TOOLS": " zendesk_apply_macro , zendesk_create_ticket "},
    )
    assert not ({"zendesk_post_comment", "zendesk_apply_macro", "zendesk_create_ticket"} & names)
    assert "zendesk_update_ticket" in names


def test_unknown_disabled_tool_is_reported_on_stderr_not_stdout(capsys):
    _registered_names(cfg={"disabled_tools": ["zendesk_nope", "zendesk_post_comment"]})
    out = capsys.readouterr()
    assert out.out == ""
    assert "zendesk_nope" in out.err
    assert "zendesk_post_comment" not in out.err


def test_no_warning_when_nothing_is_disabled(capsys):
    _registered_names()
    assert capsys.readouterr().err == ""


def test_disabled_tools_helper_unions_sources():
    result = disabled_tools(
        cfg={"read_only": True, "disabled_tools": ["zendesk_download_attachment"]},
        env={"ZENDESK_MCP_DISABLED_TOOLS": "zendesk_get_groups"},
    )
    assert WRITE_TOOLS <= result
    assert {"zendesk_download_attachment", "zendesk_get_groups"} <= result
