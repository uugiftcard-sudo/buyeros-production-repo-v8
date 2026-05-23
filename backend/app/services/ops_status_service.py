"""Read-only operations drill summaries for the BuyerOS operator UI."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict


class OpsStatusService:
    """Load latest backup/rollback/failover/smoke summaries from infra scripts."""

    ACTIONS = ("backup", "rollback", "failover", "smoke")

    def __init__(self, summary_dir: str | None = None) -> None:
        configured = summary_dir or os.getenv("BUYEROS_OPS_SUMMARY_DIR")
        if configured:
            self.summary_dir = Path(configured)
        else:
            self.summary_dir = Path(__file__).resolve().parents[3] / "infra" / "ops_runs"

    def status(self) -> Dict[str, Any]:
        summaries = {action: self._read_latest(action) for action in self.ACTIONS}
        return {"ok": True, "summary_dir": str(self.summary_dir), "summaries": summaries}

    def _read_latest(self, action: str) -> Dict[str, Any]:
        path = self.summary_dir / f"{action}-latest.json"
        if not path.exists():
            return {"ok": False, "action": action, "status": "尚無執行紀錄", "notes": "尚未產生維運演練摘要。"}
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            return {"ok": False, "action": action, "status": "摘要無法讀取", "notes": str(exc)}
        if isinstance(data, dict):
            return data
        return {"ok": False, "action": action, "status": "摘要格式錯誤", "notes": "latest summary is not a JSON object"}
