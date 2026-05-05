import json
from unittest.mock import patch, MagicMock
from zendesk_mcp.client import ConfigError

_FIELD_TOTAL = 30435145651479
_FIELD_LAST = 30435145655959


def _make_ticket_with_time(total_sec, last_sec):
    ticket = MagicMock()
    ticket.custom_fields = [
        {"id": _FIELD_TOTAL, "value": total_sec},
        {"id": _FIELD_LAST, "value": last_sec},
    ]
    return ticket


def test_format_duration_hours_and_minutes():
    from zendesk_mcp.tools.time_tracking import _format_duration
    assert _format_duration(3661) == "1h 01m"


def test_format_duration_minutes_and_seconds():
    from zendesk_mcp.tools.time_tracking import _format_duration
    assert _format_duration(90) == "1m 30s"


def test_format_duration_zero():
    from zendesk_mcp.tools.time_tracking import _format_duration
    assert _format_duration(0) == "0m 00s"


@patch("zendesk_mcp.tools.time_tracking.get_client")
def test_get_time_tracking_returns_seconds_and_human(mock_get_client):
    mock_client = MagicMock()
    mock_client.tickets.return_value = _make_ticket_with_time(3600, 1800)
    mock_get_client.return_value = mock_client

    from zendesk_mcp.tools.time_tracking import _get_time_tracking_data
    result = json.loads(_get_time_tracking_data(12345))

    assert result["ticket_id"] == 12345
    assert result["total_time_spent_sec"] == 3600
    assert result["time_spent_last_update_sec"] == 1800
    assert result["total_time_human"] == "1h 00m"
    assert result["time_spent_last_update_human"] == "30m 00s"


@patch("zendesk_mcp.tools.time_tracking.get_client")
def test_get_time_tracking_returns_zeros_when_no_time_logged(mock_get_client):
    mock_client = MagicMock()
    ticket = MagicMock()
    ticket.custom_fields = []
    mock_client.tickets.return_value = ticket
    mock_get_client.return_value = mock_client

    from zendesk_mcp.tools.time_tracking import _get_time_tracking_data
    result = json.loads(_get_time_tracking_data(12345))

    assert result["total_time_spent_sec"] == 0
    assert result["time_spent_last_update_sec"] == 0
    assert result["total_time_human"] == "0m 00s"


@patch("zendesk_mcp.tools.time_tracking.get_client")
def test_get_time_tracking_returns_error_on_config_error(mock_get_client):
    mock_get_client.side_effect = ConfigError("Zendesk not configured. Run: zendesk-mcp setup")

    from zendesk_mcp.tools.time_tracking import _get_time_tracking_data
    result = _get_time_tracking_data(12345)

    assert "zendesk-mcp setup" in result


@patch("zendesk_mcp.tools.time_tracking.Ticket")
@patch("zendesk_mcp.tools.time_tracking.get_client")
def test_log_time_adds_to_existing_total(mock_get_client, mock_ticket_cls):
    mock_client = MagicMock()
    mock_client.tickets.return_value = _make_ticket_with_time(3600, 0)
    mock_get_client.return_value = mock_client

    mock_update = MagicMock()
    mock_ticket_cls.return_value = mock_update

    from zendesk_mcp.tools.time_tracking import _log_time_data
    result = json.loads(_log_time_data(12345, 1800))

    mock_ticket_cls.assert_called_once_with(id=12345)
    assert mock_update.custom_fields == [
        {"id": _FIELD_TOTAL, "value": 5400},
        {"id": _FIELD_LAST, "value": 1800},
    ]
    mock_client.tickets.update.assert_called_once_with(mock_update)
    assert result["logged_sec"] == 1800
    assert result["logged_human"] == "30m 00s"
    assert result["new_total_sec"] == 5400
    assert result["new_total_human"] == "1h 30m"


@patch("zendesk_mcp.tools.time_tracking.Ticket")
@patch("zendesk_mcp.tools.time_tracking.get_client")
def test_log_time_starts_from_zero_when_no_existing_time(mock_get_client, mock_ticket_cls):
    mock_client = MagicMock()
    ticket = MagicMock()
    ticket.custom_fields = []
    mock_client.tickets.return_value = ticket
    mock_get_client.return_value = mock_client

    mock_update = MagicMock()
    mock_ticket_cls.return_value = mock_update

    from zendesk_mcp.tools.time_tracking import _log_time_data
    result = json.loads(_log_time_data(12345, 900))

    assert mock_update.custom_fields == [
        {"id": _FIELD_TOTAL, "value": 900},
        {"id": _FIELD_LAST, "value": 900},
    ]
    assert result["new_total_sec"] == 900


@patch("zendesk_mcp.tools.time_tracking.get_client")
def test_log_time_returns_error_on_config_error(mock_get_client):
    mock_get_client.side_effect = ConfigError("Zendesk not configured. Run: zendesk-mcp setup")

    from zendesk_mcp.tools.time_tracking import _log_time_data
    result = _log_time_data(12345, 600)

    assert "zendesk-mcp setup" in result


@patch("zendesk_mcp.tools.time_tracking.Ticket")
@patch("zendesk_mcp.tools.time_tracking.get_client")
def test_log_time_returns_error_on_ticket_not_found(mock_get_client, mock_ticket_cls):
    mock_client = MagicMock()
    mock_client.tickets.side_effect = Exception("RecordNotFound: Couldn't find Ticket with id=99999")
    mock_get_client.return_value = mock_client
    mock_ticket_cls.return_value = MagicMock()

    from zendesk_mcp.tools.time_tracking import _log_time_data
    result = _log_time_data(99999, 600)

    assert "99999" in result
    assert "not found" in result.lower()


def test_log_time_rejects_non_positive_seconds():
    from zendesk_mcp.tools.time_tracking import _log_time_data
    result = _log_time_data(12345, 0)
    assert "positive" in result.lower()

    result2 = _log_time_data(12345, -60)
    assert "positive" in result2.lower()
