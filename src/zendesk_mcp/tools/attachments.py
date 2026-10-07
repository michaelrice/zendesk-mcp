import base64
import json
import tarfile
import zipfile
from pathlib import Path
from urllib.parse import urlparse

import pdfplumber
from PIL import Image

from zendesk_mcp.client import get_client, ConfigError
from zendesk_mcp.config import attachment_cache_dir, load_config
from zendesk_mcp import auth
from zendesk_mcp.auth import api_error_message, TokenExpiredError


def _list_attachments_data(ticket_id: int) -> str:
    try:
        client = get_client()
        comments = client.tickets.comments(ticket_id)
        result = []
        for comment in comments:
            for att in (comment.attachments or []):
                result.append({
                    "comment_id": comment.id,
                    "filename": att.file_name,
                    "content_type": att.content_type,
                    "size_bytes": att.size,
                    "download_url": att.content_url,
                })
        return json.dumps(result, indent=2)
    except (ConfigError, TokenExpiredError) as e:
        return str(e)
    except Exception as e:
        if "RecordNotFound" in str(e) or "404" in str(e):
            return f"Ticket #{ticket_id} not found or not accessible with current credentials."
        return api_error_message(e)


_TEXT_EXTENSIONS = {".log", ".txt", ".json", ".yaml", ".yml", ".xml", ".csv", ".sh", ".py", ".go", ".md"}
_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}

# Bounds applied to tool response payloads to stay within MCP transport limits.
_ARCHIVE_FILE_LIST_CAP = 500
_PDF_TEXT_CAP_BYTES = 500_000

# Limits on unpacking untrusted archives (zip/tar bombs).
_ARCHIVE_MAX_MEMBERS = 10_000
_ARCHIVE_MAX_UNPACKED_BYTES = 256 * 1024 * 1024


def _validate_attachment_url(attachment_url: str) -> str | None:
    """Return an error message unless the URL points at the configured Zendesk host.

    The download is made with the OAuth bearer token attached, and the URL is supplied
    by the model (and so, indirectly, by whoever wrote the ticket). Pinning it to
    ``https://<subdomain>.zendesk.com`` keeps the token from being sent anywhere else.
    """
    subdomain = (load_config().get("subdomain") or "").strip().lower()
    if not subdomain:
        return "Zendesk not configured. Run: zendesk-mcp setup"
    parsed = urlparse(attachment_url)
    if parsed.scheme != "https" or (parsed.hostname or "").lower() != f"{subdomain}.zendesk.com":
        return (
            f"Refusing to download: attachment_url must be an https URL on "
            f"{subdomain}.zendesk.com (use the download_url from zendesk_list_attachments)."
        )
    return None


def _resolve_dest_dir(dest_dir: str, ticket_id: int) -> tuple[Path | None, str | None]:
    """Resolve a caller-supplied dest_dir, or explain why it is not allowed.

    The bytes written there come from a customer-controlled attachment, so an
    unrestricted dest_dir is an arbitrary file write. Only the attachment cache and
    directories listed under ``attachment_allowed_dest_dirs`` in the config are accepted.
    """
    target = Path(dest_dir).expanduser().resolve()
    cache_root = attachment_cache_dir(ticket_id).parent.expanduser().resolve()
    allowed = [cache_root] + [
        Path(p).expanduser().resolve()
        for p in (load_config().get("attachment_allowed_dest_dirs") or [])
    ]
    if any(target == root or root in target.parents for root in allowed):
        return target, None
    return None, (
        "dest_dir is not allowed. Use the default cache location, or add the directory "
        "to 'attachment_allowed_dest_dirs' in ~/.config/zendesk-mcp/config.json."
    )


