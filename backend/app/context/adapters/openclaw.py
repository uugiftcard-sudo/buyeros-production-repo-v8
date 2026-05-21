"""OpenClaw orchestration provider adapter."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from ..provider_registry import BaseProviderAdapter


class OpenClawProviderAdapter(BaseProviderAdapter):
    name = "openclaw"

    candidate_roots = (
        Path("/Users/rubykan/Downloads/_Organized/Code_Projects/openclaw-zero-token-main"),
        Path("/Users/rubykan/Downloads/_Organized/Code_Projects/agency-agents-main/integrations/openclaw"),
    )

    def run(self, prompt: str, context: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        roots = [str(path) for path in self.candidate_roots if path.exists()]
        integration_files: List[str] = []
        for root in roots:
            root_path = Path(root)
            for pattern in ("**/*openclaw*.py", "**/*openclaw*.md", "**/SKILL.md"):
                integration_files.extend(str(p) for p in root_path.glob(pattern) if p.is_file())
        integration_files = sorted(integration_files)[:20]
        return {
            "provider": self.name,
            "ok": True,
            "reply": f"[openclaw] task staged with {len(context or [])} context item(s): {prompt}",
            "available_roots": roots,
            "integration_files": integration_files,
        }
