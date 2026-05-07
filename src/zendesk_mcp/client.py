from pathlib import Path
from zenpy import Zenpy
from zendesk_mcp.config import load_config


class ConfigError(Exception):
    pass


def get_client(config_file: Path | None = None) -> Zenpy:
    cfg = load_config(config_file)
    subdomain = cfg.get("subdomain", "").strip()
    token = cfg.get("oauth_token", "").strip()
    if not subdomain or not token:
        raise ConfigError("Zendesk not configured. Run: zendesk-mcp setup")
    return Zenpy(subdomain=subdomain, oauth_token=token)


def get_oauth_session() -> tuple[str, str]:
    """Return (subdomain, oauth_token) for direct API calls. Raises ConfigError if unconfigured."""
    cfg = load_config()
    subdomain = cfg.get("subdomain", "").strip()
    token = cfg.get("oauth_token", "").strip()
    if not subdomain or not token:
        raise ConfigError("Zendesk not configured. Run: zendesk-mcp setup")
    return subdomain, token
