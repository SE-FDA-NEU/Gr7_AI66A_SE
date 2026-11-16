"""Xác định client gửi request để giới hạn đoán mật khẩu theo nguồn truy cập.

Who is making this request? Used to key login lockouts by client, not only
by email, so that a stranger cannot lock somebody else's account.

Two parts:
* apply_proxy_fix(): make request.remote_addr the real visitor IP when the app
  sits behind trusted proxies (Render), and ignore forged X-Forwarded-For.
* client_key(): turn that IP into a stable, non-reversible key for the DB.
"""
from __future__ import annotations

import hashlib
import hmac
import ipaddress
import os

from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix

# Render: visitor -> Cloudflare -> Render proxy -> app. Each hop appends the
# address it saw to X-Forwarded-For, so the real visitor is the 2nd entry from
# the right. Entries further left are client-supplied and must be ignored.
RENDER_PROXY_HOPS = 2


def trusted_proxy_count(test_config: dict | None = None) -> int:
    """Number of proxies in front of the app whose X-Forwarded-For we trust."""
    # Cấu hình test được ưu tiên để có thể giả lập số proxy một cách rõ ràng.
    if test_config and "TRUSTED_PROXY_COUNT" in test_config:
        return int(test_config["TRUSTED_PROXY_COUNT"])
    raw = os.environ.get("TRUSTED_PROXY_COUNT", "").strip()
    if raw:
        count = int(raw)
        if count < 0:
            raise RuntimeError("TRUSTED_PROXY_COUNT must be 0 or more.")
        return count
    return RENDER_PROXY_HOPS if os.environ.get("RENDER") else 0


def apply_proxy_fix(app: Flask, test_config: dict | None = None) -> None:
    # Chỉ bật ProxyFix khi biết chính xác có bao nhiêu proxy đáng tin.
    hops = trusted_proxy_count(test_config)
    if hops > 0:
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=hops)


def client_key(remote_addr: str | None, secret: str) -> str:
    """Return a keyed hash of the client network.

    * IPv6 addresses are reduced to their /64 so a visitor cannot dodge the
      limit by rotating inside the block their ISP gave them.
    * The raw IP is never stored: only an HMAC of it, so the database holds no
      personal data and the hash cannot be reversed without SECRET_KEY.
    """
    # Chuẩn hóa IP trước khi băm để cùng một client có khóa ổn định.
    try:
        address = ipaddress.ip_address((remote_addr or "").strip())
        if isinstance(address, ipaddress.IPv6Address):
            if address.ipv4_mapped is not None:
                address = address.ipv4_mapped
            else:
                address = ipaddress.ip_network(f"{address}/64", strict=False)
        text = str(address)
    except ValueError:
        text = "unknown"
    # HMAC dùng secret key nên DB không lưu IP thô hay hash dễ đoán.
    digest = hmac.new(
        str(secret).encode(), text.encode(), hashlib.sha256
    ).hexdigest()
    return digest[:32]
