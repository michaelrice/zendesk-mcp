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
