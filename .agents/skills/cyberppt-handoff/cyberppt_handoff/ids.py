from __future__ import annotations

import hashlib


def stable_id(prefix: str, *parts: object, length: int = 16) -> str:
    """Return a deterministic uppercase SHA-256 based identifier."""
    namespace = str(prefix).strip().upper()
    if not namespace or not namespace.replace("-", "").isalnum():
        raise ValueError("prefix must be a non-empty alphanumeric namespace")
    raw = "\0".join([namespace, *(str(part) for part in parts)]).encode("utf-8")
    digest = hashlib.sha256(raw).hexdigest()[:length].upper()
    return f"{namespace}-{digest}"
