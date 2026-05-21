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
from typing import Any, Dict, Iterable, List, Optional, Tuple

try:
    from supabase import create_client, Client as SupabaseClient  # type: ignore
except ImportError:
    create_client = None
    SupabaseClient = None


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
        self.supabase: Optional[SupabaseClient] = None
        self.memory: List[Dict[str, Any]] = []
        if supabase_url and supabase_key and create_client:
            try:
                self.supabase = create_client(supabase_url, supabase_key)
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

    def search_memory(self, *, namespace_prefix: Tuple[str, ...], query: Optional[str] = None, memory_key: Optional[str] = None, limit: int = 5) -> List[Dict[str, Any]]:
        """Retrieve recent memory entries matching the given namespace prefix.

        If running on Supabase, this issues a SQL query filtering by
        namespace and optionally by memory_key or full text search. On
        the fallback store, it simply filters the in‑memory list.

        :param namespace_prefix: tuple of namespace parts to match at the start of the namespace list
        :param query: optional substring to search in JSON content
        :param memory_key: optional exact key to match
        :param limit: maximum number of entries to return
        :return: list of memory entries, most recent first
        """
        if self.supabase:
            try:
                query_builder = self.supabase.table("agent_memory").select("*").order("created_at", desc=True)
                # Supabase/PostgREST supports the array contains operator via cs.
                query_builder = query_builder.filter("namespace", "cs", json.dumps(list(namespace_prefix)))
                if memory_key:
                    query_builder = query_builder.filter("memory_key", "eq", memory_key)
                # Supabase doesn't support JSON contains search easily; we skip query search here
                response = query_builder.limit(limit).execute()
                if response and response.data:
                    return response.data  # type: ignore
            except Exception as exc:
                logger.error("Supabase search failed: %s", exc)
        # Fallback filter
        result: List[Dict[str, Any]] = []
        for entry in reversed(self.memory):  # iterate from latest
            ns = entry.get("namespace", [])
            if len(ns) < len(namespace_prefix):
                continue
            if not all(part == ns[i] for i, part in enumerate(namespace_prefix)):
                continue
            if memory_key and entry.get("memory_key") != memory_key:
                continue
            if query:
                try:
                    if query.lower() not in json.dumps(entry.get("content")).lower():
                        continue
                except Exception:
                    pass
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
