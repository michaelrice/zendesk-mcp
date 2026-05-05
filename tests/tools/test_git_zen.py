import json
from unittest.mock import patch, MagicMock
from zendesk_mcp.client import ConfigError

_TEST_FIELD_ID = 999

_SAMPLE_GIT_ZEN_JSON = json.dumps({
    "fileGroup": [],
    "commitGroup": [],
    "issueGroup": [
        {
            "name": "widgets",
            "owner": "acme",
            "issues": [
                {
                    "name": "Widget renderer crashes on empty input",
                    "link": "https://gitlab.com/acme/widgets/-/work_items/1375",
                    "number": "1375",
                    "id": "1375",
                    "state": "closed",
                    "labels": [{"name": "status::in-progress", "color": "#c39953"}],
                    "milestone": None,
                    "weight": "2",
                    "iteration": "",
                    "pullRequests": [],
                }
            ],
        }
    ],
})


def _make_ticket_with_git_zen(git_zen_json, field_id=_TEST_FIELD_ID):
    ticket = MagicMock()
    ticket.custom_fields = [
        {"id": field_id, "value": git_zen_json},
    ]
    return ticket


@patch("zendesk_mcp.tools.git_zen.load_config")
@patch("zendesk_mcp.tools.git_zen.get_client")
def test_get_git_zen_links_returns_parsed_issues(mock_get_client, mock_load_config):
    mock_load_config.return_value = {"git_zen_field_id": _TEST_FIELD_ID}
    mock_client = MagicMock()
    mock_client.tickets.return_value = _make_ticket_with_git_zen(_SAMPLE_GIT_ZEN_JSON)
    mock_get_client.return_value = mock_client

    from zendesk_mcp.tools.git_zen import _get_git_zen_links_data
    result = json.loads(_get_git_zen_links_data(3031))

    assert result["ticket_id"] == 3031
    assert len(result["linked_issues"]) == 1
    issue = result["linked_issues"][0]
    assert issue["project"] == "acme/widgets"
    assert issue["number"] == "1375"
    assert issue["title"] == "Widget renderer crashes on empty input"
    assert issue["state"] == "closed"
    assert "status::in-progress" in issue["labels"]
    assert issue["weight"] == "2"
    assert result["linked_mrs"] == []
    assert result["linked_commits"] == []


@patch("zendesk_mcp.tools.git_zen.load_config")
@patch("zendesk_mcp.tools.git_zen.get_client")
def test_get_git_zen_links_returns_empty_when_no_field(mock_get_client, mock_load_config):
    mock_load_config.return_value = {"git_zen_field_id": _TEST_FIELD_ID}
    mock_client = MagicMock()
    ticket = MagicMock()
    ticket.custom_fields = []
    mock_client.tickets.return_value = ticket
    mock_get_client.return_value = mock_client

    from zendesk_mcp.tools.git_zen import _get_git_zen_links_data
    result = json.loads(_get_git_zen_links_data(12345))

    assert result["linked_issues"] == []
    assert result["linked_mrs"] == []
    assert result["linked_commits"] == []


@patch("zendesk_mcp.tools.git_zen.load_config")
@patch("zendesk_mcp.tools.git_zen.get_client")
def test_get_git_zen_links_returns_error_on_config_error(mock_get_client, mock_load_config):
    mock_load_config.return_value = {"git_zen_field_id": _TEST_FIELD_ID}
    mock_get_client.side_effect = ConfigError("Zendesk not configured. Run: zendesk-mcp setup")

    from zendesk_mcp.tools.git_zen import _get_git_zen_links_data
    result = _get_git_zen_links_data(12345)

    assert "zendesk-mcp setup" in result


@patch("zendesk_mcp.tools.git_zen.load_config")
@patch("zendesk_mcp.tools.git_zen.get_client")
def test_get_git_zen_links_returns_error_on_not_found(mock_get_client, mock_load_config):
    mock_load_config.return_value = {"git_zen_field_id": _TEST_FIELD_ID}
    mock_client = MagicMock()
    mock_client.tickets.side_effect = Exception("RecordNotFound: Couldn't find Ticket with id=99999")
    mock_get_client.return_value = mock_client

    from zendesk_mcp.tools.git_zen import _get_git_zen_links_data
    result = _get_git_zen_links_data(99999)

    assert "99999" in result
    assert "not found" in result.lower()


@patch("zendesk_mcp.tools.git_zen.load_config")
def test_get_git_zen_links_returns_not_configured_message_when_field_id_unset(mock_load_config):
    mock_load_config.return_value = {}

    from zendesk_mcp.tools.git_zen import _get_git_zen_links_data
    result = _get_git_zen_links_data(12345)

    assert "Git-Zen field ID not configured" in result
    assert "git_zen_field_id" in result
    assert "~/.config/zendesk-mcp/config.json" in result
