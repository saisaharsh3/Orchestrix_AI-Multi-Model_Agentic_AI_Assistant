"""
net_safety.py - Guard against server-side request forgery (SSRF).

URL tools fetch whatever link a chat user sends. Without a check, a message
like "summarize http://192.168.1.1/admin" makes this machine fetch pages on
your private network. Only public http(s) addresses are allowed unless
ALLOW_PRIVATE_URLS=true.
"""

import ipaddress
import socket
from urllib.parse import urljoin, urlparse

import requests

from config.settings import settings

MAX_REDIRECTS = 5


class UnsafeURLError(ValueError):
    pass


def _is_public_ip(ip: str) -> bool:
    addr = ipaddress.ip_address(ip)
    if isinstance(addr, ipaddress.IPv6Address) and addr.ipv4_mapped:
        addr = addr.ipv4_mapped
    return addr.is_global and not addr.is_multicast


def check_url(url: str) -> None:
    """Raise UnsafeURLError unless `url` is http(s) and resolves only to public IPs."""
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise UnsafeURLError("Only http and https links are supported.")
    host = parsed.hostname
    if not host:
        raise UnsafeURLError("That link has no host name.")
    if settings.ALLOW_PRIVATE_URLS:
        return
    try:
        infos = socket.getaddrinfo(host, parsed.port or (443 if parsed.scheme == "https" else 80))
    except socket.gaierror as e:
        raise UnsafeURLError(f"Could not resolve {host}.") from e
    for info in infos:
        if not _is_public_ip(info[4][0]):
            raise UnsafeURLError("Links to local or private network addresses are blocked.")


def safe_get(session: requests.Session, url: str, timeout: float = 15) -> requests.Response:
    """GET that re-checks every redirect hop with check_url()."""
    for _ in range(MAX_REDIRECTS + 1):
        check_url(url)
        response = session.get(url, timeout=timeout, allow_redirects=False)
        if response.is_redirect and response.headers.get("Location"):
            url = urljoin(url, response.headers["Location"])
            continue
        return response
    raise UnsafeURLError("Too many redirects.")
