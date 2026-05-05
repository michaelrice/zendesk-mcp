import json
from unittest.mock import patch, MagicMock
from tests.conftest import make_mock_ticket
from zendesk_mcp.client import ConfigError


@patch("zendesk_mcp.tools.ticket.get_client")
def test_get_ticket_returns_structured_fields(mock_get_client):
    mock_client = MagicMock()
    mock_client.tickets.return_value = make_mock_ticket()
    mock_get_client.return_value = mock_client

    from zendesk_mcp.tools.ticket import _get_ticket_data
    result = json.loads(_get_ticket_data(12345))

    assert result["id"] == 12345
    assert result["subject"] == "Login fails after password reset"
    assert result["status"] == "open"
    assert result["priority"] == "high"
    assert result["requester"]["email"] == "jane@customer.com"
    assert result["assignee"]["name"] == "Test Agent"
    assert result["group"] == "Support"
    assert "auth" in result["tags"]
    assert "zendesk.com" in result["ticket_url"]


@patch("zendesk_mcp.tools.ticket.get_client")
def test_get_ticket_returns_error_string_on_config_error(mock_get_client):
    mock_get_client.side_effect = ConfigError("Zendesk not configured. Run: zendesk-mcp setup")

    from zendesk_mcp.tools.ticket import _get_ticket_data
    result = _get_ticket_data(12345)

    assert "zendesk-mcp setup" in result
    assert not result.startswith("{")


@patch("zendesk_mcp.tools.ticket.get_client")
def test_get_ticket_returns_error_string_on_not_found(mock_get_client):
    mock_client = MagicMock()
    mock_client.tickets.side_effect = Exception("RecordNotFound: Couldn't find Ticket with id=99999")
    mock_get_client.return_value = mock_client

    from zendesk_mcp.tools.ticket import _get_ticket_data
    result = _get_ticket_data(99999)

    assert "99999" in result
    assert "not found" in result.lower()


@patch("zendesk_mcp.tools.ticket.get_client")
def test_search_tickets_with_keywords_includes_keyword_in_query(mock_get_client):
    mock_client = MagicMock()
    mock_client.search.return_value = iter([])
    mock_get_client.return_value = mock_client

    from zendesk_mcp.tools.ticket import _search_tickets_data
    _search_tickets_data(keywords="login failure", status=None, limit=10)

    call_args = mock_client.search.call_args
    assert "login failure" in call_args.kwargs["query"]
    assert "type:ticket" in call_args.kwargs["query"]


@patch("zendesk_mcp.tools.ticket.get_client")
def test_search_tickets_with_keywords_and_status(mock_get_client):
    mock_client = MagicMock()
    mock_client.search.return_value = iter([])
    mock_get_client.return_value = mock_client

    from zendesk_mcp.tools.ticket import _search_tickets_data
    _search_tickets_data(keywords="LDAP auth", status="open", limit=10)

    query = mock_client.search.call_args.kwargs["query"]
    assert "LDAP auth" in query
    assert "status:open" in query


@patch("zendesk_mcp.tools.ticket.get_client")
def test_search_tickets_no_keywords_behaves_as_before(mock_get_client):
    mock_client = MagicMock()
    mock_client.search.return_value = iter([])
    mock_get_client.return_value = mock_client

    from zendesk_mcp.tools.ticket import _search_tickets_data
    _search_tickets_data(keywords=None, status=None, limit=5)

    query = mock_client.search.call_args.kwargs["query"]
    assert query == "type:ticket"
