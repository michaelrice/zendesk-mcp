import json
import httpx
from zenpy.lib.api_objects import Ticket as ZenpyTicket, Comment
from zendesk_mcp.client import get_client, get_oauth_session, ConfigError

_SKIP_TICKET_FIELDS = {"id", "url", "created_at", "updated_at"}


def _list_macros_data() -> str:
    try:
        client = get_client()
        macros = [m for m in client.macros() if getattr(m, "active", False)]
        return json.dumps([{
            "id": m.id,
            "title": m.title,
            "description": getattr(m, "description", None),
            "actions": [
                {"field": getattr(a, "field", None), "value": getattr(a, "value", None)}
                for a in (getattr(m, "actions", []) or [])
            ],
        } for m in macros], indent=2)
    except ConfigError as e:
        return str(e)
    except Exception as e:
        return f"Zendesk API error: {e}"


def _preview_macro_data(macro_id: int) -> str:
    try:
        subdomain, token = get_oauth_session()
    except ConfigError as e:
        return str(e)
    url = f"https://{subdomain}.zendesk.com/api/v2/macros/{macro_id}/apply.json"
    try:
        response = httpx.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=30)
        response.raise_for_status()
        return json.dumps(response.json().get("result", {}), indent=2)
    except Exception as e:
        if "404" in str(e):
            return f"Macro #{macro_id} not found or not accessible with current credentials."
        return f"Zendesk API error: {e}"


def _apply_macro_data(ticket_id: int, macro_id: int) -> str:
    try:
        subdomain, token = get_oauth_session()
    except ConfigError as e:
        return str(e)

    url = f"https://{subdomain}.zendesk.com/api/v2/tickets/{ticket_id}/macros/{macro_id}/apply.json"
    try:
        response = httpx.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=30)
        response.raise_for_status()
        result = response.json().get("result", {})
    except Exception as e:
        if "404" in str(e):
            return f"Ticket #{ticket_id} or Macro #{macro_id} not found or not accessible with current credentials."
        return f"Zendesk API error: {e}"

    ticket_changes = {k: v for k, v in (result.get("ticket") or {}).items() if k not in _SKIP_TICKET_FIELDS}
    comment_data = result.get("comment") or {}
    applied_changes = {}
    comment_added = False

    # Note: the field update and comment post are two separate API calls, so
    # if the comment fails after the field update succeeds, the ticket is left
    # in a partially-mutated state and the caller sees a generic error.
    try:
        client = get_client()

        if ticket_changes:
            ticket = client.tickets(id=ticket_id)
            for k, v in ticket_changes.items():
                setattr(ticket, k, v)
            client.tickets.update(ticket)
            applied_changes = ticket_changes

        if comment_data and (comment_data.get("body") or comment_data.get("html_body")):
            body = comment_data.get("body") or comment_data.get("html_body", "")
            public = comment_data.get("public", True)
            comment_ticket = ZenpyTicket(id=ticket_id)
            comment_ticket.comment = Comment(body=body, public=public)
            client.tickets.update(comment_ticket)
            comment_added = True

        refreshed = client.tickets(id=ticket_id)
        return json.dumps({
            "id": refreshed.id,
            "status": refreshed.status,
            "tags": list(getattr(refreshed, "tags", []) or []),
            "applied_changes": applied_changes,
            "comment_added": comment_added,
        }, indent=2)
    except ConfigError as e:
        return str(e)
    except Exception as e:
        if "RecordNotFound" in str(e) or "404" in str(e):
            return f"Ticket #{ticket_id} not found or not accessible with current credentials."
        return f"Zendesk API error: {e}"


def register_macro_tools(mcp) -> None:
    @mcp.tool()
    def zendesk_list_macros() -> str:
        """List all active Zendesk macros with their actions. Returns JSON array of {id, title, description, actions: [{field, value}]}."""
        return _list_macros_data()

    @mcp.tool()
    def zendesk_preview_macro(macro_id: int) -> str:
        """Preview the effect a macro would have (without applying it). Returns the result payload from Zendesk's apply preview endpoint."""
        return _preview_macro_data(macro_id)

    @mcp.tool()
    def zendesk_apply_macro(ticket_id: int, macro_id: int) -> str:
        """Apply a macro to a Zendesk ticket. Fetches the macro preview, applies field changes, and posts any comment included in the macro. Returns JSON with id, status, tags, applied_changes, comment_added."""
        return _apply_macro_data(ticket_id, macro_id)
