import json

from zenpy.lib.api_objects import Ticket

from zendesk_mcp.client import get_client, ConfigError

_VALID_STATUSES = {"new", "open", "pending", "hold", "solved", "closed"}
_VALID_PRIORITIES = {"low", "normal", "high", "urgent"}
_VALID_TYPES = {"problem", "incident", "question", "task"}

_UPDATABLE_FIELDS = {
    "subject", "status", "priority", "type",
    "assignee_id", "requester_id", "tags", "custom_fields", "due_at",
    "group_id", "custom_status_id",
}


def _update_ticket_data(ticket_id: int, **fields) -> str:
    provided = {k: v for k, v in fields.items() if v is not None and k in _UPDATABLE_FIELDS}
    if not provided:
        return "Nothing to update: provide at least one field besides ticket_id."
    if "status" in provided and provided["status"] not in _VALID_STATUSES:
        return f"Invalid status '{provided['status']}'. Valid values: {', '.join(sorted(_VALID_STATUSES))}"
    if "priority" in provided and provided["priority"] not in _VALID_PRIORITIES:
        return f"Invalid priority '{provided['priority']}'. Valid values: {', '.join(sorted(_VALID_PRIORITIES))}"
    if "type" in provided and provided["type"] not in _VALID_TYPES:
        return f"Invalid type '{provided['type']}'. Valid values: {', '.join(sorted(_VALID_TYPES))}"
    try:
        client = get_client()
        ticket = client.tickets(id=ticket_id)
        for k, v in provided.items():
            setattr(ticket, k, v)
        client.tickets.update(ticket)
        refreshed = client.tickets(id=ticket_id)
        return json.dumps({
            "id": refreshed.id,
            "subject": refreshed.subject,
            "description": getattr(refreshed, "description", None),
            "status": refreshed.status,
            "priority": refreshed.priority,
            "type": getattr(refreshed, "type", None),
            "created_at": str(refreshed.created_at),
            "updated_at": str(refreshed.updated_at),
            "requester_id": refreshed.requester_id,
            "assignee_id": refreshed.assignee_id,
            "organization_id": getattr(refreshed, "organization_id", None),
            "group_id": getattr(refreshed, "group_id", None),
            "custom_status_id": getattr(refreshed, "custom_status_id", None),
            "tags": list(getattr(refreshed, "tags", []) or []),
        }, indent=2)
    except ConfigError as e:
        return str(e)
    except Exception as e:
        if "RecordNotFound" in str(e) or "404" in str(e):
            return f"Ticket #{ticket_id} not found or not accessible with current credentials."
        return f"Zendesk API error: {e}"


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

    @mcp.tool()
    def zendesk_update_ticket(
        ticket_id: int,
        subject: str | None = None,
        status: str | None = None,
        priority: str | None = None,
        type: str | None = None,
        assignee_id: int | None = None,
        requester_id: int | None = None,
        tags: list | None = None,
        custom_fields: list | None = None,
        due_at: str | None = None,
        group_id: int | None = None,
        custom_status_id: int | None = None,
    ) -> str:
        """Update one or more fields on a Zendesk ticket. Pass only the fields you want to change. status: new/open/pending/hold/solved/closed. priority: low/normal/high/urgent. type: problem/incident/question/task. assignee_id, requester_id, group_id, custom_status_id are integer IDs. due_at is ISO8601. Returns JSON of the refreshed ticket."""
        return _update_ticket_data(
            ticket_id=ticket_id,
            subject=subject,
            status=status,
            priority=priority,
            type=type,
            assignee_id=assignee_id,
            requester_id=requester_id,
            tags=tags,
            custom_fields=custom_fields,
            due_at=due_at,
            group_id=group_id,
            custom_status_id=custom_status_id,
        )
