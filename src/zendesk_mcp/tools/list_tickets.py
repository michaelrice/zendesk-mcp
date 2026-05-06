import json
import httpx
from zendesk_mcp.client import ConfigError
from zendesk_mcp.config import load_config

_VALID_SORT_BY = {"created_at", "updated_at", "priority", "status"}
_VALID_SORT_ORDER = {"asc", "desc"}
_MAX_PER_PAGE = 100


def _get_tickets_data(
    page: int = 1,
    per_page: int = 25,
    sort_by: str = "created_at",
    sort_order: str = "desc",
) -> str:
    if sort_by not in _VALID_SORT_BY:
        return f"Invalid sort_by '{sort_by}'. Valid values: {', '.join(sorted(_VALID_SORT_BY))}"
    if sort_order not in _VALID_SORT_ORDER:
        return f"Invalid sort_order '{sort_order}'. Valid values: {', '.join(sorted(_VALID_SORT_ORDER))}"
    per_page = max(1, min(per_page, _MAX_PER_PAGE))
    page = max(1, int(page))

    cfg = load_config()
    subdomain = cfg.get("subdomain", "").strip()
    token = cfg.get("oauth_token", "").strip()
    if not subdomain or not token:
        raise ConfigError("Zendesk not configured. Run: zendesk-mcp setup")

    url = f"https://{subdomain}.zendesk.com/api/v2/tickets.json"
    try:
        response = httpx.get(
            url,
            params={"page": page, "per_page": per_page, "sort_by": sort_by, "sort_order": sort_order},
            headers={"Authorization": f"Bearer {token}"},
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
    except ConfigError:
        raise
    except Exception as e:
        return f"Zendesk API error: {e}"

    raw_tickets = data.get("tickets", [])
    tickets = [{
        "id": t.get("id"),
        "subject": t.get("subject"),
        "status": t.get("status"),
        "priority": t.get("priority"),
        "description": t.get("description"),
        "created_at": t.get("created_at"),
        "updated_at": t.get("updated_at"),
        "requester_id": t.get("requester_id"),
        "assignee_id": t.get("assignee_id"),
    } for t in raw_tickets]

    has_more = data.get("next_page") is not None
    return json.dumps({
        "tickets": tickets,
        "page": page,
        "per_page": per_page,
        "count": len(tickets),
        "sort_by": sort_by,
        "sort_order": sort_order,
        "has_more": has_more,
        "next_page": page + 1 if has_more else None,
        "previous_page": page - 1 if data.get("previous_page") and page > 1 else None,
    }, indent=2)


def register_list_tickets_tools(mcp) -> None:
    @mcp.tool()
    def zendesk_get_tickets(
        page: int = 1,
        per_page: int = 25,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> str:
        """List Zendesk tickets with pagination. page: 1-based page number. per_page: max 100. sort_by: created_at, updated_at, priority, or status. sort_order: asc or desc. Returns tickets plus pagination metadata."""
        try:
            return _get_tickets_data(page=page, per_page=per_page, sort_by=sort_by, sort_order=sort_order)
        except ConfigError as e:
            return str(e)
