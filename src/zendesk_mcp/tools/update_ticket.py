from zenpy.lib.api_objects import Ticket

from zendesk_mcp.client import get_client, ConfigError

_VALID_STATUSES = {"new", "open", "pending", "hold", "solved", "closed"}


def _set_ticket_status_data(ticket_id: int, status: str) -> str:
    if status not in _VALID_STATUSES:
        return f"Invalid status '{status}'. Valid values: {', '.join(sorted(_VALID_STATUSES))}"
    try:
        client = get_client()
        ticket = Ticket(id=ticket_id)
        ticket.status = status
        client.tickets.update(ticket)
        return f"Ticket #{ticket_id} status set to '{status}'."
    except ConfigError as e:
        return str(e)
    except Exception as e:
        if "RecordNotFound" in str(e) or "404" in str(e):
            return f"Ticket #{ticket_id} not found or not accessible with current credentials."
        return f"Zendesk API error: {e}"


def _assign_ticket_data(ticket_id: int, assignee_email: str) -> str:
    try:
        client = get_client()
        if assignee_email.lower() == "me":
            user = client.users.me()
        else:
            search_results = list(client.search(query=f"type:user email:{assignee_email}"))
            if not search_results:
                return f"User not found: no Zendesk user with email: {assignee_email}"
            user = search_results[0]
        ticket = Ticket(id=ticket_id)
        ticket.assignee_id = user.id
        client.tickets.update(ticket)
        return f"Ticket #{ticket_id} assigned to {user.name} ({user.email})."
    except ConfigError as e:
        return str(e)
    except Exception as e:
        if "RecordNotFound" in str(e) or "404" in str(e):
            return f"Ticket #{ticket_id} not found or not accessible with current credentials."
        return f"Zendesk API error: {e}"


def register_update_ticket_tools(mcp) -> None:
    @mcp.tool()
    def zendesk_set_ticket_status(ticket_id: int, status: str) -> str:
        """Set the status of a Zendesk ticket. Valid statuses: new, open, pending, hold, solved, closed."""
        return _set_ticket_status_data(ticket_id, status)

    @mcp.tool()
    def zendesk_assign_ticket(ticket_id: int, assignee_email: str) -> str:
        """Assign a Zendesk ticket to an agent by their email address. Pass 'me' as assignee_email to assign the ticket to yourself (the authenticated user)."""
        return _assign_ticket_data(ticket_id, assignee_email)
