import json
from datetime import datetime
from unittest.mock import patch, MagicMock
from zendesk_mcp.client import ConfigError


def _make_refreshed_ticket():
    t = MagicMock()
    t.id = 555
    t.subject = "New issue"
    t.description = "Something is broken"
    t.status = "new"
    t.priority = "high"
    t.type = "problem"
    t.created_at = datetime(2026, 5, 6, 12, 0, 0)
    t.updated_at = datetime(2026, 5, 6, 12, 0, 0)
    t.requester_id = 101
    t.assignee_id = 202
    t.organization_id = 303
    t.tags = ["bug"]
    return t


@patch("zendesk_mcp.tools.create_ticket.ZenpyTicket")
@patch("zendesk_mcp.tools.create_ticket.get_client")
def test_create_ticket_happy_path(mock_get_client, mock_ticket_cls):
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client

    audit = MagicMock()
    audit.ticket = MagicMock()
    audit.ticket.id = 555
    mock_client.tickets.create.return_value = audit

    refreshed = _make_refreshed_ticket()
    mock_client.tickets.return_value = refreshed

    from zendesk_mcp.tools.create_ticket import _create_ticket_data
    result = _create_ticket_data(
        subject="New issue",
        description="Something is broken",
        priority="high",
        type="problem",
        requester_id=101,
        assignee_id=202,
        tags=["bug"],
    )

    mock_ticket_cls.assert_called_once()
    kwargs = mock_ticket_cls.call_args.kwargs
    assert kwargs["subject"] == "New issue"
    assert kwargs["description"] == "Something is broken"
    assert kwargs["priority"] == "high"
    assert kwargs["type"] == "problem"
    assert kwargs["tags"] == ["bug"]

    mock_client.tickets.create.assert_called_once()
    mock_client.tickets.assert_called_once_with(id=555)

    parsed = json.loads(result)
    assert parsed["id"] == 555
    assert parsed["subject"] == "New issue"
    assert parsed["status"] == "new"
    assert parsed["tags"] == ["bug"]


@patch("zendesk_mcp.tools.create_ticket.get_client")
def test_create_ticket_rejects_invalid_priority(mock_get_client):
    from zendesk_mcp.tools.create_ticket import _create_ticket_data
    result = _create_ticket_data(subject="x", description="y", priority="banana")
    mock_get_client.assert_not_called()
    assert "invalid priority" in result.lower()
    assert "banana" in result


@patch("zendesk_mcp.tools.create_ticket.get_client")
def test_create_ticket_rejects_invalid_type(mock_get_client):
    from zendesk_mcp.tools.create_ticket import _create_ticket_data
    result = _create_ticket_data(subject="x", description="y", type="banana")
    mock_get_client.assert_not_called()
    assert "invalid type" in result.lower()
    assert "banana" in result


@patch("zendesk_mcp.tools.create_ticket.get_client")
def test_create_ticket_returns_error_on_config_error(mock_get_client):
    mock_get_client.side_effect = ConfigError("Zendesk not configured. Run: zendesk-mcp setup")
    from zendesk_mcp.tools.create_ticket import _create_ticket_data
    result = _create_ticket_data(subject="x", description="y")
    assert "zendesk-mcp setup" in result


@patch("zendesk_mcp.tools.create_ticket.ZenpyTicket")
@patch("zendesk_mcp.tools.create_ticket.get_client")
def test_create_ticket_returns_generic_error_on_api_failure(mock_get_client, mock_ticket_cls):
    mock_client = MagicMock()
    mock_client.tickets.create.side_effect = Exception("kaboom")
    mock_get_client.return_value = mock_client
    mock_ticket_cls.return_value = MagicMock()

    from zendesk_mcp.tools.create_ticket import _create_ticket_data
    result = _create_ticket_data(subject="x", description="y")
    assert "Zendesk API error" in result
    assert "kaboom" in result
