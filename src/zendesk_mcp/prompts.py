TICKET_ANALYSIS_TEMPLATE = """\
You are a helpful Zendesk support analyst. You've been asked to analyze ticket #{ticket_id}.

Please fetch the ticket info and comments to analyze it and provide:
1. A summary of the issue
2. The current status and timeline
3. Key points of interaction

Remember to be professional and focus on actionable insights."""


COMMENT_DRAFT_TEMPLATE = """\
You are a helpful Zendesk support agent. You need to draft a response to ticket #{ticket_id}.

Please fetch the ticket info, comments and knowledge base to draft a professional and helpful response that:
1. Acknowledges the customer's concern
2. Addresses the specific issues raised
3. Provides clear next steps or ask for specific details need to proceed
4. Maintains a friendly and professional tone
5. Ask for confirmation before commenting on the ticket

The response should be formatted well and ready to be posted as a comment."""


def _analyze_ticket_messages(ticket_id: int) -> list[dict]:
    return [{"role": "user", "content": TICKET_ANALYSIS_TEMPLATE.format(ticket_id=ticket_id)}]


def _draft_ticket_response_messages(ticket_id: int) -> list[dict]:
    return [{"role": "user", "content": COMMENT_DRAFT_TEMPLATE.format(ticket_id=ticket_id)}]


def register_prompts(mcp) -> None:
    @mcp.prompt(name="analyze-ticket", description="Analyze a Zendesk ticket and provide insights")
    def analyze_ticket(ticket_id: int) -> list[dict]:
        return _analyze_ticket_messages(ticket_id)

    @mcp.prompt(name="draft-ticket-response", description="Draft a professional response to a Zendesk ticket")
    def draft_ticket_response(ticket_id: int) -> list[dict]:
        return _draft_ticket_response_messages(ticket_id)
