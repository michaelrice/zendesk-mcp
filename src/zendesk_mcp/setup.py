import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, quote, urlparse

import httpx

from zendesk_mcp.config import config_path, save_config

REDIRECT_URI = "http://localhost:8787/callback"
CALLBACK_PORT = 8787
CALLBACK_TIMEOUT_SECONDS = 90


def _extract_code(raw: str) -> str | None:
    raw = raw.strip()
    if not raw:
        return None
    if "?" in raw or raw.startswith("http"):
        params = parse_qs(urlparse(raw).query)
        return params.get("code", [None])[0]
    return raw


def _exchange_code(subdomain: str, code: str, client_id: str, client_secret: str) -> str:
    response = httpx.post(
        f"https://{subdomain}.zendesk.com/oauth/tokens",
        json={
            "grant_type": "authorization_code",
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": REDIRECT_URI,
            "scope": "read write",
        },
        timeout=30,
    )
    response.raise_for_status()
    return response.json()["access_token"]


def _verify_token(subdomain: str, token: str) -> dict:
    response = httpx.get(
        f"https://{subdomain}.zendesk.com/api/v2/users/me.json",
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()["user"]


def run_setup() -> None:
    import os
    print("\n  zendesk-mcp setup\n")

    env_subdomain = os.environ.get("ZENDESK_SUBDOMAIN", "")
    env_client_id = os.environ.get("ZENDESK_CLIENT_ID", "")
    env_client_secret = os.environ.get("ZENDESK_CLIENT_SECRET", "")

    if env_subdomain:
        subdomain = env_subdomain
        print(f"  Zendesk subdomain: {subdomain} (from ZENDESK_SUBDOMAIN)")
    else:
        subdomain = input("  Zendesk subdomain (e.g. 'acme' for acme.zendesk.com): ").strip()

    if env_client_id:
        client_id = env_client_id
        print(f"  OAuth client_id: {client_id} (from ZENDESK_CLIENT_ID)")
    else:
        client_id = input("  OAuth client_id: ").strip()

    if env_client_secret:
        client_secret = env_client_secret
        print("  OAuth client_secret: *** (from ZENDESK_CLIENT_SECRET)")
    else:
        client_secret = input("  OAuth client_secret: ").strip()

    auth_url = (
        f"https://{subdomain}.zendesk.com/oauth/authorizations/new"
        f"?response_type=code"
        f"&redirect_uri={quote(REDIRECT_URI, safe='')}"
        f"&client_id={quote(client_id, safe='')}"
        f"&scope=read%20write"
    )

    code_holder: dict = {"code": None}

    class CallbackHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            params = parse_qs(urlparse(self.path).query)
            if "code" in params:
                code_holder["code"] = params["code"][0]
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"Authorization successful! You can close this tab.")
            else:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"No authorization code received.")

        def log_message(self, format, *args):
            pass

    server = HTTPServer(("localhost", CALLBACK_PORT), CallbackHandler)
    server.timeout = 1

    def _serve():
        import time
        deadline = time.time() + CALLBACK_TIMEOUT_SECONDS
        while code_holder["code"] is None and time.time() < deadline:
            server.handle_request()

    thread = threading.Thread(target=_serve, daemon=True)
    thread.start()

    print(f"\n  Opening browser for Zendesk authorization...")
    print(f"  Waiting up to {CALLBACK_TIMEOUT_SECONDS}s for callback on {REDIRECT_URI}\n")
    print(f"  If your browser is on a different machine, open this URL manually:")
    print(f"    {auth_url}\n")

    webbrowser.open(auth_url)

    thread.join(timeout=CALLBACK_TIMEOUT_SECONDS)

    if code_holder["code"] is None:
        print("  Callback not received automatically.")
        pasted = input("  Paste the full redirect URL (or just the code value) here: ").strip()
        code_holder["code"] = _extract_code(pasted)

    if not code_holder["code"]:
        print("\n  No authorization code received. Setup failed.\n")
        sys.exit(1)

    print("\n  Exchanging code for access token...")
    try:
        token = _exchange_code(subdomain, code_holder["code"], client_id, client_secret)
    except Exception as e:
        print(f"\n  Token exchange failed: {e}\n")
        sys.exit(1)

    print("  Verifying token...")
    try:
        user = _verify_token(subdomain, token)
    except Exception as e:
        print(f"\n  Token verification failed: {e}\n")
        sys.exit(1)

    role = user.get("role", "unknown")
    email = user.get("email", "unknown")

    git_zen_input = input(
        "  Git-Zen integration field ID (optional, press Enter to skip): "
    ).strip()
    config_data = {
        "subdomain": subdomain,
        "oauth_token": token,
        "attachment_cache_dir": "~/.cache/zendesk-mcp/attachments",
    }
    if git_zen_input:
        try:
            config_data["git_zen_field_id"] = int(git_zen_input)
        except ValueError:
            print(f"  Warning: '{git_zen_input}' is not a valid integer; skipping Git-Zen field ID.")

    save_config(config_data)

    cfg_path = config_path()
    if role == "admin":
        print(f"\n  Warning: connected as {email} (role: admin).")
        print("     Consider using a dedicated agent-role account for least-privilege access.")
    else:
        print(f"\n  Authorization successful.")
        print(f"  Verified: connected as {email} (role: {role})")

    print(f"  Token saved to {cfg_path}\n")
