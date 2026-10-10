"""Access control and SSRF protection."""

import socket

import pytest

from tools import net_safety
from tools.net_safety import UnsafeURLError, check_url


def _resolve_to(monkeypatch, ip):
    monkeypatch.setattr(socket, "getaddrinfo", lambda host, port: [(None, None, None, None, (ip, port))])


@pytest.mark.parametrize("ip", ["127.0.0.1", "10.0.0.5", "192.168.1.1", "169.254.169.254", "::1", "::ffff:127.0.0.1"])
def test_private_addresses_blocked(monkeypatch, ip):
    _resolve_to(monkeypatch, ip)
    with pytest.raises(UnsafeURLError):
        check_url("http://internal.example/admin")


def test_public_address_allowed(monkeypatch):
    _resolve_to(monkeypatch, "93.184.216.34")
    check_url("https://example.com/page")


@pytest.mark.parametrize("url", ["file:///etc/passwd", "ftp://example.com/x", "http:///nohost"])
def test_bad_schemes_and_hosts_rejected(url):
    with pytest.raises(UnsafeURLError):
        check_url(url)


def test_redirect_to_private_address_blocked(monkeypatch):
    class Resp:
        is_redirect = True
        headers = {"Location": "http://127.0.0.1/secret"}

    class Session:
        def get(self, url, **kw):
            return Resp()

    def resolve(host, port):
        ip = "127.0.0.1" if host == "127.0.0.1" else "93.184.216.34"
        return [(None, None, None, None, (ip, port))]

    monkeypatch.setattr(socket, "getaddrinfo", resolve)
    with pytest.raises(UnsafeURLError):
        net_safety.safe_get(Session(), "https://example.com/r")


def test_summarize_url_reports_blocked_link(monkeypatch):
    from tools.url_tool import summarize_url

    _resolve_to(monkeypatch, "10.1.2.3")
    assert "private network" in summarize_url("http://router.local/")


# ── Telegram allowlist ───────────────────────────────────────────────────────

def test_telegram_allowlist():
    import telegram_bot

    assert telegram_bot.is_allowed(111)       # from TELEGRAM_ALLOWED_USER_IDS in conftest
    assert not telegram_bot.is_allowed(222)
    assert not telegram_bot.is_allowed(None)


# ── HTTP API auth ────────────────────────────────────────────────────────────

@pytest.fixture
def api(monkeypatch):
    from fastapi.testclient import TestClient

    from app import api as api_module
    from core.handlers.base import Reply

    monkeypatch.setattr(api_module, "respond", lambda text, **kw: Reply(f"echo:{text}"))
    return api_module, TestClient(api_module.app)


def test_api_rejects_remote_without_token(api):
    _, client = api  # TestClient's host is "testclient", not localhost
    assert client.post("/chat", data={"message": "hi"}).status_code == 403


def test_api_token(api, monkeypatch):
    module, client = api
    monkeypatch.setattr(module.settings, "API_TOKEN", "s3cret")
    assert client.post("/chat", data={"message": "hi"}).status_code == 401
    ok = client.post("/chat", data={"message": "hi"}, headers={"Authorization": "Bearer s3cret"})
    assert ok.status_code == 200 and ok.json()["answer"] == "echo:hi"


def test_api_validates_model(api, monkeypatch):
    module, client = api
    monkeypatch.setattr(module.settings, "API_TOKEN", "t")
    r = client.post("/chat", data={"message": "hi", "model_type": "gpt"}, headers={"Authorization": "Bearer t"})
    assert r.status_code == 422
