"""Small per-process token bucket for the public read API."""

from collections import defaultdict
from ipaddress import ip_address, ip_network
import json
import os
from threading import Lock
from time import monotonic


def _trusted_proxies():
    raw = os.getenv("NEXUS_TRUSTED_PROXY_CIDRS", "")
    try:
        return tuple(ip_network(item.strip(), strict=False) for item in raw.split(",") if item.strip())
    except ValueError as erro:
        raise RuntimeError("NEXUS_TRUSTED_PROXY_CIDRS contém uma rede inválida.") from erro


def _limit():
    try:
        value = int(os.getenv("NEXUS_API_RATE_LIMIT_PER_MINUTE", "60"))
    except ValueError as erro:
        raise RuntimeError("NEXUS_API_RATE_LIMIT_PER_MINUTE deve ser um inteiro positivo.") from erro
    if value < 1:
        raise RuntimeError("NEXUS_API_RATE_LIMIT_PER_MINUTE deve ser um inteiro positivo.")
    return value


class ApiRateLimitMiddleware:
    """Limits API reads per client, trusting X-Forwarded-For only from configured proxies."""

    def __init__(self, app):
        self.app = app
        self.capacity = _limit()
        self.trusted_proxies = _trusted_proxies()
        self.buckets = {}
        self.lock = Lock()

    def _client_key(self, scope):
        peer = scope.get("client")
        if not peer:
            return "unknown"
        try:
            peer_ip = ip_address(peer[0])
        except ValueError:
            return "unknown"
        if not any(peer_ip in network for network in self.trusted_proxies):
            return str(peer_ip)

        headers = {k.lower(): v for k, v in scope.get("headers", [])}
        forwarded = headers.get(b"x-forwarded-for", b"").decode("latin-1")
        try:
            chain = [ip_address(item.strip()) for item in forwarded.split(",") if item.strip()]
        except ValueError:
            return str(peer_ip)
        # Walk from the trusted proxy toward the original client. Ignore spoofable
        # entries to the left once the chain reaches an untrusted address.
        for candidate in reversed(chain):
            if not any(candidate in network for network in self.trusted_proxies):
                return str(candidate)
        return str(chain[0]) if chain else str(peer_ip)

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or not scope.get("path", "").startswith("/api/"):
            await self.app(scope, receive, send)
            return

        now = monotonic()
        key = self._client_key(scope)
        with self.lock:
            tokens, updated = self.buckets.get(key, (float(self.capacity), now))
            tokens = min(float(self.capacity), tokens + (now - updated) * self.capacity / 60)
            allowed = tokens >= 1
            if allowed:
                tokens -= 1
            self.buckets[key] = (tokens, now)
            if len(self.buckets) > 10_000:
                self.buckets = {
                    ip: state for ip, state in self.buckets.items()
                    if now - state[1] < 120
                }

        remaining = str(max(0, int(tokens)))
        if not allowed:
            retry_after = max(1, int((1 - tokens) * 60 / self.capacity + 0.999))
            body = json.dumps({"detail": "Limite de consultas excedido. Tente novamente mais tarde."}).encode()
            headers = [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(body)).encode()),
                (b"retry-after", str(retry_after).encode()),
                (b"x-ratelimit-limit", str(self.capacity).encode()),
                (b"x-ratelimit-remaining", b"0"),
            ]
            await send({"type": "http.response.start", "status": 429, "headers": headers})
            await send({"type": "http.response.body", "body": body})
            return

        async def send_with_rate_headers(message):
            if message["type"] == "http.response.start":
                message["headers"].extend([
                    (b"x-ratelimit-limit", str(self.capacity).encode()),
                    (b"x-ratelimit-remaining", remaining.encode()),
                ])
            await send(message)

        await self.app(scope, receive, send_with_rate_headers)
