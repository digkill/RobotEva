"""
Shared HTTP client helpers.

Goal: reduce 403 blocks and allow routing requests via proxy (HTTP/HTTPS).
Used by: internet search/weather, LLM calls, model downloads.
"""

from __future__ import annotations

from typing import Any, Dict, Optional


def _get_cfg(config: Any, key: str, default: Any = None) -> Any:
    try:
        return config.get(key, default)
    except Exception:
        return default


def build_requests_proxies(config: Any) -> Optional[Dict[str, str]]:
    """
    Returns proxies dict for `requests`, or None if not configured.

    Config:
      network.proxy.enabled: bool
      network.proxy.url: "socks5h://user:pass@host:port"  (applies to both http/https)
      network.proxy.http: "http://user:pass@host:port"
      network.proxy.https: "http://user:pass@host:port"
    """
    enabled = bool(_get_cfg(config, "network.proxy.enabled", False))
    if not enabled:
        return None

    # Single proxy URL (supports socks5 / socks5h / http / https)
    proxy_url = str(_get_cfg(config, "network.proxy.url", "") or "").strip()
    if proxy_url:
        return {"http": proxy_url, "https": proxy_url}

    http_p = str(_get_cfg(config, "network.proxy.http", "") or "").strip()
    https_p = str(_get_cfg(config, "network.proxy.https", "") or "").strip()
    proxies: Dict[str, str] = {}
    if http_p:
        proxies["http"] = http_p
    if https_p:
        proxies["https"] = https_p
    return proxies or None


def build_default_headers(config: Any) -> Dict[str, str]:
    ua = str(
        _get_cfg(
            config,
            "network.http.user_agent",
            "Mozilla/5.0 (X11; Linux aarch64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122 Safari/537.36",
        )
        or ""
    ).strip()

    headers: Dict[str, str] = {
        "User-Agent": ua,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/json;q=0.8,*/*;q=0.7",
        "Accept-Language": str(_get_cfg(config, "network.http.accept_language", "ru-RU,ru;q=0.9,en;q=0.7") or ""),
        "Connection": "keep-alive",
    }
    # Remove empty values
    return {k: v for k, v in headers.items() if isinstance(v, str) and v.strip()}


def create_requests_session(config: Any):
    """
    Create configured `requests.Session` with:
    - proxy support
    - stable User-Agent
    - retries/backoff
    """
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry

    session = requests.Session()
    session.headers.update(build_default_headers(config))

    proxies = build_requests_proxies(config)
    if proxies:
        session.proxies.update(proxies)

    retries = int(_get_cfg(config, "network.http.retries", 2) or 0)
    backoff = float(_get_cfg(config, "network.http.retry_backoff", 0.6) or 0.0)
    status_forcelist = _get_cfg(config, "network.http.retry_statuses", [403, 429, 500, 502, 503, 504]) or []
    try:
        status_forcelist = [int(x) for x in status_forcelist]
    except Exception:
        status_forcelist = [403, 429, 500, 502, 503, 504]

    retry = Retry(
        total=retries,
        connect=retries,
        read=retries,
        status=retries,
        backoff_factor=backoff,
        status_forcelist=status_forcelist,
        allowed_methods=frozenset(["GET", "POST", "PUT", "DELETE", "HEAD", "OPTIONS"]),
        raise_on_status=False,
    )

    adapter = HTTPAdapter(max_retries=retry, pool_connections=10, pool_maxsize=10)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def _normalize_proxy_url_for_httpx(proxy_url: str) -> str:
    """
    httpx+socksio accepts socks5://... (and usually does remote DNS by default).
    User may provide socks5h://... (requests/PySocks style). Convert it for httpx.
    """
    p = (proxy_url or "").strip()
    if p.startswith("socks5h://"):
        return "socks5://" + p[len("socks5h://") :]
    return p


def create_httpx_client(config: Any):
    """
    Create configured httpx.Client for OpenAI SDK (and any httpx usage).

    Supports SOCKS via socksio (required for socks5:// proxies).
    """
    import httpx

    timeout = float(_get_cfg(config, "network.http.timeout_seconds", 30) or 30)
    headers = build_default_headers(config)

    proxies = build_requests_proxies(config)
    # httpx 0.28 expects a single proxy (string/Proxy), not a dict mapping.
    # We pick https first, then http, and apply it globally.
    proxy = None
    if proxies:
        proxy_url = None
        if isinstance(proxies, dict):
            proxy_url = proxies.get("https") or proxies.get("http")
        if isinstance(proxy_url, str) and proxy_url.strip():
            proxy = _normalize_proxy_url_for_httpx(proxy_url.strip())

    # httpx>=0.28 uses `proxy=` (singular). Older versions had `proxies=`.
    return httpx.Client(
        headers=headers,
        proxy=proxy,
        timeout=timeout,
        follow_redirects=True,
    )


