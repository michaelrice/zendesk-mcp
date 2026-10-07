from unittest.mock import MagicMock

from zendesk_mcp.tools.channel import ticket_channel


def test_channel_from_zenpy_style_object():
    via = MagicMock()
    via.channel = "web"
    ticket = MagicMock()
    ticket.via = via
    assert ticket_channel(ticket) == "web"


def test_channel_from_raw_api_dict():
    assert ticket_channel({"id": 1, "via": {"channel": "api"}}) == "api"


def test_channel_is_none_when_via_missing():
    assert ticket_channel({"id": 1}) is None
    assert ticket_channel({"id": 1, "via": {}}) is None


def test_channel_is_none_when_not_a_string():
    ticket = MagicMock()  # via.channel is itself a MagicMock
    assert ticket_channel(ticket) is None