def _download_attachment_data(
    attachment_url: str,
    filename: str,
    ticket_id: int,
    dest_dir: str | None = None,
) -> str:
    url_error = _validate_attachment_url(attachment_url)
    if url_error:
        return json.dumps({"type": "error", "message": url_error})
    if dest_dir:
        target_dir, dest_error = _resolve_dest_dir(dest_dir, ticket_id)
        if dest_error:
            return json.dumps({"type": "error", "message": dest_error})
    else:
        target_dir = attachment_cache_dir(ticket_id)
    target_dir.mkdir(parents=True, exist_ok=True)
    # Strip path components from filename to prevent directory traversal
    safe_filename = Path(filename).name
    dest = target_dir / safe_filename

    try:
        response = auth.request("GET", attachment_url, follow_redirects=True)
        response.raise_for_status()
        dest.write_bytes(response.content)
    except Exception as e:
        return json.dumps({
            "type": "error",
            "message": f"Download failed: {api_error_message(e)}",
            "cached_path": str(dest),
        })

    suffix = Path(filename).suffix.lower()

    if suffix in _TEXT_EXTENSIONS:
        try:
            text = dest.read_text(errors="replace")
            return json.dumps({"type": "text", "content": text, "cached_path": str(dest)})
        except Exception as e:
            return json.dumps({"type": "error", "message": str(e), "cached_path": str(dest)})

    if suffix == ".zip":
        return _handle_zip(dest)

    if suffix in {".tar", ".gz", ".tgz"} or filename.endswith(".tar.gz"):
        return _handle_tar(dest)

    if suffix == ".pdf":
        return _handle_pdf(dest)

    if suffix in _IMAGE_EXTENSIONS:
        return _handle_image(dest)

    return json.dumps({
        "type": "binary",
        "message": "Binary file — content not returned. Use cached_path to access it.",
        "cached_path": str(dest),
        "size_bytes": dest.stat().st_size,
    })


def _safe_zip_members(zf: zipfile.ZipFile, unpack_dir: Path) -> list:
    safe = []
    for member in zf.infolist():
        member_path = (unpack_dir / member.filename).resolve()
        if member_path.parts[:len(unpack_dir.resolve().parts)] == unpack_dir.resolve().parts:
            safe.append(member)
    return safe


def _archive_summary(dest: Path, unpack_dir: Path) -> str:
    all_paths = sorted(p for p in unpack_dir.rglob("*") if p.is_file())
    total_bytes = sum(p.stat().st_size for p in all_paths)
    file_list = [str(p.relative_to(unpack_dir)) for p in all_paths[:_ARCHIVE_FILE_LIST_CAP]]
    return json.dumps({
        "type": "archive",
        "unpack_dir": str(unpack_dir),
        "cached_path": str(dest),
        "file_count": len(all_paths),
        "total_bytes": total_bytes,
        "files": file_list,
        "truncated": len(all_paths) > _ARCHIVE_FILE_LIST_CAP,
    })


def _archive_limit_error(count: int, total_bytes: int) -> str | None:
    if count > _ARCHIVE_MAX_MEMBERS:
        return f"Archive has {count} entries; limit is {_ARCHIVE_MAX_MEMBERS}."
    if total_bytes > _ARCHIVE_MAX_UNPACKED_BYTES:
        return (
            f"Archive unpacks to {total_bytes} bytes; "
            f"limit is {_ARCHIVE_MAX_UNPACKED_BYTES}."
        )
    return None


def _handle_zip(dest: Path) -> str:
    unpack_dir = dest.parent / dest.stem
    try:
        with zipfile.ZipFile(dest) as zf:
            safe_members = _safe_zip_members(zf, unpack_dir)
            limit_error = _archive_limit_error(
                len(safe_members), sum(m.file_size for m in safe_members)
            )
            if limit_error:
                return json.dumps({"type": "error", "message": limit_error, "cached_path": str(dest)})
            for member in safe_members:
                zf.extract(member, unpack_dir)
        return _archive_summary(dest, unpack_dir)
    except zipfile.BadZipFile as e:
        return json.dumps({"type": "error", "message": f"Failed to unpack zip: {e}", "cached_path": str(dest)})


