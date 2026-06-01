"""Redis-backed session state with a no-Redis fallback."""

from __future__ import annotations

import json
from typing import Any, Optional

try:  # pragma: no cover - import behavior is exercised via patched tests
    import redis
except Exception:  # pragma: no cover
    redis = None  # type: ignore[assignment]


class RedisSessionStore:
    def __init__(self, redis_url: Optional[str], *, ttl_seconds: int = 86400) -> None:
        self.redis_url = redis_url
        self.ttl_seconds = ttl_seconds
        self.client: Any = None
        if not redis_url or redis is None:
            return
        try:
            self.client = redis.Redis.from_url(redis_url, decode_responses=True)
            self.client.ping()
        except Exception:
            self.client = None

    def save_state(self, session_id: Optional[str], state: dict[str, Any]) -> None:
        if not session_id or self.client is None:
            return
        payload = {key: value for key, value in state.items() if key != "memory_hits"}
        self.client.setex(self._key(session_id), self.ttl_seconds, json.dumps(payload, ensure_ascii=False, default=str))

    def get_state(self, session_id: str) -> Optional[dict[str, Any]]:
        if self.client is None:
            return None
        raw = self.client.get(self._key(session_id))
        if not raw:
            return None
        try:
            data = json.loads(raw)
        except Exception:
            return None
        return data if isinstance(data, dict) else None

    def status(self) -> dict[str, Any]:
        if self.client is None:
            return {"configured": False, "ok": False}
        try:
            self.client.ping()
        except Exception:
            return {"configured": True, "ok": False}
        return {"configured": True, "ok": True}

    @staticmethod
    def _key(session_id: str) -> str:
        return f"buyeros:session:{session_id}"
