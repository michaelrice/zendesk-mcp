import json
import httpx
from zendesk_mcp.client import get_oauth_session, ConfigError


def _get_groups_data() -> str:
    try:
        subdomain, token = get_oauth_session()
    except ConfigError as e:
        return str(e)
    url = f"https://{subdomain}.zendesk.com/api/v2/groups.json"
    try:
        response = httpx.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=30)
        response.raise_for_status()
        groups = [g for g in response.json().get("groups", []) if not g.get("deleted")]
        return json.dumps([{"id": g["id"], "name": g["name"]} for g in groups], indent=2)
    except Exception as e:
        return f"Zendesk API error: {e}"


def _get_group_users_data(group_id: int) -> str:
    try:
        subdomain, token = get_oauth_session()
    except ConfigError as e:
        return str(e)
    url = f"https://{subdomain}.zendesk.com/api/v2/groups/{group_id}/users.json"
    try:
        response = httpx.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=30)
        response.raise_for_status()
        users = response.json().get("users", [])
        return json.dumps([{"id": u["id"], "name": u["name"], "email": u.get("email")} for u in users], indent=2)
    except Exception as e:
        if "404" in str(e):
            return f"Group #{group_id} not found or not accessible with current credentials."
        return f"Zendesk API error: {e}"


def register_group_tools(mcp) -> None:
    @mcp.tool()
    def zendesk_get_groups() -> str:
        """List all active Zendesk groups (excluding deleted). Returns JSON array of {id, name}."""
        return _get_groups_data()

    @mcp.tool()
    def zendesk_get_group_users(group_id: int) -> str:
        """List the members of a Zendesk group. Returns JSON array of {id, name, email}."""
        return _get_group_users_data(group_id)
