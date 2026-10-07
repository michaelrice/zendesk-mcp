import threading
import urllib.error
import urllib.request
from http.server import HTTPServer
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

import httpx

from zendesk_mcp.setup import (
    _authorization_url,
    _exchange_code,
    _extract_code,
    _make_callback_handler,
)


def _post_response(**extra):
    body = {
        "access_token": "acc-tok",
        "token_type": "bearer",
        "scope": "read write",
    }
    body.update(extra)
    return httpx.Response(
        status_code=200,
        json=body,
        request=httpx.Request("POST", "https://acme.zendesk.com/oauth/tokens"),
    )


@patch("zendesk_mcp.setup.httpx.post")
def test_exchange_code_retains_refresh_token_and_expiry(mock_post):
    mock_post.return_value = _post_response(
        refresh_token="ref-tok", expires_in=86400, refresh_token_expires_in=2592000
    )

    result = _exchange_code("acme", "the-code", "cid", "secret", now=1000)

    assert result["access_token"] == "acc-tok"
    assert result["refresh_token"] == "ref-tok"
    assert result["expires_at"] == 1000 + 86400


@patch("zendesk_mcp.setup.httpx.post")
def test_exchange_code_requests_an_expiry_so_legacy_clients_get_refresh_tokens(mock_post):
    """Zendesk only issues a refresh token for a legacy client if expires_in is passed explicitly."""
    mock_post.return_value = _post_response(refresh_token="ref-tok", expires_in=86400)

    _exchange_code("acme", "the-code", "cid", "secret", now=1000)

    sent = mock_post.call_args.kwargs["json"]
    assert sent["grant_type"] == "authorization_code"
    assert "expires_in" in sent
    assert "refresh_token_expires_in" in sent


@patch("zendesk_mcp.setup.httpx.post")
def test_exchange_code_tolerates_server_omitting_refresh_token(mock_post):
    """A non-expiring legacy token must still configure cleanly, just without refresh."""
    mock_post.return_value = _post_response()

    result = _exchange_code("acme", "the-code", "cid", "secret", now=1000)

    assert result["access_token"] == "acc-tok"
    assert result.get("refresh_token") is None
    assert result.get("expires_at") is None


# --- OAuth state (CSRF) ----------------------------------------------------


def test_authorization_url_carries_the_state():
    url = _authorization_url("acme", "cid", "s t&te")
    params = parse_qs(urlparse(url).query)
    assert params["state"] == ["s t&te"]
    assert params["client_id"] == ["cid"]
    assert params["response_type"] == ["code"]


def test_extract_code_accepts_a_redirect_url_with_matching_state():
    url = "http://localhost:8787/callback?code=abc&state=good"
    assert _extract_code(url, "good") == "abc"


def test_extract_code_rejects_a_redirect_url_with_wrong_or_missing_state():
    assert _extract_code("http://localhost:8787/callback?code=abc&state=evil", "good") is None
    assert _extract_code("http://localhost:8787/callback?code=abc", "good") is None


def test_extract_code_still_accepts_a_bare_code_and_urls_when_no_state_expected():
    assert _extract_code("abc", "good") == "abc"
    assert _extract_code("http://localhost:8787/callback?code=abc") == "abc"
    assert _extract_code("   ", "good") is None


def _get(port: int, query: str) -> int:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/callback?{query}", timeout=5) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code


def test_callback_ignores_a_code_without_the_expected_state_and_keeps_listening():
    holder = {"code": None}
    server = HTTPServer(("127.0.0.1", 0), _make_callback_handler(holder, "good"))
    server.timeout = 5
    port = server.server_address[1]
    served = threading.Thread(target=lambda: [server.handle_request() for _ in range(3)], daemon=True)
    served.start()
    try:
        assert _get(port, "code=attacker") == 400
        assert holder["code"] is None
        assert _get(port, "code=attacker&state=evil") == 400
        assert holder["code"] is None
        assert _get(port, "code=real&state=good") == 200
        assert holder["code"] == "real"
    finally:
        served.join(timeout=10)
        server.server_close()


# --- credential prompts ------------------------------------------------------


@patch("zendesk_mcp.setup.getpass")
@patch("zendesk_mcp.setup.input")
def test_collect_credentials_reads_the_secret_without_echo(mock_input, mock_getpass):
    from zendesk_mcp.setup import _collect_credentials
    mock_input.side_effect = ["acme", "cid"]
    mock_getpass.return_value = "s3cret"

    assert _collect_credentials({}) == ("acme", "cid", "s3cret")
    prompts = [c.args[0] for c in mock_input.call_args_list]
    assert not any("secret" in p.lower() for p in prompts)
    mock_getpass.assert_called_once()


@patch("zendesk_mcp.setup.getpass")
@patch("zendesk_mcp.setup.input")
def test_collect_credentials_prefers_environment_and_prompts_for_nothing(mock_input, mock_getpass):
    from zendesk_mcp.setup import _collect_credentials
    env = {
        "ZENDESK_SUBDOMAIN": "acme",
        "ZENDESK_CLIENT_ID": "cid",
        "ZENDESK_CLIENT_SECRET": "s3cret",
    }

    assert _collect_credentials(env) == ("acme", "cid", "s3cret")
    mock_input.assert_not_called()
    mock_getpass.assert_not_called()
