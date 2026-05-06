import json
from unittest.mock import patch, MagicMock
from datetime import datetime


def _mk_section(section_id: int, name: str, description: str = ""):
    s = MagicMock()
    s.id = section_id
    s.name = name
    s.description = description
    return s


def _mk_article(article_id: int, title: str):
    a = MagicMock()
    a.id = article_id
    a.title = title
    a.body = "<p>article body</p>"
    a.updated_at = datetime(2026, 5, 1, 0, 0, 0)
    a.html_url = f"https://example.zendesk.com/hc/articles/{article_id}"
    return a


@patch("zendesk_mcp.tools.knowledge_base.get_client")
def test_get_knowledge_base_data_happy_path(mock_get_client):
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client

    section_a = _mk_section(1, "Getting Started", "intro")
    section_b = _mk_section(2, "FAQ", "")
    mock_client.help_center.sections.return_value = [section_a, section_b]

    def section_articles(section_id):
        if section_id == 1:
            return [_mk_article(10, "Welcome")]
        return [_mk_article(20, "Common questions"), _mk_article(21, "More questions")]

    mock_client.help_center.sections.articles.side_effect = section_articles

    from zendesk_mcp.tools.knowledge_base import _get_knowledge_base_data
    result = _get_knowledge_base_data()
    parsed = json.loads(result)

    assert "knowledge_base" in parsed
    assert "Getting Started" in parsed["knowledge_base"]
    assert parsed["knowledge_base"]["Getting Started"]["section_id"] == 1
    assert len(parsed["knowledge_base"]["Getting Started"]["articles"]) == 1
    assert parsed["knowledge_base"]["Getting Started"]["articles"][0]["id"] == 10
    assert parsed["knowledge_base"]["FAQ"]["section_id"] == 2
    assert len(parsed["knowledge_base"]["FAQ"]["articles"]) == 2

    assert parsed["metadata"]["sections"] == 2
    assert parsed["metadata"]["total_articles"] == 3


def test_register_knowledge_base_resource_skipped_when_disabled():
    from zendesk_mcp.tools.knowledge_base import register_knowledge_base_resource
    mcp = MagicMock()
    with patch("zendesk_mcp.tools.knowledge_base.load_config", return_value={}):
        register_knowledge_base_resource(mcp)
    mcp.resource.assert_not_called()


def test_register_knowledge_base_resource_active_when_enabled():
    from zendesk_mcp.tools.knowledge_base import register_knowledge_base_resource
    mcp = MagicMock()
    decorator = MagicMock(side_effect=lambda f: f)
    mcp.resource.return_value = decorator
    with patch("zendesk_mcp.tools.knowledge_base.load_config", return_value={"knowledge_base_enabled": True}):
        register_knowledge_base_resource(mcp)
    mcp.resource.assert_called_once()
    args, kwargs = mcp.resource.call_args
    assert args[0] == "zendesk://knowledge-base"
    assert kwargs.get("mime_type") == "application/json"
