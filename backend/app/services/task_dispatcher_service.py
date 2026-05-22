"""Task dispatcher planning (no agent group chat).

This service creates a parent task, a deterministic subtask plan, and can run
subtasks sequentially through ProviderRegistry. Each subtask reads shared
context and writes results back; no open-ended multi-agent loops.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from ..context.context_hub import ContextHub
from ..context.provider_registry import ProviderRegistry
from ..agents.ops_agent import OpsAgent
from ..agents.finance_agent import FinanceAgent
from ..memory_store import MemoryStore
from .project_registry_service import ProjectRegistryService
from .task_board_service import TaskBoardService


class TaskDispatcherService:
    def __init__(
        self,
        *,
        memory_store: MemoryStore,
        task_board: TaskBoardService,
        projects: ProjectRegistryService,
        providers: ProviderRegistry,
        context_hub: ContextHub,
        ops_agent: OpsAgent,
        finance_agent: FinanceAgent,
    ) -> None:
        self.memory = memory_store
        self.task_board = task_board
        self.projects = projects
        self.providers = providers
        self.context_hub = context_hub
        self.ops_agent = ops_agent
        self.finance_agent = finance_agent

    def _task_level_preferred_provider(self, *, task_type: str, prompt: str) -> Optional[str]:
        """Deterministic task-level routing for provider work.

        This makes routing explicit (vs. purely prompt heuristics) and keeps
        operation predictable in production.
        """
        t = (task_type or "").lower().strip()
        lower = (prompt or "").lower()
        if t in {"code", "coding", "dev"} or any(k in lower for k in ["code", "coding", "repo", "bug", "stack trace", "cursor", "claude"]):
            return "claude"
        if t in {"research", "news"} or any(k in lower for k in ["research", "news", "search", "perplexity", "grok"]):
            return "perplexity"
        return None

    def _route_for(self, *, task_type: str, prompt: str) -> str:
        """Return routing target: ops | finance | provider.

        Dispatcher routing is explicit and deterministic; it never starts a
        group chat loop. Business intents go to local agents; everything else
        goes through ProviderRegistry with fallback.
        """
        t = (task_type or "").lower().strip()
        lower = (prompt or "").lower()
        if t in {"ops", "refund", "order"} or any(k in lower for k in ["refund", "退款", "order", "ocr", "文字識別"]):
            return "ops"
        if t in {"finance", "payout", "profit"} or any(k in lower for k in ["profit", "盈利", "payout", "出糧", "結算"]):
            return "finance"
        return "provider"

    def create_plan(
        self,
        *,
        project: str,
        task_type: str,
        title: str,
        prompt: str,
        preferred_provider: Optional[str],
        session_id: Optional[str],
        max_steps: int,
    ) -> Dict[str, Any]:
        project = self.task_board.normalize_lane(project)
        created = self.task_board.create_task(
            title=title,
            lane=project,
            owner_provider=preferred_provider or "openai",
            priority="P0",
            payload={"project": project, "task_type": task_type, "prompt": prompt},
        )
        task_id = created["task"]["task_id"]
        subtasks = self._heuristic_plan(project=project, task_type=task_type, prompt=prompt, max_steps=max_steps)
        for step in subtasks:
            step["task_id"] = task_id
        now = datetime.now(timezone.utc).isoformat()
        plan_id = f"plan-{uuid4().hex[:8]}"
        plan = {
            "plan_id": plan_id,
            "task_id": task_id,
            "project": project,
            "task_type": task_type,
            "title": title,
            "prompt": prompt,
            "steps": subtasks,
            "status": "planned",
            "created_at": now,
            "session_id": session_id,
        }
        self.memory.save_memory(["buyeros", "dispatch_plans"], plan_id, plan, created_by="dispatcher")
        for step in subtasks:
            self.memory.save_memory(["buyeros", "subtasks"], step["subtask_id"], step, created_by="dispatcher")
        self.task_board.update_status(task_id=task_id, status="queued", note=f"planned {len(subtasks)} subtasks")
        return {"ok": True, "task_id": task_id, "plan": plan}

    def list_subtasks(self, *, task_id: str, limit: int = 50) -> Dict[str, Any]:
        items = self.memory.search_memory(namespace_prefix=("buyeros", "subtasks"), query=task_id, limit=limit)
        # search_memory doesn't understand task_id field natively for supabase, so filter here too
        filtered = [it for it in items if (it.get("content") or {}).get("task_id") == task_id]
        latest_by_subtask: Dict[str, Dict[str, Any]] = {}
        for item in filtered:
            content = item.get("content") or {}
            subtask_id = str(content.get("subtask_id") or item.get("memory_key") or "")
            if not subtask_id:
                continue
            existing = latest_by_subtask.get(subtask_id)
            if existing is None or self._item_timestamp(item) >= self._item_timestamp(existing):
                latest_by_subtask[subtask_id] = item
        deduped = list(latest_by_subtask.values())
        deduped.sort(key=lambda x: int(((x.get("content") or {}).get("order") or 0)))
        return {"ok": True, "items": deduped}

    def run_subtask(
        self,
        *,
        task_id: str,
        subtask_id: str,
        preferred_provider: Optional[str],
        session_id: Optional[str],
    ) -> Dict[str, Any]:
        items = self.memory.search_memory(namespace_prefix=("buyeros", "subtasks"), memory_key=subtask_id, limit=1)
        if not items:
            return {"ok": False, "error": "subtask_not_found"}
        subtask = items[0].get("content") or {}
        if subtask.get("task_id") != task_id:
            return {"ok": False, "error": "subtask_task_mismatch"}
        if subtask.get("status") in {"completed"}:
            return {"ok": True, "status": "already_completed", "subtask": subtask}

        self._update_subtask(subtask_id=subtask_id, status="running")
        self.task_board.update_status(task_id=task_id, status="running", note=f"running {subtask_id}")

        subtask_project = self.task_board.normalize_lane(str(subtask.get("project") or ""))
        project_meta = self.projects.get_project(project_id=subtask_project) or {"project_id": subtask_project}
        context = self.context_hub.search_context(query=str(subtask.get("goal") or ""), session_id=session_id, limit=8)
        context.insert(
            0,
            {
                "namespace": ["buyeros", "projects"],
                "memory_key": subtask_project,
                "content": {"summary": f"Project {subtask_project}", "content": project_meta},
            },
        )
        agent_prompt = str(subtask.get("prompt") or "")
        dispatch_prompt = f"[project={subtask_project} task_type={subtask.get('task_type')} subtask={subtask_id}]\n{agent_prompt}"
        route = self._route_for(task_type=str(subtask.get("task_type") or ""), prompt=str(subtask.get("prompt") or ""))
        effective_session = session_id or f"subtask-{subtask_id}"

        if route == "ops":
            reply = self.ops_agent.handle_message(user_id="dispatcher", text=agent_prompt)
            self.context_hub.write_context(
                source_provider="ops_agent",
                content={"reply": reply, "route": "ops", "subtask_id": subtask_id, "task_id": task_id, "project": subtask_project},
                session_id=effective_session,
                task_id=task_id,
                summary=reply,
                created_by="dispatcher",
            )
            self._update_subtask(subtask_id=subtask_id, status="completed", output=reply, provider="ops_agent")
            self.task_board.run_task(task_id=task_id, result=f"[{subtask_id}] {reply}", provider="ops_agent")
            return {"ok": True, "result": {"ok": True, "provider": "ops_agent", "reply": reply}, "subtask_id": subtask_id}

        if route == "finance":
            reply = self.finance_agent.handle_message(user_id="dispatcher", text=agent_prompt)
            self.context_hub.write_context(
                source_provider="finance_agent",
                content={"reply": reply, "route": "finance", "subtask_id": subtask_id, "task_id": task_id, "project": subtask_project},
                session_id=effective_session,
                task_id=task_id,
                summary=reply,
                created_by="dispatcher",
            )
            self._update_subtask(subtask_id=subtask_id, status="completed", output=reply, provider="finance_agent")
            self.task_board.run_task(task_id=task_id, result=f"[{subtask_id}] {reply}", provider="finance_agent")
            return {"ok": True, "result": {"ok": True, "provider": "finance_agent", "reply": reply}, "subtask_id": subtask_id}

        # Provider route: explicit task-level preferred provider + fallback chain.
        task_level_preferred = self._task_level_preferred_provider(
            task_type=str(subtask.get("task_type") or ""),
            prompt=str(subtask.get("prompt") or ""),
        )
        effective_preferred = preferred_provider or subtask.get("preferred_provider") or task_level_preferred
        chain = self.providers.fallback_chain(dispatch_prompt, preferred=effective_preferred)
        routing_record = {
            "task_id": task_id,
            "subtask_id": subtask_id,
            "project": subtask_project,
            "task_type": subtask.get("task_type"),
            "route": "provider",
            "preferred_provider": effective_preferred,
            "fallback_chain": chain,
            "session_id": effective_session,
        }
        self.memory.save_memory(["buyeros", "routing"], subtask_id, routing_record, created_by="dispatcher")
        self.context_hub.write_context(
            source_provider="dispatcher",
            content={"type": "routing", **routing_record},
            session_id=effective_session,
            task_id=task_id,
            summary=f"routing provider={effective_preferred} chain={chain[:3]}",
            created_by="dispatcher",
        )

        result = self.providers.run(
            prompt=dispatch_prompt,
            context=context,
            preferred=effective_preferred,
            session_id=effective_session,
            task_id=task_id,
        )
        reply = result.get("reply") or ""
        if result.get("ok"):
            self._update_subtask(subtask_id=subtask_id, status="completed", output=reply, provider=str(result.get("provider") or "unknown"))
            self.task_board.run_task(task_id=task_id, result=f"[{subtask_id}] {reply}", provider=str(result.get("provider") or "unknown"))
            return {"ok": True, "result": result, "subtask_id": subtask_id}

        self._update_subtask(subtask_id=subtask_id, status="blocked", output=reply, provider=str(result.get("provider") or "unknown"))
        self.task_board.update_status(task_id=task_id, status="blocked", note=f"{subtask_id} blocked")
        return {"ok": False, "result": result, "subtask_id": subtask_id}

    def run_next(self, *, task_id: str, preferred_provider: Optional[str], session_id: Optional[str]) -> Dict[str, Any]:
        subtasks = self.list_subtasks(task_id=task_id, limit=200)["items"]
        for it in subtasks:
            sub = it.get("content") or {}
            if sub.get("status") in {"queued", "planned"}:
                return self.run_subtask(
                    task_id=task_id,
                    subtask_id=str(sub.get("subtask_id")),
                    preferred_provider=preferred_provider,
                    session_id=session_id,
                )
        return {"ok": True, "status": "no_pending_subtasks"}

    def run_all(
        self,
        *,
        task_id: str,
        preferred_provider: Optional[str],
        session_id: Optional[str],
        max_steps: int = 50,
    ) -> Dict[str, Any]:
        """Run queued subtasks sequentially until done or blocked.

        No agent group chat; this is a deterministic step runner.
        """
        results: List[Dict[str, Any]] = []
        for _ in range(max(1, min(max_steps, 200))):
            out = self.run_next(task_id=task_id, preferred_provider=preferred_provider, session_id=session_id)
            results.append(out)
            if out.get("status") == "no_pending_subtasks":
                return self._record_run_all(
                    task_id=task_id,
                    session_id=session_id,
                    status="completed",
                    ok=True,
                    results=results,
                )
            if not out.get("ok"):
                reason = str((out.get("result") or {}).get("error") or out.get("error") or out.get("status") or "subtask_blocked")
                return self._record_run_all(
                    task_id=task_id,
                    session_id=session_id,
                    status="blocked",
                    ok=False,
                    results=results,
                    blocked_reason=reason,
                )
        return self._record_run_all(
            task_id=task_id,
            session_id=session_id,
            status="max_steps_exceeded",
            ok=False,
            results=results,
            blocked_reason="max_steps_exceeded",
        )

    def _record_run_all(
        self,
        *,
        task_id: str,
        session_id: Optional[str],
        status: str,
        ok: bool,
        results: List[Dict[str, Any]],
        blocked_reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        task_items = self.memory.search_memory(namespace_prefix=("buyeros", "tasks"), memory_key=task_id, limit=1)
        task_content = (task_items[0].get("content") if task_items else {}) or {}
        task_payload = task_content.get("payload") if isinstance(task_content, dict) else {}
        project = self.task_board.normalize_lane(str(task_payload.get("project") or "")) if isinstance(task_payload, dict) else None
        payload = {
            "task_id": task_id,
            "project": project,
            "session_id": session_id,
            "status": status,
            "ok": ok,
            "blocked_reason": blocked_reason,
            "steps": len(results),
            "results": results,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        run_all_id = f"runall-{uuid4().hex[:10]}"
        self.memory.save_memory(["buyeros", "run_all"], run_all_id, payload, created_by="dispatcher")
        return payload

    def _update_subtask(self, *, subtask_id: str, status: str, output: Optional[str] = None, provider: Optional[str] = None) -> None:
        existing = self.memory.search_memory(namespace_prefix=("buyeros", "subtasks"), memory_key=subtask_id, limit=1)
        content = dict((existing[0].get("content") if existing else {}) or {})
        content["status"] = status
        content["updated_at"] = datetime.now(timezone.utc).isoformat()
        if output is not None:
            content["output"] = output
        if provider is not None:
            content["provider"] = provider
        self.memory.save_memory(["buyeros", "subtasks"], subtask_id, content, created_by="dispatcher")

    def _item_timestamp(self, item: Dict[str, Any]) -> float:
        raw = item.get("created_at") or (item.get("content") or {}).get("updated_at") or ""
        try:
            return datetime.fromisoformat(str(raw).replace("Z", "+00:00")).timestamp()
        except Exception:
            return 0.0

    def _heuristic_plan(self, *, project: str, task_type: str, prompt: str, max_steps: int) -> List[Dict[str, Any]]:
        # Deterministic v1: safe defaults + no external calls.
        t = (task_type or "").lower().strip()
        if t in {"ops", "refund", "order"}:
            base = [
                ("execute", "Run ops workflow", "Execute the requested ops action (refund/order/OCR) and write a concrete outcome to shared memory."),
                ("verify", "Verify and summarize", "Verify memory was written and summarize next operator action (if any)."),
            ]
        elif t in {"finance", "profit", "payout"}:
            base = [
                ("execute", "Run finance workflow", "Execute requested finance computation (profit/payout) and write results to shared memory."),
                ("verify", "Verify and summarize", "Verify memory was written and summarize next operator action (if any)."),
            ]
        elif t in {"research", "news"}:
            base = [
                ("collect", "Collect known facts", "Summarize what is already known in shared memory and what is missing."),
                ("research", "Research gaps", "Propose sources/queries and produce a concise findings summary."),
                ("synthesize", "Synthesize output", "Write a deliverable: brief, checklist, or decision memo."),
            ]
        else:
            base = [
                ("collect", "Collect context and constraints", "Read shared memory and identify constraints, acceptance, and current state."),
                ("plan", "Draft implementation plan", "Produce a concrete plan with files to touch and verification commands."),
                ("implement", "Implement changes", "Make code changes for the plan, minimal scope."),
                ("verify", "Verify and smoke", "Run tests/build/smoke relevant to changes and summarize results."),
            ]
        steps = base[: max_steps]
        planned: List[Dict[str, Any]] = []
        for index, (kind, goal, hint) in enumerate(steps, start=1):
            subtask_id = f"sub-{uuid4().hex[:8]}"
            planned.append(
                {
                    "subtask_id": subtask_id,
                    "task_id": "",  # filled by caller
                    "order": index,
                    "project": project,
                    "task_type": task_type,
                    "kind": kind,
                    "goal": goal,
                    "status": "queued",
                    "preferred_provider": None,
                    "prompt": f"{goal}\n\nContext:\n{prompt}\n\nGuidance:\n{hint}",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
            )
        return planned
