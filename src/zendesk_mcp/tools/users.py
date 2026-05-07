import json
import httpx
from zendesk_mcp.client import get_oauth_session, ConfigError


def _search_users_data(query: str) -> str:
    try:
        subdomain, token = get_oauth_session()
    except ConfigError as e:
        return str(e)
    url = f"https://{subdomain}.zendesk.com/api/v2/users/search.json"
    try:
        response = httpx.get(
            url,
            params={"query": query},
            headers={"Authorization": f"Bearer {token}"},
            timeout=30,
        )
        response.raise_for_status()
        users = response.json().get("users", [])
        return json.dumps([{
            "id": u.get("id"),
            "name": u.get("name"),
            "email": u.get("email"),
            "role": u.get("role"),
        } for u in users], indent=2)
    except Exception as e:
        return f"Zendesk API error: {e}"


def register_user_tools(mcp) -> None:
    @mcp.tool()
    def zendesk_search_users(query: str) -> str:
        """Search Zendesk users by name or email. Returns JSON array of {id, name, email, role}."""
        return _search_users_data(query)
