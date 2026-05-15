import json
import zipfile
import tarfile
import base64
from pathlib import Path
from unittest.mock import patch, MagicMock
from tests.conftest import make_mock_attachment, make_mock_comment
from zendesk_mcp.client import ConfigError


def _client_with_comments(comments):
    mock_client = MagicMock()
    mock_client.tickets.comments.return_value = iter(comments)
    return mock_client


@patch("zendesk_mcp.tools.attachments.get_client")
def test_list_attachments_aggregates_across_comments(mock_get_client):
    att1 = make_mock_attachment("debug.log", "text/plain", 512, "https://cdn.zendesk.com/1")
    att2 = make_mock_attachment("bundle.zip", "application/zip", 4096, "https://cdn.zendesk.com/2")
    c1 = make_mock_comment(comment_id=1, attachments=[att1])
    c2 = make_mock_comment(comment_id=2, attachments=[att2])
    mock_get_client.return_value = _client_with_comments([c1, c2])

    from zendesk_mcp.tools.attachments import _list_attachments_data
    result = json.loads(_list_attachments_data(12345))

    assert len(result) == 2
    assert result[0]["comment_id"] == 1
    assert result[0]["filename"] == "debug.log"
    assert result[1]["filename"] == "bundle.zip"
    assert result[1]["size_bytes"] == 4096


@patch("zendesk_mcp.tools.attachments.get_client")
def test_list_attachments_returns_empty_list_when_no_attachments(mock_get_client):
    c = make_mock_comment(comment_id=1, attachments=[])
    mock_get_client.return_value = _client_with_comments([c])

    from zendesk_mcp.tools.attachments import _list_attachments_data
    result = json.loads(_list_attachments_data(12345))

    assert result == []


@patch("zendesk_mcp.tools.attachments.get_client")
def test_list_attachments_returns_error_on_config_error(mock_get_client):
    mock_get_client.side_effect = ConfigError("Zendesk not configured. Run: zendesk-mcp setup")

    from zendesk_mcp.tools.attachments import _list_attachments_data
    result = _list_attachments_data(12345)

    assert "zendesk-mcp setup" in result


@patch("zendesk_mcp.tools.attachments.load_config")
@patch("zendesk_mcp.tools.attachments.httpx.get")
def test_download_text_file_returns_content(mock_httpx_get, mock_load_config, tmp_path):
    mock_load_config.return_value = {
        "oauth_token": "tok",
        "attachment_cache_dir": str(tmp_path / "attachments"),
    }
    mock_httpx_get.return_value = MagicMock(
        content=b"ERROR: disk full\nstack trace here",
        raise_for_status=lambda: None,
    )

    from zendesk_mcp.tools.attachments import _download_attachment_data
    result = json.loads(_download_attachment_data("https://cdn.zendesk.com/debug.log", "debug.log", 12345))

    assert result["type"] == "text"
    assert "disk full" in result["content"]
    assert result["cached_path"].endswith("12345/debug.log")


@patch("zendesk_mcp.tools.attachments.load_config")
@patch("zendesk_mcp.tools.attachments.httpx.get")
def test_download_zip_returns_file_tree(mock_httpx_get, mock_load_config, tmp_path):
    mock_load_config.return_value = {
        "oauth_token": "tok",
        "attachment_cache_dir": str(tmp_path / "attachments"),
    }
    import io
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("readme.txt", "hello from zip")
    mock_httpx_get.return_value = MagicMock(
        content=buf.getvalue(),
        raise_for_status=lambda: None,
    )

    from zendesk_mcp.tools.attachments import _download_attachment_data
    result = json.loads(_download_attachment_data("https://cdn.zendesk.com/bundle.zip", "bundle.zip", 12345))

    assert result["type"] == "archive"
    assert any("readme.txt" in f for f in result["files"])
    assert result["file_count"] == 1
    assert result["truncated"] is False
    assert result["unpack_dir"].endswith("12345/bundle")
    # Body of files is not inlined — caller reads from unpack_dir
    assert "text_contents" not in result
    unpack_dir = Path(result["unpack_dir"])
    assert (unpack_dir / "readme.txt").read_text() == "hello from zip"


