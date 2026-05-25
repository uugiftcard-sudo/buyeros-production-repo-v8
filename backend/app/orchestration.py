"""Redis-backed orchestration state and trace streaming for BuyerOS."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from .security import require_api_key

logger = logging.getLogger(__name__)


class AgentStateUpdate(BaseModel):
    """State update emitted by agents and remote workers."""

    agent_id: str = Field(..., min_length=1)
    trace_id: str = Field(..., min_length=1)
    status: str = Field(..., min_length=1)
    node: str = Field(..., min_length=1)
    level: str = Field(..., min_length=1)
    message: str = Field(..., min_length=1)


class OrchestrationStore:
    """Persist agent state and trace timelines in Redis with local fallback."""

    def __init__(self, redis_url: Optional[str] = None, *, ttl_seconds: int = 604800) -> None:
        self.redis_url = redis_url or os.getenv("REDIS_URL")
        self.ttl_seconds = ttl_seconds
        self.client: Any = None
        self._redis_available = False
        self._states: Dict[str, Dict[str, Any]] = {}
        self._timelines: Dict[str, List[Dict[str, Any]]] = {}

    async def connect(self) -> None:
        """Connect to Redis when configured; otherwise keep in-memory fallback."""
        if not self.redis_url:
            return
        try:
            import redis.asyncio as aioredis

            self.client = aioredis.from_url(self.redis_url, decode_responses=True)
            await self.client.ping()
            self._redis_available = True
            logger.info("Using Redis for orchestration state")
        except Exception as exc:  # pragma: no cover - depends on local Redis availability
            logger.warning("Redis unavailable, orchestration state using memory fallback: %s", exc)
            self.client = None
            self._redis_available = False

    async def close(self) -> None:
        if self.client:
            await self.client.close()

    def status(self) -> Dict[str, Any]:
        return {
            "configured": bool(self.redis_url),
            "ok": self._redis_available or not self.redis_url,
            "backend": "redis" if self._redis_available else "memory",
        }

    async def update(self, payload: AgentStateUpdate) -> Dict[str, Any]:
        timestamp = int(time.time())
        log_frame = {
            "timestamp": timestamp,
            "node": payload.node,
            "level": payload.level,
            "message": payload.message,
        }
        state = {
            "agent_id": payload.agent_id,
            "current_status": payload.status,
            "current_trace_id": payload.trace_id,
            "last_heartbeat": timestamp,
            "error_message": payload.message if payload.status == "FAILED" else "None",
        }

        if self.client:
            state_key = self._state_key(payload.agent_id)
            timeline_key = self._timeline_key(payload.trace_id)
            try:
                pipe = self.client.pipeline(transaction=True)
                pipe.hset(state_key, mapping=state)
                pipe.expire(state_key, self.ttl_seconds)
                pipe.rpush(timeline_key, json.dumps(log_frame, ensure_ascii=False))
                pipe.expire(timeline_key, self.ttl_seconds)
                await pipe.execute()
            except Exception as exc:
                logger.error("Redis orchestration write failed: %s", exc)
                raise HTTPException(status_code=500, detail="Database orchestration failure") from exc
        else:
            self._states[payload.agent_id] = dict(state)
            self._timelines.setdefault(payload.trace_id, []).append(dict(log_frame))

        return {"state": state, "log_frame": log_frame}

    async def get_agent_state(self, agent_id: str) -> Optional[Dict[str, Any]]:
        if self.client:
            state = await self.client.hgetall(self._state_key(agent_id))
            return dict(state) if state else None
        return self._states.get(agent_id)

    async def get_timeline(self, trace_id: str, *, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        if self.client:
            start = -limit if limit else 0
            raw_logs = await self.client.lrange(self._timeline_key(trace_id), start, -1)
            return [json.loads(item) for item in raw_logs]
        logs = list(self._timelines.get(trace_id, []))
        return logs[-limit:] if limit else logs

    @staticmethod
    def _state_key(agent_id: str) -> str:
        return f"buyeros:agent:{agent_id}:state"

    @staticmethod
    def _timeline_key(trace_id: str) -> str:
        return f"buyeros:trace:{trace_id}:timeline"


class TraceConnectionManager:
    """WebSocket connection registry grouped by trace_id."""

    def __init__(self) -> None:
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, trace_id: str) -> None:
        await websocket.accept()
        self.active_connections.setdefault(trace_id, []).append(websocket)

    def disconnect(self, websocket: WebSocket, trace_id: str) -> None:
        connections = self.active_connections.get(trace_id)
        if not connections:
            return
        if websocket in connections:
            connections.remove(websocket)
        if not connections:
            del self.active_connections[trace_id]

    async def broadcast_to_trace(self, trace_id: str, payload: Dict[str, Any]) -> None:
        connections = list(self.active_connections.get(trace_id, []))
        if not connections:
            return
        message = json.dumps(payload, ensure_ascii=False)
        results = await asyncio.gather(
            *[connection.send_text(message) for connection in connections],
            return_exceptions=True,
        )
        for connection, result in zip(connections, results):
            if isinstance(result, Exception):
                self.disconnect(connection, trace_id)


def create_orchestration_router(store: OrchestrationStore, manager: TraceConnectionManager) -> APIRouter:
    """Create the orchestration API and WebSocket router."""

    router = APIRouter(tags=["Orchestration"])

    @router.post("/api/v1/orchestration/state-update", dependencies=[Depends(require_api_key)])
    async def update_agent_state(payload: AgentStateUpdate) -> Dict[str, Any]:
        result = await store.update(payload)
        broadcast_payload = {
            "agent_id": payload.agent_id,
            "status": payload.status,
            "latest_log": result["log_frame"],
        }
        await manager.broadcast_to_trace(payload.trace_id, broadcast_payload)
        return {"status": "synchronized", "agent_id": payload.agent_id, "trace_id": payload.trace_id}

    @router.get("/api/v1/orchestration/agent/{agent_id}", dependencies=[Depends(require_api_key)])
    async def get_agent_current_state(agent_id: str) -> Dict[str, Any]:
        state = await store.get_agent_state(agent_id)
        if not state:
            raise HTTPException(status_code=404, detail="Agent state not found")
        return state

    @router.get("/api/v1/orchestration/trace/{trace_id}/timeline", dependencies=[Depends(require_api_key)])
    async def get_trace_timeline(trace_id: str, limit: int = Query(100, ge=1, le=1000)) -> Dict[str, Any]:
        logs = await store.get_timeline(trace_id, limit=limit)
        return {"trace_id": trace_id, "logs": logs}

    @router.websocket("/ws/trace/{trace_id}")
    async def websocket_trace_stream(websocket: WebSocket, trace_id: str) -> None:
        await manager.connect(websocket, trace_id)
        try:
            history_logs = await store.get_timeline(trace_id)
            if history_logs:
                await websocket.send_text(
                    json.dumps({"type": "HISTORY_ECHO", "logs": history_logs}, ensure_ascii=False)
                )
            while True:
                client_raw_message = await websocket.receive_text()
                await websocket.send_text(
                    json.dumps({"received": True, "echo": client_raw_message}, ensure_ascii=False)
                )
        except WebSocketDisconnect:
            manager.disconnect(websocket, trace_id)
        except Exception:
            logger.exception("Trace websocket failure", extra={"trace_id": trace_id})
            manager.disconnect(websocket, trace_id)

    return router
