"""Shared memory store for BuyerOS.

This module implements a simple memory store that can either persist
entries to Supabase/PostgreSQL or fall back to an in‑memory list.  It
provides two high‑level methods: ``save_memory`` to persist a memory
entry and ``search_memory`` to retrieve past entries matching a
namespace prefix and optional keyword or key.  The goal of this
component is to provide durable storage for conversations and state so
that agents can share context across sessions and over long periods.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

create_supabase_client: Optional[Callable[..., Any]] = None
try:
    from supabase import create_client as _imported_create_supabase_client  # type: ignore

    create_supabase_client = _imported_create_supabase_client
except ImportError:
    pass


logger = logging.getLogger(__name__)


class MemoryStore:
    """A simple memory store with optional Supabase backend.

    If Supabase credentials are provided via environment variables
    ``SUPABASE_URL`` and ``SUPABASE_KEY``, this store will persist
    entries to a Supabase table named ``agent_memory``.  Otherwise it
    falls back to an in‑memory list, which is useful for local
    development and testing.  Each memory entry records its namespace
    (a list of strings), a memory key, arbitrary JSON content, the
    creator identifier and a timestamp.
    """

    def __init__(self, *, supabase_url: Optional[str] = None, supabase_key: Optional[str] = None) -> None:
        self.supabase: Optional[Any] = None
        self.memory: List[Dict[str, Any]] = []
        if supabase_url and supabase_key and create_supabase_client:
            try:
                self.supabase = create_supabase_client(supabase_url, supabase_key)
                # ensure table exists (Supabase will create on insert if absent)
                logger.info("Using Supabase for memory storage")
            except Exception as exc:
                logger.warning("Failed to initialise Supabase client: %s", exc)
                self.supabase = None

    def save_memory(self, namespace: Iterable[str], memory_key: str, content: Dict[str, Any], created_by: str) -> None:
        """Persist a memory entry.

        :param namespace: hierarchical list representing the scope (e.g. ["buyeros", "refunds"])
        :param memory_key: key (such as transaction id) for later retrieval
        :param content: arbitrary JSON serialisable data
        :param created_by: identifier of the agent or user creating the entry
        """
        entry = {
            "namespace": list(namespace),
            "memory_key": memory_key,
            "content": content,
            "created_by": created_by,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        if self.supabase:
            try:
                # Insert into Supabase; table must have matching columns
                self.supabase.table("agent_memory").insert(entry).execute()
                return
            except Exception as exc:
                logger.error("Supabase save failed: %s", exc)
        # Fallback: deduplicate by (namespace, memory_key) then append
        for existing in self.memory:
            if existing.get("namespace") == entry.get("namespace") and existing.get("memory_key") == entry.get("memory_key"):
                existing.update(entry)
                return
        self.memory.append(entry)

    def search_memory(
        self,
        *,
        namespace_prefix: Tuple[str, ...],
        query: Optional[str] = None,
        memory_key: Optional[str] = None,
        session_id: Optional[str] = None,
        task_id: Optional[str] = None,
        source_provider: Optional[str] = None,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """Retrieve recent memory entries matching the given namespace prefix.

        If running on Supabase, this issues a SQL query filtering by
        namespace and optionally by memory_key or full text search. On
        the fallback store, it simply filters the in‑memory list.

        :param namespace_prefix: tuple of namespace parts to match at the start of the namespace list
        :param query: optional substring to search in JSON content
        :param memory_key: optional exact key to match
        :param session_id: optional session id stored inside the content payload
        :param task_id: optional task id stored inside the content payload
        :param source_provider: optional provider stored inside the content payload
        :param limit: maximum number of entries to return
        :return: list of memory entries, most recent first
        """
        if self.supabase:
            try:
                query_builder = self.supabase.table("agent_memory").select("*").order("created_at", desc=True)
                # PostgREST expects Postgres array literal syntax for text[] filters.
                query_builder = query_builder.filter("namespace", "cs", self._pg_array_literal(namespace_prefix))
                if memory_key:
                    query_builder = query_builder.filter("memory_key", "eq", memory_key)
                # Keep JSON/text filtering deterministic across Supabase and the
                # in-memory store. Fetch a bounded candidate window first, then
                # apply query/session/provider filters before final limiting.
                fetch_limit = min(max(limit * 20, 100), 1000)
                response = query_builder.limit(fetch_limit).execute()
                if response and response.data:
                    return self._filter_entries(
                        list(response.data),
                        namespace_prefix=namespace_prefix,
                        query=query,
                        memory_key=memory_key,
                        session_id=session_id,
                        task_id=task_id,
                        source_provider=source_provider,
                        limit=limit,
                    )
            except Exception as exc:
                logger.error("Supabase search failed: %s", exc)
        # Fallback filter
        return self._filter_entries(
            list(reversed(self.memory)),
            namespace_prefix=namespace_prefix,
            query=query,
            memory_key=memory_key,
            session_id=session_id,
            task_id=task_id,
            source_provider=source_provider,
            limit=limit,
        )

    def _filter_entries(
        self,
        entries: List[Dict[str, Any]],
        *,
        namespace_prefix: Tuple[str, ...],
        query: Optional[str],
        memory_key: Optional[str],
        session_id: Optional[str],
        task_id: Optional[str],
        source_provider: Optional[str],
        limit: int,
    ) -> List[Dict[str, Any]]:
        result: List[Dict[str, Any]] = []
        normalized_query = query.lower() if query else None
        normalized_provider = source_provider.lower().strip() if source_provider else None
        for entry in entries:
            ns = entry.get("namespace", [])
            if len(ns) < len(namespace_prefix):
                continue
            if not all(part == ns[i] for i, part in enumerate(namespace_prefix)):
                continue
            if memory_key and entry.get("memory_key") != memory_key:
                continue
            content = entry.get("content") or {}
            if session_id and content.get("session_id") != session_id:
                continue
            if task_id and content.get("task_id") != task_id:
                continue
            if normalized_provider and str(content.get("source_provider", "")).lower().strip() != normalized_provider:
                continue
            if normalized_query:
                try:
                    searchable = json.dumps(content, ensure_ascii=False, sort_keys=True).lower()
                    if normalized_query not in searchable and normalized_query not in str(entry.get("memory_key", "")).lower():
                        continue
                except Exception:
                    continue
            result.append(entry)
            if len(result) >= limit:
                break
        return result

    def status(self) -> Dict[str, Any]:
        if not self.supabase:
            return {"backend": "memory", "ok": True, "items": len(self.memory)}
        try:
            self.supabase.table("agent_memory").select("id").limit(1).execute()
            return {"backend": "supabase", "ok": True}
        except Exception as exc:
            logger.error("Supabase status check failed: %s", exc)
            return {"backend": "supabase", "ok": False, "error": str(exc)}

    def _pg_array_literal(self, values: Iterable[str]) -> str:
        escaped = [str(value).replace("\\", "\\\\").replace('"', '\\"') for value in values]
        return "{" + ",".join(f'"{value}"' for value in escaped) + "}"
