"""API router for all BuyerOS endpoints.

This module aggregates all service endpoints into a single router.
Routes: /api/expenses, /api/tasks, /api/automation, /api/memory
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, status
from typing import Any, Dict, List, Optional

from app.rate_limit import limiter, DEFAULT_LIMIT, WRITE_LIMIT

router = APIRouter(prefix="/api", tags=["buyeros"])


# ---------------------------------------------------------------------------
# Health & Status (no rate limit)
# ---------------------------------------------------------------------------

@router.get("/health")
async def health_check() -> Dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy", "service": "buyeros"}


@router.get("/status")
@limiter.limit(DEFAULT_LIMIT)
async def get_status(request: Request) -> Dict[str, Any]:
    """Get system status including AI router status."""
    from app.ai_router import AIModelRouter
    router_ai = AIModelRouter()
    return {
        "status": "operational",
        "ai_router": router_ai.status(),
    }


# ---------------------------------------------------------------------------
# Expenses
# ---------------------------------------------------------------------------

@router.get("/expenses")
@limiter.limit(DEFAULT_LIMIT)
async def list_expenses(
    request: Request,
    status_filter: Optional[str] = None,
    buyer_name: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """List expense claims."""
    from app.services.expense_service import ExpenseService
    service = ExpenseService()
    return service.list_claims(status=status_filter, buyer_name=buyer_name)


@router.post("/expenses")
@limiter.limit(WRITE_LIMIT)
async def create_expense(request: Request, data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new expense claim."""
    from app.services.expense_service import ExpenseService
    service = ExpenseService()
    return service.submit_claim(
        buyer_name=data.get("buyer_name", ""),
        amount=float(data.get("amount", 0)),
        description=data.get("description", ""),
        category=data.get("category", "other"),
    )


@router.get("/expenses/{expense_id}")
@limiter.limit(DEFAULT_LIMIT)
async def get_expense(request: Request, expense_id: str) -> Dict[str, Any]:
    """Get expense by ID."""
    from app.services.expense_service import ExpenseService
    service = ExpenseService()
    result = service.get_claim(expense_id)
    if not result:
        raise HTTPException(status_code=404, detail="Expense not found")
    return result


@router.patch("/expenses/{expense_id}")
@limiter.limit(WRITE_LIMIT)
async def update_expense(
    request: Request,
    expense_id: str,
    data: Dict[str, Any],
) -> Dict[str, Any]:
    """Update expense status (approve/reject)."""
    from app.services.expense_service import ExpenseService
    service = ExpenseService()
    action = data.get("action", "")
    if action == "approve":
        return service.update_status(
            expense_id,
            new_status="approved",
            reviewer_note=data.get("reviewer_note", ""),
        )
    elif action == "reject":
        return service.update_status(
            expense_id,
            new_status="rejected",
            reviewer_note=data.get("reviewer_note", ""),
        )
    raise HTTPException(status_code=400, detail="Invalid action")


# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------

@router.post("/tasks/dispatch")
@limiter.limit(WRITE_LIMIT)
async def dispatch_task(request: Request, data: Dict[str, Any]) -> Dict[str, Any]:
    """Dispatch a new task."""
    from app.services.task_dispatcher_service import TaskDispatcherService
    service = TaskDispatcherService()
    return service.dispatch_task(data)


@router.get("/tasks/{task_id}")
@limiter.limit(DEFAULT_LIMIT)
async def get_task(request: Request, task_id: str) -> Dict[str, Any]:
    """Get task by ID."""
    from app.services.task_dispatcher_service import TaskDispatcherService
    service = TaskDispatcherService()
    result = service.get_task_status(task_id)
    if not result:
        raise HTTPException(status_code=404, detail="Task not found")
    return result


@router.get("/tasks")
@limiter.limit(DEFAULT_LIMIT)
async def list_tasks(
    request: Request,
    status_filter: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """List tasks with optional status filter."""
    from app.services.task_dispatcher_service import TaskDispatcherService
    service = TaskDispatcherService()
    if status_filter == "pending":
        return service.list_pending_tasks()
    return service.list_pending_tasks()


@router.patch("/tasks/{task_id}/cancel")
@limiter.limit(WRITE_LIMIT)
async def cancel_task(request: Request, task_id: str) -> Dict[str, Any]:
    """Cancel a task."""
    from app.services.task_dispatcher_service import TaskDispatcherService
    service = TaskDispatcherService()
    return service.cancel_task(task_id)


# ---------------------------------------------------------------------------
# Bank & Reconciliation
# ---------------------------------------------------------------------------

@router.post("/bank/import")
@limiter.limit(WRITE_LIMIT)
async def import_bank_transactions(request: Request, data: Dict[str, Any]) -> Dict[str, Any]:
    """Import bank transactions."""
    from app.services.bank_import_service import BankImportService
    service = BankImportService()
    return service.import_transactions(data.get("transactions", []))


@router.get("/bank/reconciliations")
@limiter.limit(DEFAULT_LIMIT)
async def list_reconciliations(request: Request) -> List[Dict[str, Any]]:
    """List reconciliations."""
    from app.services.recon_store import ReconStore
    store = ReconStore()
    return store.list_reconciliations()


@router.get("/bank/reconciliations/{recon_id}")
@limiter.limit(DEFAULT_LIMIT)
async def get_reconciliation(request: Request, recon_id: str) -> Dict[str, Any]:
    """Get reconciliation by ID."""
    from app.services.recon_store import ReconStore
    store = ReconStore()
    result = store.get_reconciliation(recon_id)
    if not result:
        raise HTTPException(status_code=404, detail="Reconciliation not found")
    return result


# ---------------------------------------------------------------------------
# AI Router
# ---------------------------------------------------------------------------

@router.post("/ai/route")
@limiter.limit(WRITE_LIMIT)
async def route_ai_request(request: Request, data: Dict[str, Any]) -> Dict[str, Any]:
    """Route AI request to appropriate model."""
    from app.ai_router import AIModelRouter
    router_ai = AIModelRouter()
    role = data.get("role", "supervisor")
    prompt = data.get("prompt", "")
    reply = router_ai.route(role=role, prompt=prompt)
    return {"role": role, "reply": reply}


# ---------------------------------------------------------------------------
# Memory
# ---------------------------------------------------------------------------

@router.get("/memory/{key}")
@limiter.limit(DEFAULT_LIMIT)
async def get_memory(request: Request, key: str) -> Dict[str, Any]:
    """Get memory by key."""
    from app.memory_store import MemoryStore
    store = MemoryStore()
    return {"key": key, "value": store.get_memory(key)}


@router.post("/memory/{key}")
@limiter.limit(WRITE_LIMIT)
async def set_memory(request: Request, key: str, data: Dict[str, Any]) -> Dict[str, str]:
    """Set memory value."""
    from app.memory_store import MemoryStore
    store = MemoryStore()
    store.set_memory(key, data.get("value", ""))
    return {"key": key, "status": "saved"}


@router.delete("/memory/{key}")
@limiter.limit(WRITE_LIMIT)
async def delete_memory(request: Request, key: str) -> Dict[str, str]:
    """Delete memory."""
    from app.memory_store import MemoryStore
    store = MemoryStore()
    store.delete_memory(key)
    return {"key": key, "status": "deleted"}
