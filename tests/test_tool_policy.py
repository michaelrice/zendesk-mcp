import asyncio

import pytest

from zendesk_mcp.tool_policy import WRITE_TOOLS, _ToolPolicy, disabled_tools


def _registered_names(cfg=None, env=None):
    from zendesk_mcp.server import FastMCP, register_all
    from unittest.mock import patch

    srv = FastMCP("zendesk-mcp-policy-test")
    with patch("zendesk_mcp.tool_policy.load_config", return_value=cfg or {}), \
         patch.dict("os.environ", env or {}, clear=False):
        register_all(srv)
    return {t.name for t in asyncio.run(srv.list_tools())}


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch, tmp_path):
    monkeypatch.delenv("ZENDESK_MCP_READ_ONLY", raising=False)
    monkeypatch.delenv("ZENDESK_MCP_DISABLED_TOOLS", raising=False)
    # Never read the developer's real ~/.config/zendesk-mcp/config.json.
    monkeypatch.setattr("zendesk_mcp.config.Path.home", lambda: tmp_path)


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


# --- fail-open reporting: an unreadable config must not lose a restriction silently --------


def _write_config(tmp_path, text):
    path = tmp_path / ".config" / "zendesk-mcp" / "config.json"
    path.parent.mkdir(parents=True)
    path.write_text(text)
    return path


def test_unparseable_config_is_reported_on_stderr_not_stdout(tmp_path, capsys):
    path = _write_config(tmp_path, '{"read_only": true,')  # truncated JSON

    result = disabled_tools(env={})

    out = capsys.readouterr()
    assert result == frozenset()  # fails open, as documented
    assert out.out == ""
    assert str(path) in out.err and "could not read" in out.err
    assert "read_only and disabled_tools" in out.err and "NOT being applied" in out.err


def test_environment_still_applies_when_the_config_file_is_unparseable(tmp_path, capsys):
    _write_config(tmp_path, "not json at all")
    result = disabled_tools(env={"ZENDESK_MCP_READ_ONLY": "true"})
    assert WRITE_TOOLS <= result
    assert "NOT being applied" in capsys.readouterr().err


def test_missing_config_file_is_silent(capsys):
    assert disabled_tools(env={}) == frozenset()
    assert capsys.readouterr().err == ""


@pytest.mark.parametrize("text", ["{}", '{"subdomain": "acme", "oauth_token": "t"}'])
def test_readable_config_without_restrictions_is_silent(tmp_path, capsys, text):
    _write_config(tmp_path, text)
    assert disabled_tools(env={}) == frozenset()
    assert capsys.readouterr().err == ""


def test_readable_config_with_read_only_is_applied_silently(tmp_path, capsys):
    _write_config(tmp_path, '{"read_only": true}')
    assert WRITE_TOOLS <= disabled_tools(env={})
    assert capsys.readouterr().err == ""


# --- the filter must see every tool, however it is declared (review note on #19) -------------


def test_every_write_tool_name_is_a_registered_tool():
    """A rename or a reclassified write tool must fail here, not quietly leave WRITE_TOOLS stale."""
    names = _registered_names()
    assert sorted(WRITE_TOOLS - names) == []


def test_disabling_every_registered_tool_by_name_leaves_nothing_registered(capsys):
    """If any tool were registered in a way the policy cannot see, it would survive this."""
    names = _registered_names()
    assert names  # the baseline is not empty

    remaining = _registered_names(cfg={"disabled_tools": sorted(names)})

    assert remaining == set()
    assert capsys.readouterr().err == ""  # and no name was reported as unknown


class _StubMCP:
    """Records what the SDK would register, for each way a tool can be declared."""

    def __init__(self):
        self.registered = []

    def tool(self, *args, **kwargs):
        if args and callable(args[0]):
            self.registered.append(kwargs.get("name") or args[0].__name__)
            return args[0]
        explicit = args[0] if args and isinstance(args[0], str) else kwargs.get("name")

        def decorator(fn):
            self.registered.append(explicit or fn.__name__)
            return fn

        return decorator


def _declare(policy):
    @policy.tool()
    def zendesk_post_comment():  # default name
        pass

    @policy.tool(name="renamed_tool")
    def some_function():  # explicit name by keyword
        pass

    @policy.tool("positional_tool")
    def another_function():  # explicit name, positional
        pass

    @policy.tool
    def zendesk_assign_ticket():  # bare decorator
        pass

    @policy.tool()
    def zendesk_get_ticket():  # a tool that is never disabled
        pass


def test_policy_skips_tools_declared_with_a_keyword_name():
    stub = _StubMCP()
    _declare(_ToolPolicy(stub, frozenset({"renamed_tool"})))
    assert "renamed_tool" not in stub.registered and "some_function" not in stub.registered
    assert {"zendesk_post_comment", "positional_tool", "zendesk_assign_ticket", "zendesk_get_ticket"} <= set(stub.registered)


def test_policy_skips_tools_declared_with_a_positional_name():
    stub = _StubMCP()
    _declare(_ToolPolicy(stub, frozenset({"positional_tool"})))
    assert "positional_tool" not in stub.registered and "another_function" not in stub.registered


def test_policy_skips_tools_declared_with_the_bare_decorator():
    stub = _StubMCP()
    _declare(_ToolPolicy(stub, frozenset({"zendesk_assign_ticket"})))
    assert "zendesk_assign_ticket" not in stub.registered
    assert "zendesk_post_comment" in stub.registered


def test_policy_skips_the_default_named_tool_and_reports_nothing_unknown(capsys):
    stub = _StubMCP()
    policy = _ToolPolicy(stub, frozenset({"zendesk_post_comment"}))
    _declare(policy)
    policy.report_unknown()
    assert "zendesk_post_comment" not in stub.registered
    assert capsys.readouterr().err == ""


def test_policy_skips_every_declaration_form_at_once_and_registers_the_rest():
    stub = _StubMCP()
    every = frozenset({"zendesk_post_comment", "renamed_tool", "positional_tool", "zendesk_assign_ticket"})
    policy = _ToolPolicy(stub, every)
    _declare(policy)
    assert stub.registered == ["zendesk_get_ticket"] and policy.skipped == every
