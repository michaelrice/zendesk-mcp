import json
from zendesk_mcp.client import get_client, ConfigError


def _search_tickets_data(keywords: str | None, status: str | None, limit: int) -> str:
    try:
        client = get_client()
        query = "type:ticket"
        if keywords:
            query += f" {keywords}"
        if status:
            query += f" status:{status}"
        results = client.search(query=query, sort_by="created_at", sort_order="desc")
        tickets = []
        for ticket in results:
            if len(tickets) >= limit:
                break
            tickets.append({
                "id": ticket.id,
                "subject": ticket.subject,
                "status": ticket.status,
                "priority": ticket.priority,
                "requester": {
                    "name": ticket.requester.name,
                    "email": ticket.requester.email,
                },
                "assignee": {
                    "name": ticket.assignee.name,
                    "email": ticket.assignee.email,
                } if ticket.assignee else None,
                "created_at": str(ticket.created_at),
                "updated_at": str(ticket.updated_at),
                "description": ticket.description[:300] if ticket.description else "",
            })
        return json.dumps(tickets, indent=2)
    except ConfigError as e:
        return str(e)
    except Exception as e:
        return f"Zendesk API error: {e}"


def _get_ticket_data(ticket_id: int) -> str:
    try:
        client = get_client()
        ticket = client.tickets(id=ticket_id)
        return json.dumps({
            "id": ticket.id,
            "subject": ticket.subject,
            "status": ticket.status,
            "priority": ticket.priority,
            "type": ticket.type,
            "requester": {
                "name": ticket.requester.name,
                "email": ticket.requester.email,
            },
            "assignee": {
                "name": ticket.assignee.name,
                "email": ticket.assignee.email,
            } if ticket.assignee else None,
            "group": ticket.group.name if ticket.group else None,
            "tags": ticket.tags,
            "created_at": str(ticket.created_at),
            "updated_at": str(ticket.updated_at),
            "description": ticket.description,
            "ticket_url": f"https://{_get_subdomain()}.zendesk.com/agent/tickets/{ticket.id}",
        }, indent=2)
    except ConfigError as e:
        return str(e)
    except Exception as e:
        if "RecordNotFound" in str(e) or "404" in str(e):
            return f"Ticket #{ticket_id} not found or not accessible with current credentials."
        return f"Zendesk API error: {e}"


def _get_subdomain() -> str:
    from zendesk_mcp.config import load_config
    return load_config().get("subdomain", "")


def register_ticket_tools(mcp) -> None:
    @mcp.tool()
    def zendesk_get_ticket(ticket_id: int) -> str:
        """Get a Zendesk ticket by ID. Returns ticket fields including status, priority, requester, assignee, tags, and description."""
        return _get_ticket_data(ticket_id)

    @mcp.tool()
    def zendesk_search_tickets(keywords: str = "", status: str = "", limit: int = 50) -> str:
        """Search Zendesk tickets by keyword and/or status. keywords: free-text search (e.g. 'login failure LDAP'). status: new, open, pending, hold, solved, closed — leave empty for all statuses. Returns id, subject, status, requester, assignee, and dates."""
        return _search_tickets_data(keywords or None, status or None, limit)
