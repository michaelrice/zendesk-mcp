import json
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
    resolved = path or config_path()
    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text(json.dumps(data, indent=2) + "\n")
    resolved.chmod(0o600)


def attachment_cache_dir(ticket_id: int, config_file: Path | None = None) -> Path:
    cfg = load_config(config_file)
    base = cfg.get("attachment_cache_dir", "~/.cache/zendesk-mcp/attachments")
    return Path(base).expanduser() / str(ticket_id)
