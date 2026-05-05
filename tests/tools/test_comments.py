import json
from datetime import datetime
from unittest.mock import patch, MagicMock
from tests.conftest import make_mock_comment, make_mock_attachment, make_mock_user
from zendesk_mcp.client import ConfigError


def _make_client_with_comments(comments):
    mock_client = MagicMock()
    mock_client.tickets.comments.return_value = iter(comments)
    mock_client.users.return_value = make_mock_user()
    return mock_client


@patch("zendesk_mcp.tools.comments.get_client")
def test_get_comments_returns_list(mock_get_client):
    comment = make_mock_comment(comment_id=1, body="Please help.", public=True)
    mock_get_client.return_value = _make_client_with_comments([comment])

    from zendesk_mcp.tools.comments import _get_comments_data
    result = json.loads(_get_comments_data(12345))

    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]["id"] == 1
    assert result[0]["body"] == "Please help."
    assert result[0]["is_public"] is True


@patch("zendesk_mcp.tools.comments.get_client")
def test_get_comments_includes_attachment_metadata(mock_get_client):
    att = make_mock_attachment("bundle.zip", "application/zip", 2048, "https://cdn.zendesk.com/1")
    comment = make_mock_comment(comment_id=2, attachments=[att])
    mock_get_client.return_value = _make_client_with_comments([comment])

    from zendesk_mcp.tools.comments import _get_comments_data
    result = json.loads(_get_comments_data(12345))

    attachments = result[0]["attachments"]
    assert len(attachments) == 1
    assert attachments[0]["filename"] == "bundle.zip"
    assert attachments[0]["content_type"] == "application/zip"
    assert attachments[0]["size_bytes"] == 2048
    assert "content_url" in attachments[0]


@patch("zendesk_mcp.tools.comments.get_client")
def test_get_comments_returns_error_on_config_error(mock_get_client):
    mock_get_client.side_effect = ConfigError("Zendesk not configured. Run: zendesk-mcp setup")

    from zendesk_mcp.tools.comments import _get_comments_data
    result = _get_comments_data(12345)

    assert "zendesk-mcp setup" in result
    assert not result.startswith("[")
