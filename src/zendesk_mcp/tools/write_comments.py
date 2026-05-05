from zenpy.lib.api_objects import Comment, Ticket

from zendesk_mcp.client import get_client, ConfigError


def _post_comment_data(ticket_id: int, body: str, public: bool) -> str:
    try:
        client = get_client()
        ticket = Ticket(id=ticket_id)
        ticket.comment = Comment(body=body, public=public)
        client.tickets.update(ticket)
        label = "Public comment" if public else "Internal note"
        return f"{label} posted successfully on ticket #{ticket_id}."
    except ConfigError as e:
        return str(e)
    except Exception as e:
        if "RecordNotFound" in str(e) or "404" in str(e):
            return f"Ticket #{ticket_id} not found or not accessible with current credentials."
        return f"Zendesk API error: {e}"


def register_write_comment_tools(mcp) -> None:
    @mcp.tool()
    def zendesk_post_comment(ticket_id: int, body: str) -> str:
        """Post a public reply on a Zendesk ticket. The reply is visible to the requester. Use for customer-facing responses."""
        return _post_comment_data(ticket_id, body, public=True)

    @mcp.tool()
    def zendesk_post_internal_note(ticket_id: int, body: str) -> str:
        """Post an internal note on a Zendesk ticket. Internal notes are only visible to agents and are not sent to the requester."""
        return _post_comment_data(ticket_id, body, public=False)
