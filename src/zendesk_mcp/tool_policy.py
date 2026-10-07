"""Optional restrictions on which tools the server registers.

Everything is enabled by default. An operator can narrow the surface, for example for a
deployment where tickets include customer-written text and the agent should not be able
to reply to customers, without changing the code:

* ``read_only`` (config) / ``ZENDESK_MCP_READ_ONLY`` (env): register no write tools.
* ``disabled_tools`` (config list) / ``ZENDESK_MCP_DISABLED_TOOLS`` (env, comma-separated):
  do not register the named tools, e.g. ``zendesk_post_comment,zendesk_apply_macro``.

Environment variables are added to the config values. A disabled tool is never
registered, so the model cannot see it or call it.

This fails open: restrictions that cannot be read are not applied. If the config file is
missing, nothing from it is applied (normal before setup, when the server has no token and
cannot do anything anyway). If it exists but is not valid JSON, ``load_config()`` also returns
``{}``, so ``read_only`` / ``disabled_tools`` from it are silently lost; that case is reported
on stderr below so a restriction that was meant to be in force does not vanish unnoticed. Set
the environment variables as well when a restriction must hold even if the file is damaged.
"""
import json
import os
import sys

from zendesk_mcp.config import config_path, load_config

WRITE_TOOLS = frozenset({
    "zendesk_add_tag",
    "zendesk_apply_macro",
    "zendesk_assign_ticket",
    "zendesk_create_ticket",
    "zendesk_log_time",
    "zendesk_post_comment",
    "zendesk_post_internal_note",
    "zendesk_remove_tag",
    "zendesk_set_ticket_status",
    "zendesk_update_ticket",
})

_TRUE = {"1", "true", "yes", "on"}


def _truthy(value) -> bool:
    return str(value).strip().lower() in _TRUE


def _load_policy_config() -> dict:
    """load_config(), but say so on stderr when an existing file could not be read.

    ``load_config()`` returns ``{}`` for a missing file and for an unparseable one. The first is
    normal; the second means a restriction written in the file is not being applied.
    """
    cfg = load_config()
    path = config_path()
    if not cfg and path.exists():
        try:
            json.loads(path.read_text())
        except (OSError, ValueError) as e:
            # stdout carries the MCP protocol on stdio transport; diagnostics go to stderr.
            print(
                f"zendesk-mcp: could not read {path} ({e}); read_only and disabled_tools from "
                f"the config file are NOT being applied",
                file=sys.stderr,
            )
    return cfg


def disabled_tools(cfg: dict | None = None, env: dict | None = None) -> frozenset[str]:
    cfg = _load_policy_config() if cfg is None else cfg
    env = os.environ if env is None else env

    disabled: set[str] = set()
    if _truthy(cfg.get("read_only", False)) or _truthy(env.get("ZENDESK_MCP_READ_ONLY", "")):
        disabled |= WRITE_TOOLS
    disabled |= {str(n).strip() for n in (cfg.get("disabled_tools") or []) if str(n).strip()}
    disabled |= {n.strip() for n in env.get("ZENDESK_MCP_DISABLED_TOOLS", "").split(",") if n.strip()}
    return frozenset(disabled)


class _ToolPolicy:
    """Wraps an MCP server so tools on the disabled list are not registered."""

    def __init__(self, mcp, disabled: frozenset[str]):
        self._mcp = mcp
        self._disabled = disabled
        self.skipped: set[str] = set()

    def __getattr__(self, name):
        return getattr(self._mcp, name)

    def report_unknown(self) -> None:
        """Warn about disabled names that matched no registered tool (likely typos)."""
        # stdout carries the MCP protocol on stdio transport; diagnostics go to stderr.
        for name in sorted(self._disabled - self.skipped):
            print(f"zendesk-mcp: ignoring unknown tool in disabled list: {name}", file=sys.stderr)

    def _skip(self, tool_name: str) -> bool:
        if tool_name in self._disabled:
            self.skipped.add(tool_name)
            return True
        return False

    def tool(self, *args, **kwargs):
        """Register a tool unless it is disabled, however it is declared.

        The name checked is the one the SDK would register: an explicit ``name`` (first positional
        argument or keyword), else the function's name. Handles ``@mcp.tool()``,
        ``@mcp.tool(name="...")``, ``@mcp.tool("...")`` and the bare ``@mcp.tool`` form.
        """
        if args and callable(args[0]):  # bare @mcp.tool: the function is the first argument
            fn = args[0]
            if self._skip(kwargs.get("name") or fn.__name__):
                return fn
            return self._mcp.tool(*args, **kwargs)

        explicit = args[0] if args and isinstance(args[0], str) else kwargs.get("name")
        register = self._mcp.tool(*args, **kwargs)

        def decorator(fn):
            if self._skip(explicit or fn.__name__):
                return fn
            return register(fn)

        return decorator


def apply_tool_policy(mcp, cfg: dict | None = None, env: dict | None = None) -> "_ToolPolicy":
    return _ToolPolicy(mcp, disabled_tools(cfg, env))
