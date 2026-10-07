import json
import os
import tempfile
from pathlib import Path


def config_path() -> Path:
    return Path.home() / ".config" / "zendesk-mcp" / "config.json"


def load_config(path: Path | None = None) -> dict:
    resolved = path or config_path()
    try:
        return json.loads(resolved.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_config(data: dict, path: Path | None = None) -> None:
    """Write the config atomically, readable only by the owner from the moment it exists.

    The file holds OAuth tokens and the client secret. Writing it with write_text() and
    chmod-ing afterwards leaves a window where it is world-readable under a permissive
    umask, and a crash mid-write leaves a truncated file that load_config() reads as empty,
    losing the rotated refresh token. mkstemp creates the file 0600, and os.replace swaps it
    in as a single step.
    """
    resolved = path or config_path()
    resolved.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, tmp_name = tempfile.mkstemp(dir=resolved.parent, prefix=f"{resolved.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as tmp:
            tmp.write(json.dumps(data, indent=2) + "\n")
            tmp.flush()
            os.fsync(tmp.fileno())
        os.replace(tmp_name, resolved)
    except BaseException:
        try:
            os.unlink(tmp_name)
        except FileNotFoundError:
            pass
        raise


def attachment_cache_dir(ticket_id: int, config_file: Path | None = None) -> Path:
    cfg = load_config(config_file)
    base = cfg.get("attachment_cache_dir", "~/.cache/zendesk-mcp/attachments")
    return Path(base).expanduser() / str(ticket_id)
