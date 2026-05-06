import json
from zenpy.lib.api_objects import Ticket as ZenpyTicket
from zendesk_mcp.client import get_client, ConfigError

_VALID_PRIORITIES = {"low", "normal", "high", "urgent"}
_VALID_TYPES = {"problem", "incident", "question", "task"}


def _create_ticket_data(
    subject: str,
    description: str,
    requester_id: int | None = None,
    assignee_id: int | None = None,
    priority: str | None = None,
    type: str | None = None,
    tags: list | None = None,
    custom_fields: list | None = None,
) -> str:
    if priority is not None and priority not in _VALID_PRIORITIES:
        return f"Invalid priority '{priority}'. Valid values: {', '.join(sorted(_VALID_PRIORITIES))}"
    if type is not None and type not in _VALID_TYPES:
        return f"Invalid type '{type}'. Valid values: {', '.join(sorted(_VALID_TYPES))}"
    try:
        client = get_client()
        kwargs = {"subject": subject, "description": description}
        if requester_id is not None:
            kwargs["requester_id"] = requester_id
        if assignee_id is not None:
            kwargs["assignee_id"] = assignee_id
        if priority is not None:
            kwargs["priority"] = priority
        if type is not None:
            kwargs["type"] = type
        if tags is not None:
            kwargs["tags"] = tags
        if custom_fields is not None:
            kwargs["custom_fields"] = custom_fields
        ticket = ZenpyTicket(**kwargs)
        audit = client.tickets.create(ticket)
        created_id = getattr(getattr(audit, "ticket", None), "id", None)
        if created_id is None:
            return "Ticket created but ID could not be determined from Zendesk response."
        refreshed = client.tickets(id=created_id)
        return json.dumps({
            "id": refreshed.id,
            "subject": refreshed.subject,
            "description": refreshed.description,
            "status": refreshed.status,
            "priority": refreshed.priority,
            "type": getattr(refreshed, "type", None),
            "created_at": str(refreshed.created_at),
            "updated_at": str(refreshed.updated_at),
            "requester_id": refreshed.requester_id,
            "assignee_id": refreshed.assignee_id,
            "organization_id": refreshed.organization_id,
            "tags": list(getattr(refreshed, "tags", []) or []),
        }, indent=2)
    except ConfigError as e:
        return str(e)
    except Exception as e:
        return f"Zendesk API error: {e}"


def register_create_ticket_tools(mcp) -> None:
    @mcp.tool()
    def zendesk_create_ticket(
        subject: str,
        description: str,
        requester_id: int | None = None,
        assignee_id: int | None = None,
        priority: str | None = None,
        type: str | None = None,
        tags: list | None = None,
        custom_fields: list | None = None,
    ) -> str:
        """Create a new Zendesk ticket. subject and description are required. priority: low/normal/high/urgent. type: problem/incident/question/task. requester_id/assignee_id are user IDs (integers). custom_fields is a list of {id, value} dicts. Returns JSON of the created ticket."""
        return _create_ticket_data(
            subject=subject,
            description=description,
            requester_id=requester_id,
            assignee_id=assignee_id,
            priority=priority,
            type=type,
            tags=tags,
            custom_fields=custom_fields,
        )
