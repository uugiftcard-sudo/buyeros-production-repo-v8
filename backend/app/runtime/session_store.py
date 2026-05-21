"""Short-term session state backed by Redis when available."""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, Optional

try:
    import redis
except ImportError:  # pragma: no cover - optional dependency fallback
    redis = None

logger = logging.getLogger(__name__)


class RedisSessionStore:
    """Persist latest workflow state for debugging and short-term recall."""

    def __init__(self, redis_url: Optional[str] = None, *, ttl_seconds: int = 86400) -> None:
        self.ttl_seconds = ttl_seconds
        self.client: Any = None
        url = redis_url or os.getenv("REDIS_URL")
        if url and redis:
            try:
                self.client = redis.Redis.from_url(url, decode_responses=True)
                self.client.ping()
                logger.info("Using Redis for session state")
            except Exception as exc:
                logger.warning("Redis unavailable, session state disabled: %s", exc)
                self.client = None

    def save_state(self, session_id: Optional[str], state: Dict[str, Any]) -> None:
        if not session_id or not self.client:
            return
        safe_state = {key: value for key, value in state.items() if key != "memory_hits"}
        self.client.setex(f"buyeros:session:{session_id}:last_state", self.ttl_seconds, json.dumps(safe_state, ensure_ascii=False, default=str))

    def get_state(self, session_id: str) -> Optional[Dict[str, Any]]:
        if not self.client:
            return None
        raw = self.client.get(f"buyeros:session:{session_id}:last_state")
        if not raw:
            return None
        return json.loads(raw)

    def status(self) -> Dict[str, Any]:
        if not self.client:
            return {"configured": False, "ok": False}
        try:
            self.client.ping()
            return {"configured": True, "ok": True}
        except Exception as exc:
            return {"configured": True, "ok": False, "error": str(exc)}
