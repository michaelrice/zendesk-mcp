from unittest.mock import patch, MagicMock
from zendesk_mcp.client import ConfigError


@patch("zendesk_mcp.tools.write_comments.Ticket")
@patch("zendesk_mcp.tools.write_comments.Comment")
@patch("zendesk_mcp.tools.write_comments.get_client")
def test_post_comment_creates_public_comment(mock_get_client, mock_comment_cls, mock_ticket_cls):
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client

    mock_comment_instance = MagicMock()
    mock_comment_cls.return_value = mock_comment_instance

    mock_ticket_instance = MagicMock()
    mock_ticket_cls.return_value = mock_ticket_instance

    from zendesk_mcp.tools.write_comments import _post_comment_data
    result = _post_comment_data(12345, "We are investigating the issue.", public=True)

    mock_comment_cls.assert_called_once_with(body="We are investigating the issue.", public=True)
    mock_ticket_cls.assert_called_once_with(id=12345)
    assert mock_ticket_instance.comment == mock_comment_instance
    mock_client.tickets.update.assert_called_once_with(mock_ticket_instance)
    assert "12345" in result
    assert "public" in result.lower()


@patch("zendesk_mcp.tools.write_comments.Ticket")
@patch("zendesk_mcp.tools.write_comments.Comment")
@patch("zendesk_mcp.tools.write_comments.get_client")
def test_post_internal_note_sets_public_false(mock_get_client, mock_comment_cls, mock_ticket_cls):
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client

    mock_comment_cls.return_value = MagicMock()
    mock_ticket_cls.return_value = MagicMock()

    from zendesk_mcp.tools.write_comments import _post_comment_data
    result = _post_comment_data(12345, "Internal: escalate to tier 2.", public=False)

    mock_comment_cls.assert_called_once_with(body="Internal: escalate to tier 2.", public=False)
    assert "12345" in result
    assert "internal" in result.lower()


@patch("zendesk_mcp.tools.write_comments.get_client")
def test_post_comment_returns_error_on_config_error(mock_get_client):
    mock_get_client.side_effect = ConfigError("Zendesk not configured. Run: zendesk-mcp setup")

    from zendesk_mcp.tools.write_comments import _post_comment_data
    result = _post_comment_data(12345, "hello", public=True)

    assert "zendesk-mcp setup" in result


@patch("zendesk_mcp.tools.write_comments.Ticket")
@patch("zendesk_mcp.tools.write_comments.Comment")
@patch("zendesk_mcp.tools.write_comments.get_client")
def test_post_comment_returns_error_on_ticket_not_found(mock_get_client, mock_comment_cls, mock_ticket_cls):
    mock_client = MagicMock()
    mock_client.tickets.update.side_effect = Exception("RecordNotFound: Couldn't find Ticket with id=99999")
    mock_get_client.return_value = mock_client
    mock_comment_cls.return_value = MagicMock()
    mock_ticket_cls.return_value = MagicMock()

    from zendesk_mcp.tools.write_comments import _post_comment_data
    result = _post_comment_data(99999, "hello", public=True)

    assert "99999" in result
    assert "not found" in result.lower()
