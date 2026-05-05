from unittest.mock import patch, MagicMock
from tests.conftest import make_mock_ticket, make_mock_comment, make_mock_user
from zendesk_mcp.client import ConfigError


def _client_with_ticket_and_comments(ticket, comments):
    mock_client = MagicMock()
    mock_client.tickets.return_value = ticket
    mock_client.tickets.comments.return_value = iter(comments)
    mock_client.users.return_value = make_mock_user()
    return mock_client


@patch("zendesk_mcp.tools.gitlab_context.load_config")
@patch("zendesk_mcp.tools.gitlab_context.get_client")
def test_gitlab_context_contains_ticket_metadata(mock_get_client, mock_load_config):
    mock_load_config.return_value = {"subdomain": "example"}
    ticket = make_mock_ticket(ticket_id=12345, subject="Login fails after password reset")
    comment = make_mock_comment(comment_id=1, body="User can't log in.", public=True)
    mock_get_client.return_value = _client_with_ticket_and_comments(ticket, [comment])

    from zendesk_mcp.tools.gitlab_context import _get_gitlab_context
    result = _get_gitlab_context(12345)

    assert "12345" in result
    assert "Login fails after password reset" in result
    assert "jane@customer.com" in result
    assert "example.zendesk.com" in result


@patch("zendesk_mcp.tools.gitlab_context.load_config")
@patch("zendesk_mcp.tools.gitlab_context.get_client")
def test_gitlab_context_includes_public_comments(mock_get_client, mock_load_config):
    mock_load_config.return_value = {"subdomain": "example"}
    ticket = make_mock_ticket()
    public = make_mock_comment(comment_id=1, body="User reports crash.", public=True)
    internal = make_mock_comment(comment_id=2, body="Internal: looks like a DB issue.", public=False)
    mock_get_client.return_value = _client_with_ticket_and_comments(ticket, [public, internal])

    from zendesk_mcp.tools.gitlab_context import _get_gitlab_context
    result = _get_gitlab_context(12345)

    assert "User reports crash." in result
    assert "Internal: looks like a DB issue." in result
    assert "[Internal Note]" in result


@patch("zendesk_mcp.tools.gitlab_context.get_client")
def test_gitlab_context_returns_error_on_config_error(mock_get_client):
    mock_get_client.side_effect = ConfigError("Zendesk not configured. Run: zendesk-mcp setup")

    from zendesk_mcp.tools.gitlab_context import _get_gitlab_context
    result = _get_gitlab_context(12345)

    assert "zendesk-mcp setup" in result
    assert not result.startswith("#")


@patch("zendesk_mcp.tools.gitlab_context.load_config")
@patch("zendesk_mcp.tools.gitlab_context.get_client")
def test_gitlab_context_contains_issue_template_sections(mock_get_client, mock_load_config):
    mock_load_config.return_value = {"subdomain": "example"}
    ticket = make_mock_ticket()
    comment = make_mock_comment()
    mock_get_client.return_value = _client_with_ticket_and_comments(ticket, [comment])

    from zendesk_mcp.tools.gitlab_context import _get_gitlab_context
    result = _get_gitlab_context(12345)

    assert "## Description" in result
    assert "## Steps to Reproduce" in result
    assert "## Environment" not in result
    assert "DRP version" not in result
