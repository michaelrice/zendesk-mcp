from unittest.mock import patch, MagicMock
from zendesk_mcp.client import ConfigError


# ---- set_ticket_status tests ----

@patch("zendesk_mcp.tools.update_ticket.Ticket")
@patch("zendesk_mcp.tools.update_ticket.get_client")
def test_set_ticket_status_updates_ticket(mock_get_client, mock_ticket_cls):
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client

    mock_ticket_instance = MagicMock()
    mock_ticket_cls.return_value = mock_ticket_instance

    from zendesk_mcp.tools.update_ticket import _set_ticket_status_data
    result = _set_ticket_status_data(12345, "pending")

    mock_ticket_cls.assert_called_once_with(id=12345)
    assert mock_ticket_instance.status == "pending"
    mock_client.tickets.update.assert_called_once_with(mock_ticket_instance)
    assert "12345" in result
    assert "pending" in result


@patch("zendesk_mcp.tools.update_ticket.get_client")
def test_set_ticket_status_rejects_invalid_status(mock_get_client):
    from zendesk_mcp.tools.update_ticket import _set_ticket_status_data
    result = _set_ticket_status_data(12345, "banana")

    mock_get_client.assert_not_called()
    assert "invalid" in result.lower()
    assert "banana" in result


@patch("zendesk_mcp.tools.update_ticket.get_client")
def test_set_ticket_status_returns_error_on_config_error(mock_get_client):
    mock_get_client.side_effect = ConfigError("Zendesk not configured. Run: zendesk-mcp setup")

    from zendesk_mcp.tools.update_ticket import _set_ticket_status_data
    result = _set_ticket_status_data(12345, "open")

    assert "zendesk-mcp setup" in result


@patch("zendesk_mcp.tools.update_ticket.Ticket")
@patch("zendesk_mcp.tools.update_ticket.get_client")
def test_set_ticket_status_returns_error_on_not_found(mock_get_client, mock_ticket_cls):
    mock_client = MagicMock()
    mock_client.tickets.update.side_effect = Exception("RecordNotFound: Couldn't find Ticket with id=99999")
    mock_get_client.return_value = mock_client
    mock_ticket_cls.return_value = MagicMock()

    from zendesk_mcp.tools.update_ticket import _set_ticket_status_data
    result = _set_ticket_status_data(99999, "open")

    assert "99999" in result
    assert "not found" in result.lower()


# ---- assign_ticket tests ----

@patch("zendesk_mcp.tools.update_ticket.Ticket")
@patch("zendesk_mcp.tools.update_ticket.get_client")
def test_assign_ticket_by_email(mock_get_client, mock_ticket_cls):
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client

    mock_user = MagicMock()
    mock_user.id = 42
    mock_user.name = "Alice"
    mock_user.email = "alice@example.com"
    mock_client.search.return_value = iter([mock_user])

    mock_ticket_instance = MagicMock()
    mock_ticket_cls.return_value = mock_ticket_instance

    from zendesk_mcp.tools.update_ticket import _assign_ticket_data
    result = _assign_ticket_data(12345, "alice@example.com")

    mock_client.search.assert_called_once_with(query="type:user email:alice@example.com")
    mock_ticket_cls.assert_called_once_with(id=12345)
    assert mock_ticket_instance.assignee_id == 42
    mock_client.tickets.update.assert_called_once_with(mock_ticket_instance)
    assert "Alice" in result
    assert "12345" in result


@patch("zendesk_mcp.tools.update_ticket.Ticket")
@patch("zendesk_mcp.tools.update_ticket.get_client")
def test_assign_ticket_to_me(mock_get_client, mock_ticket_cls):
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client

    mock_me = MagicMock()
    mock_me.id = 7
    mock_me.name = "Agent"
    mock_me.email = "agent@example.com"
    mock_client.users.me.return_value = mock_me

    mock_ticket_instance = MagicMock()
    mock_ticket_cls.return_value = mock_ticket_instance

    from zendesk_mcp.tools.update_ticket import _assign_ticket_data
    result = _assign_ticket_data(12345, "me")

    mock_client.users.me.assert_called_once()
    mock_client.search.assert_not_called()
    assert mock_ticket_instance.assignee_id == 7
    assert "Agent" in result


@patch("zendesk_mcp.tools.update_ticket.get_client")
def test_assign_ticket_returns_error_when_user_not_found(mock_get_client):
    mock_client = MagicMock()
    mock_client.search.return_value = iter([])
    mock_get_client.return_value = mock_client

    from zendesk_mcp.tools.update_ticket import _assign_ticket_data
    result = _assign_ticket_data(12345, "ghost@example.com")

    assert "ghost@example.com" in result
    assert "not found" in result.lower()
    mock_client.tickets.update.assert_not_called()


@patch("zendesk_mcp.tools.update_ticket.get_client")
def test_assign_ticket_returns_error_on_config_error(mock_get_client):
    mock_get_client.side_effect = ConfigError("Zendesk not configured. Run: zendesk-mcp setup")

    from zendesk_mcp.tools.update_ticket import _assign_ticket_data
    result = _assign_ticket_data(12345, "alice@example.com")

    assert "zendesk-mcp setup" in result