def _safe_tar_members(tf: tarfile.TarFile, unpack_dir: Path) -> list:
    """Regular files and directories that stay inside unpack_dir.

    Symlinks, hardlinks and device nodes are dropped: a link member can point outside
    unpack_dir, and a later member written "through" it would escape. The path check
    below runs before extraction, so it cannot see links that extraction would create.
    """
    root = unpack_dir.resolve()
    safe = []
    for member in tf.getmembers():
        if not (member.isreg() or member.isdir()):
            continue
        member_path = (unpack_dir / member.name).resolve()
        if member_path.parts[:len(root.parts)] == root.parts:
            safe.append(member)
    return safe


def _handle_tar(dest: Path) -> str:
    unpack_dir = dest.parent / dest.stem.replace(".tar", "")
    try:
        with tarfile.open(dest) as tf:
            safe_members = _safe_tar_members(tf, unpack_dir)
            limit_error = _archive_limit_error(
                len(safe_members), sum(m.size for m in safe_members)
            )
            if limit_error:
                return json.dumps({"type": "error", "message": limit_error, "cached_path": str(dest)})
            if hasattr(tarfile, "data_filter"):
                tf.extractall(unpack_dir, members=safe_members, filter="data")
            else:  # pragma: no cover - interpreters without extraction filters
                tf.extractall(unpack_dir, members=safe_members)
        return _archive_summary(dest, unpack_dir)
    except tarfile.TarError as e:
        return json.dumps({"type": "error", "message": f"Failed to unpack tar: {e}", "cached_path": str(dest)})


def _handle_pdf(dest: Path) -> str:
    try:
        with pdfplumber.open(dest) as pdf:
            chunks: list[str] = []
            size = 0
            truncated = False
            for page in pdf.pages:
                page_text = page.extract_text() or ""
                chunks.append(page_text)
                size += len(page_text) + 1
                if size >= _PDF_TEXT_CAP_BYTES:
                    truncated = True
                    break
            text = "\n".join(chunks)
        if truncated:
            text = text[:_PDF_TEXT_CAP_BYTES] + "\n[truncated]"
        return json.dumps({
            "type": "text",
            "content": text,
            "cached_path": str(dest),
            "truncated": truncated,
        })
    except Exception as e:
        return json.dumps({"type": "error", "message": f"PDF text extraction failed: {e}", "cached_path": str(dest)})


def _handle_image(dest: Path) -> str:
    try:
        import io
        with Image.open(dest) as img:
            buf = io.BytesIO()
            img.save(buf, format=img.format or "PNG")
            data = base64.b64encode(buf.getvalue()).decode()
        return json.dumps({
            "type": "image",
            "encoding": "base64",
            "data": data,
            "cached_path": str(dest),
        })
    except Exception as e:
        return json.dumps({"type": "error", "message": f"Image processing failed: {e}", "cached_path": str(dest)})


def register_attachment_tools(mcp) -> None:
    @mcp.tool()
    def zendesk_list_attachments(ticket_id: int) -> str:
        """List all attachments across all comments for a Zendesk ticket. Returns filename, content type, size, and download URL for each. Use zendesk_download_attachment to fetch file contents."""
        return _list_attachments_data(ticket_id)

    @mcp.tool()
    def zendesk_download_attachment(
        attachment_url: str,
        filename: str,
        ticket_id: int,
        dest_dir: str | None = None,
    ) -> str:
        """Download a Zendesk attachment. Obtain attachment_url and filename from zendesk_list_attachments. ticket_id is required for cache organization. Optional dest_dir overrides the default cache location (it must be inside the cache or a directory listed in 'attachment_allowed_dest_dirs' in the config); the file is written there and (for archives) extracted alongside it. Archives return a file list and unpack_dir — read individual files with your normal file tools. PDFs return up to ~500KB of extracted text. Images are base64-encoded."""
        return _download_attachment_data(attachment_url, filename, ticket_id, dest_dir)
