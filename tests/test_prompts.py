from unittest.mock import MagicMock

from zendesk_mcp.prompts import (
    _analyze_ticket_messages,
    _draft_ticket_response_messages,
    register_prompts,
)


def test_analyze_ticket_messages_includes_ticket_id():
    messages = _analyze_ticket_messages(ticket_id=42)
    assert isinstance(messages, list)
    assert len(messages) == 1
    msg = messages[0]
    assert msg["role"] == "user"
    assert "42" in msg["content"]
    assert "summary" in msg["content"].lower()


def test_draft_ticket_response_messages_includes_ticket_id():
    messages = _draft_ticket_response_messages(ticket_id=42)
    assert isinstance(messages, list)
    assert len(messages) == 1
    msg = messages[0]
    assert msg["role"] == "user"
    assert "42" in msg["content"]
    assert "draft" in msg["content"].lower() or "response" in msg["content"].lower()


def test_register_prompts_calls_decorator_for_each():
    mcp = MagicMock()
    decorator_factory = MagicMock(side_effect=lambda **kw: lambda f: f)
    mcp.prompt = decorator_factory
    register_prompts(mcp)
    names = [call.kwargs.get("name") for call in decorator_factory.call_args_list]
    assert "analyze-ticket" in names
    assert "draft-ticket-response" in names