# ---- generic update_ticket tests ----

import json
from datetime import datetime


def _make_refreshed_update_ticket():
    t = MagicMock()
    t.id = 12345
    t.subject = "Updated subject"
    t.description = "desc"
    t.status = "pending"
    t.priority = "urgent"
    t.type = "incident"
    t.created_at = datetime(2026, 4, 20, 10, 0, 0)
    t.updated_at = datetime(2026, 5, 6, 12, 0, 0)
    t.requester_id = 101
    t.assignee_id = 42
    t.organization_id = 303
    t.tags = ["x", "y"]
    return t


@patch("zendesk_mcp.tools.update_ticket.get_client")
def test_update_ticket_happy_path(mock_get_client):
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client

    loaded = MagicMock()
    refreshed = _make_refreshed_update_ticket()
    mock_client.tickets.side_effect = [loaded, refreshed]

    from zendesk_mcp.tools.update_ticket import _update_ticket_data
    result = _update_ticket_data(
        ticket_id=12345,
        subject="Updated subject",
        status="pending",
        priority="urgent",
        type="incident",
        assignee_id=42,
        tags=["x", "y"],
    )

    assert loaded.subject == "Updated subject"
    assert loaded.status == "pending"
    assert loaded.priority == "urgent"
    assert loaded.type == "incident"
    assert loaded.assignee_id == 42
    assert loaded.tags == ["x", "y"]

    mock_client.tickets.update.assert_called_once_with(loaded)
    parsed = json.loads(result)
    assert parsed["id"] == 12345
    assert parsed["subject"] == "Updated subject"
    assert parsed["status"] == "pending"
    assert parsed["assignee_id"] == 42


@patch("zendesk_mcp.tools.update_ticket.get_client")
def test_update_ticket_skips_none_fields(mock_get_client):
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client

    loaded = MagicMock()
    # Make the loaded ticket's pre-existing fields visible, so we can detect if they get overwritten
    loaded.subject = "original"
    loaded.priority = "low"
    refreshed = _make_refreshed_update_ticket()
    mock_client.tickets.side_effect = [loaded, refreshed]

    from zendesk_mcp.tools.update_ticket import _update_ticket_data
    _update_ticket_data(ticket_id=12345, status="pending")

    # subject and priority should not have been touched
    assert loaded.subject == "original"
    assert loaded.priority == "low"
    assert loaded.status == "pending"


@patch("zendesk_mcp.tools.update_ticket.get_client")
def test_update_ticket_rejects_no_fields(mock_get_client):
    from zendesk_mcp.tools.update_ticket import _update_ticket_data
    result = _update_ticket_data(ticket_id=12345)
    mock_get_client.assert_not_called()
    assert "nothing to update" in result.lower()


@patch("zendesk_mcp.tools.update_ticket.get_client")
def test_update_ticket_rejects_invalid_status(mock_get_client):
    from zendesk_mcp.tools.update_ticket import _update_ticket_data
    result = _update_ticket_data(ticket_id=12345, status="banana")
    mock_get_client.assert_not_called()
    assert "invalid status" in result.lower()
    assert "banana" in result


@patch("zendesk_mcp.tools.update_ticket.get_client")
def test_update_ticket_rejects_invalid_priority(mock_get_client):
    from zendesk_mcp.tools.update_ticket import _update_ticket_data
    result = _update_ticket_data(ticket_id=12345, priority="banana")
    mock_get_client.assert_not_called()
    assert "invalid priority" in result.lower()


@patch("zendesk_mcp.tools.update_ticket.get_client")
def test_update_ticket_rejects_invalid_type(mock_get_client):
    from zendesk_mcp.tools.update_ticket import _update_ticket_data
    result = _update_ticket_data(ticket_id=12345, type="banana")
    mock_get_client.assert_not_called()
    assert "invalid type" in result.lower()


@patch("zendesk_mcp.tools.update_ticket.get_client")
def test_update_ticket_returns_error_on_not_found(mock_get_client):
    mock_client = MagicMock()
    mock_client.tickets.side_effect = Exception("RecordNotFound: Couldn't find Ticket with id=99999")
    mock_get_client.return_value = mock_client

    from zendesk_mcp.tools.update_ticket import _update_ticket_data
    result = _update_ticket_data(ticket_id=99999, status="open")
    assert "99999" in result
    assert "not found" in result.lower()


@patch("zendesk_mcp.tools.update_ticket.get_client")
def test_update_ticket_returns_error_on_config_error(mock_get_client):
    mock_get_client.side_effect = ConfigError("Zendesk not configured. Run: zendesk-mcp setup")
    from zendesk_mcp.tools.update_ticket import _update_ticket_data
    result = _update_ticket_data(ticket_id=12345, status="open")
    assert "zendesk-mcp setup" in result
