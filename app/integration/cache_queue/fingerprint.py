from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha256
from typing import Any


def _normalize(value: Any) -> Any:
    """
    Convert arbitrarily nested values to JSON-serializable stable forms.
    """
    if isinstance(value, dict):
        return {str(k): _normalize(v) for k, v in sorted(value.items(), key=lambda kv: str(kv[0]))}
    if isinstance(value, (list, tuple)):
        return [_normalize(v) for v in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return repr(value)


@dataclass(frozen=True)
class RequestFingerprint:
    model: str
    messages: list[dict[str, str]]
    params: dict[str, Any]

    def to_hash(self) -> str:
        payload = {
            "model": self.model,
            "messages": self.messages,
            "params": _normalize(self.params),
        }
        raw = json.dumps(payload, sort_keys=True)
        return sha256(raw.encode("utf-8")).hexdigest()
