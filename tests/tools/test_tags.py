import json
from unittest.mock import patch, MagicMock
from zendesk_mcp.client import ConfigError


def _make_ticket(ticket_id: int, tags: list):
    t = MagicMock()
    t.id = ticket_id
    t.tags = list(tags)
    return t


@patch("zendesk_mcp.tools.tags.get_client")
def test_add_tag_appends_new_tag(mock_get_client):
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    loaded = _make_ticket(10, ["existing"])
    refreshed = _make_ticket(10, ["existing", "newtag"])
    mock_client.tickets.side_effect = [loaded, refreshed]

    from zendesk_mcp.tools.tags import _add_tag_data
    result = _add_tag_data(10, "newtag")

    mock_client.tickets.update.assert_called_once_with(loaded)
    parsed = json.loads(result)
    assert parsed["ticket_id"] == 10
    assert "newtag" in parsed["tags"]
    assert "existing" in parsed["tags"]


@patch("zendesk_mcp.tools.tags.get_client")
def test_add_tag_is_idempotent_when_tag_exists(mock_get_client):
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    loaded = _make_ticket(10, ["existing"])
    mock_client.tickets.return_value = loaded

    from zendesk_mcp.tools.tags import _add_tag_data
    result = _add_tag_data(10, "existing")

    mock_client.tickets.update.assert_not_called()
    parsed = json.loads(result)
    assert parsed["tags"] == ["existing"]


@patch("zendesk_mcp.tools.tags.get_client")
def test_remove_tag_removes_existing_tag(mock_get_client):
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    loaded = _make_ticket(10, ["keep", "remove-me"])
    refreshed = _make_ticket(10, ["keep"])
    mock_client.tickets.side_effect = [loaded, refreshed]

    from zendesk_mcp.tools.tags import _remove_tag_data
    result = _remove_tag_data(10, "remove-me")

    mock_client.tickets.update.assert_called_once_with(loaded)
    parsed = json.loads(result)
    assert "remove-me" not in parsed["tags"]
    assert "keep" in parsed["tags"]


@patch("zendesk_mcp.tools.tags.get_client")
def test_remove_tag_is_idempotent_when_tag_missing(mock_get_client):
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    loaded = _make_ticket(10, ["only"])
    mock_client.tickets.return_value = loaded

    from zendesk_mcp.tools.tags import _remove_tag_data
    result = _remove_tag_data(10, "ghost")

    mock_client.tickets.update.assert_not_called()
    parsed = json.loads(result)
    assert parsed["tags"] == ["only"]


@patch("zendesk_mcp.tools.tags.get_client")
def test_add_tag_returns_error_on_config_error(mock_get_client):
    mock_get_client.side_effect = ConfigError("Zendesk not configured. Run: zendesk-mcp setup")
    from zendesk_mcp.tools.tags import _add_tag_data
    result = _add_tag_data(10, "tag")
    assert "zendesk-mcp setup" in result


@patch("zendesk_mcp.tools.tags.get_client")
def test_add_tag_returns_error_on_not_found(mock_get_client):
    mock_client = MagicMock()
    mock_client.tickets.side_effect = Exception("RecordNotFound: Couldn't find Ticket")
    mock_get_client.return_value = mock_client
    from zendesk_mcp.tools.tags import _add_tag_data
    result = _add_tag_data(99, "tag")
    assert "99" in result
    assert "not found" in result.lower()