@patch("zendesk_mcp.tools.attachments.load_config")
@patch("zendesk_mcp.tools.attachments.httpx.get")
def test_download_zip_caps_file_list_when_large(mock_httpx_get, mock_load_config, tmp_path):
    mock_load_config.return_value = {
        "oauth_token": "tok",
        "attachment_cache_dir": str(tmp_path / "attachments"),
    }
    import io
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for i in range(600):
            zf.writestr(f"f{i:04d}.log", "x")
    mock_httpx_get.return_value = MagicMock(
        content=buf.getvalue(),
        raise_for_status=lambda: None,
    )

    from zendesk_mcp.tools.attachments import _download_attachment_data
    result = json.loads(_download_attachment_data("https://cdn.zendesk.com/big.zip", "big.zip", 12345))

    assert result["file_count"] == 600
    assert len(result["files"]) == 500
    assert result["truncated"] is True


@patch("zendesk_mcp.tools.attachments.load_config")
@patch("zendesk_mcp.tools.attachments.httpx.get")
def test_download_with_dest_dir_uses_override(mock_httpx_get, mock_load_config, tmp_path):
    mock_load_config.return_value = {
        "oauth_token": "tok",
        "attachment_cache_dir": str(tmp_path / "cache"),
    }
    mock_httpx_get.return_value = MagicMock(
        content=b"hello",
        raise_for_status=lambda: None,
    )

    override = tmp_path / "workspace" / "bundles" / "12345"
    from zendesk_mcp.tools.attachments import _download_attachment_data
    result = json.loads(_download_attachment_data(
        "https://cdn.zendesk.com/notes.txt", "notes.txt", 12345, str(override)
    ))

    assert result["cached_path"] == str(override / "notes.txt")
    assert not (tmp_path / "cache").exists()


@patch("zendesk_mcp.tools.attachments.load_config")
@patch("zendesk_mcp.tools.attachments.httpx.get")
def test_download_image_returns_base64(mock_httpx_get, mock_load_config, tmp_path):
    mock_load_config.return_value = {
        "oauth_token": "tok",
        "attachment_cache_dir": str(tmp_path / "attachments"),
    }
    import io
    from PIL import Image
    img = Image.new("RGB", (1, 1), color=(255, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    mock_httpx_get.return_value = MagicMock(
        content=buf.getvalue(),
        raise_for_status=lambda: None,
    )

    from zendesk_mcp.tools.attachments import _download_attachment_data
    result = json.loads(_download_attachment_data("https://cdn.zendesk.com/screen.png", "screen.png", 12345))

    assert result["type"] == "image"
    assert result["encoding"] == "base64"
    assert len(result["data"]) > 0


@patch("zendesk_mcp.tools.attachments.load_config")
@patch("zendesk_mcp.tools.attachments.httpx.get")
def test_download_corrupt_zip_returns_error_not_exception(mock_httpx_get, mock_load_config, tmp_path):
    mock_load_config.return_value = {
        "oauth_token": "tok",
        "attachment_cache_dir": str(tmp_path / "attachments"),
    }
    mock_httpx_get.return_value = MagicMock(
        content=b"this is not a zip",
        raise_for_status=lambda: None,
    )

    from zendesk_mcp.tools.attachments import _download_attachment_data
    result = json.loads(_download_attachment_data("https://cdn.zendesk.com/bad.zip", "bad.zip", 12345))

    assert result["type"] == "error"
    assert "unpack" in result["message"].lower() or "zip" in result["message"].lower()
    assert "cached_path" in result


@patch("zendesk_mcp.tools.attachments.load_config")
@patch("zendesk_mcp.tools.attachments.httpx.get")
def test_download_tar_returns_file_tree(mock_httpx_get, mock_load_config, tmp_path):
    mock_load_config.return_value = {
        "oauth_token": "tok",
        "attachment_cache_dir": str(tmp_path / "attachments"),
    }
    import io
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tf:
        content = b"hello from tar"
        info = tarfile.TarInfo(name="readme.txt")
        info.size = len(content)
        tf.addfile(info, io.BytesIO(content))
    mock_httpx_get.return_value = MagicMock(
        content=buf.getvalue(),
        raise_for_status=lambda: None,
    )

    from zendesk_mcp.tools.attachments import _download_attachment_data
    result = json.loads(_download_attachment_data("https://cdn.zendesk.com/logs.tar.gz", "logs.tar.gz", 12345))

    assert result["type"] == "archive"
    assert any("readme.txt" in f for f in result["files"])
    assert result["file_count"] == 1
    assert "text_contents" not in result
    unpack_dir = Path(result["unpack_dir"])
    assert (unpack_dir / "readme.txt").read_text() == "hello from tar"
