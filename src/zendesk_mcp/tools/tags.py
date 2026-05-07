import json
from zendesk_mcp.client import get_client, ConfigError


def _add_tag_data(ticket_id: int, tag: str) -> str:
    try:
        client = get_client()
        ticket = client.tickets(id=ticket_id)
        current_tags = list(getattr(ticket, "tags", []) or [])
        if tag in current_tags:
            return json.dumps({"ticket_id": ticket_id, "tags": current_tags}, indent=2)
        current_tags.append(tag)
        ticket.tags = current_tags
        client.tickets.update(ticket)
        refreshed = client.tickets(id=ticket_id)
        return json.dumps({"ticket_id": ticket_id, "tags": list(getattr(refreshed, "tags", []) or [])}, indent=2)
    except ConfigError as e:
        return str(e)
    except Exception as e:
        if "RecordNotFound" in str(e) or "404" in str(e):
            return f"Ticket #{ticket_id} not found or not accessible with current credentials."
        return f"Zendesk API error: {e}"


def _remove_tag_data(ticket_id: int, tag: str) -> str:
    try:
        client = get_client()
        ticket = client.tickets(id=ticket_id)
        current_tags = list(getattr(ticket, "tags", []) or [])
        if tag not in current_tags:
            return json.dumps({"ticket_id": ticket_id, "tags": current_tags}, indent=2)
        current_tags.remove(tag)
        ticket.tags = current_tags
        client.tickets.update(ticket)
        refreshed = client.tickets(id=ticket_id)
        return json.dumps({"ticket_id": ticket_id, "tags": list(getattr(refreshed, "tags", []) or [])}, indent=2)
    except ConfigError as e:
        return str(e)
    except Exception as e:
        if "RecordNotFound" in str(e) or "404" in str(e):
            return f"Ticket #{ticket_id} not found or not accessible with current credentials."
        return f"Zendesk API error: {e}"


def register_tag_tools(mcp) -> None:
    @mcp.tool()
    def zendesk_add_tag(ticket_id: int, tag: str) -> str:
        """Add a tag to a Zendesk ticket. Idempotent: adding an existing tag returns the current tag list without modifying the ticket. Returns JSON with ticket_id and current tags."""
        return _add_tag_data(ticket_id, tag)

    @mcp.tool()
    def zendesk_remove_tag(ticket_id: int, tag: str) -> str:
        """Remove a tag from a Zendesk ticket. Idempotent: removing a tag that isn't present returns the current tag list without modifying the ticket. Returns JSON with ticket_id and current tags."""
        return _remove_tag_data(ticket_id, tag)
