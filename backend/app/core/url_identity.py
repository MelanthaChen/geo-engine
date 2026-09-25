from urllib.parse import urlsplit


def canonical_url_identity(value: str) -> str:
    """Return a comparison-only identity for a website URL.

    HTTP and HTTPS are intentionally equivalent for demo-target selection.
    Stored values are never rewritten.
    """
    candidate = value.strip()
    parsed = urlsplit(candidate if "://" in candidate else f"//{candidate}")
    hostname = (parsed.hostname or "").lower()
    if not hostname:
        return ""

    port = parsed.port
    authority = hostname
    if port is not None and port not in {80, 443}:
        authority = f"{authority}:{port}"

    path = parsed.path.rstrip("/")
    query = f"?{parsed.query}" if parsed.query else ""
    return f"{authority}{path}{query}"
