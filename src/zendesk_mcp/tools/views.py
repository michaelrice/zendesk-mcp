import json
from zendesk_mcp.client import get_client, get_oauth_session, ConfigError
from zendesk_mcp import auth
from zendesk_mcp.auth import api_error_message, TokenExpiredError
from zendesk_mcp.tools.channel import ticket_channel


def _list_views_data() -> str:
    try:
        client = get_client()
        views = list(client.views.active())
        return json.dumps([{"id": v.id, "title": v.title} for v in views], indent=2)
    except (ConfigError, TokenExpiredError) as e:
        return str(e)
    except Exception as e:
        return api_error_message(e)


def _get_view_data(view_id: int) -> str:
    try:
        subdomain, _ = get_oauth_session()
    except (ConfigError, TokenExpiredError) as e:
        return str(e)
    url = f"https://{subdomain}.zendesk.com/api/v2/views/{view_id}.json"
    try:
        response = auth.request("GET", url, timeout=30)
        response.raise_for_status()
        view = response.json().get("view", {})
        return json.dumps({
            "id": view.get("id"),
            "title": view.get("title"),
            "active": view.get("active"),
            "conditions": view.get("conditions"),
            "execution": view.get("execution"),
        }, indent=2)
    except Exception as e:
        if "404" in str(e):
            return f"View #{view_id} not found or not accessible with current credentials."
        return api_error_message(e)


def _get_view_tickets_data(view_id: int) -> str:
    try:
        client = get_client()
        tickets = list(client.views.tickets(view_id))
        return json.dumps([{
            "id": t.id,
            "subject": t.subject,
            "status": t.status,
            "priority": t.priority,
            "assignee_id": t.assignee_id,
            "requester_id": t.requester_id,
            "organization_id": t.organization_id,
            "group_id": getattr(t, "group_id", None),
            "channel": ticket_channel(t),
            "created_at": str(t.created_at),
            "updated_at": str(t.updated_at),
            "tags": list(getattr(t, "tags", []) or []),
        } for t in tickets], indent=2)
    except (ConfigError, TokenExpiredError) as e:
        return str(e)
    except Exception as e:
        if "RecordNotFound" in str(e) or "404" in str(e):
            return f"View #{view_id} not found or not accessible with current credentials."
        return api_error_message(e)


def register_view_tools(mcp) -> None:
    @mcp.tool()
    def zendesk_list_views() -> str:
        """List all active Zendesk views. Returns JSON array of {id, title}."""
        return _list_views_data()

    @mcp.tool()
    def zendesk_get_view(view_id: int) -> str:
        """Get a Zendesk view's definition including filter conditions and execution settings. Returns JSON with id, title, active, conditions, execution."""
        return _get_view_data(view_id)

    @mcp.tool()
    def zendesk_get_view_tickets(view_id: int) -> str:
        """Get the tickets currently matching a Zendesk view. Returns JSON array of tickets with essential fields."""
        return _get_view_tickets_data(view_id)
