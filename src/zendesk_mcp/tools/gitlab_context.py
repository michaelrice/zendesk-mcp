from zendesk_mcp.client import get_client, ConfigError
from zendesk_mcp.config import load_config


def _get_gitlab_context(ticket_id: int) -> str:
    try:
        client = get_client()
        ticket = client.tickets(id=ticket_id)
        comments = list(client.tickets.comments(ticket_id))

        subdomain = load_config().get("subdomain", "")
        ticket_url = f"https://{subdomain}.zendesk.com/agent/tickets/{ticket_id}"

        comment_lines = []
        for comment in comments:
            try:
                author = client.users(id=comment.author_id)
                author_name = author.name
            except Exception:
                author_name = "Unknown"

            visibility = "Internal Note" if not comment.public else "Public Reply"
            timestamp = str(comment.created_at)[:10]
            comment_lines.append(
                f"**[{visibility}] {author_name} ({timestamp}):**\n{comment.body}"
            )

        conversation = "\n\n---\n\n".join(comment_lines) if comment_lines else "_No comments._"

        return f"""## [Ticket #{ticket_id}] {ticket.subject}

**Zendesk:** {ticket_url}
**Requester:** {ticket.requester.name} <{ticket.requester.email}>
**Status:** {ticket.status} | **Priority:** {ticket.priority} | **Type:** {ticket.type}
**Tags:** {", ".join(ticket.tags) if ticket.tags else "none"}

---

## Description

{ticket.description}

---

## Conversation

{conversation}

---

## Steps to Reproduce

<!-- Fill in from ticket context or leave for engineer -->
1.
2.
3.

---

_Source: Zendesk ticket #{ticket_id} — {ticket_url}_
"""
    except ConfigError as e:
        return str(e)
    except Exception as e:
        if "RecordNotFound" in str(e) or "404" in str(e):
            return f"Ticket #{ticket_id} not found or not accessible with current credentials."
        return f"Zendesk API error: {e}"


def register_gitlab_context_tools(mcp) -> None:
    @mcp.tool()
    def zendesk_ticket_to_gitlab_context(ticket_id: int) -> str:
        """Format a Zendesk ticket and its comments as an issue draft. Returns Markdown with ticket metadata, full conversation, and an empty Steps to Reproduce section. Use this output as the description when creating an issue in your tracker."""
        return _get_gitlab_context(ticket_id)
