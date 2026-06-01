"""Registries for agents and tools.

A registry maps names to callable implementations, allowing dynamic
lookup and invocation.  The ``AgentRegistry`` stores agent instances
and the ``ToolRegistry`` stores tool functions.  These registries
provide a central point of coordination for the system.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict

logger = logging.getLogger(__name__)


class AgentRegistry:
    """Registry for agent instances."""

    def __init__(self) -> None:
        self._agents: Dict[str, Any] = {}

    def register(self, name: str, agent: Any) -> None:
        logger.debug("Registering agent %s", name)
        self._agents[name] = agent

    def get(self, name: str) -> Any:
        return self._agents[name]

    def has_agent(self, name: str) -> bool:
        return name in self._agents

    def names(self) -> list[str]:
        return sorted(self._agents.keys())


class ToolRegistry:
    """Registry for tool functions."""

    def __init__(self) -> None:
        self._tools: Dict[str, Callable[[Dict[str, Any]], Any]] = {}

    def register(self, name: str, func: Callable[[Dict[str, Any]], Any]) -> None:
        logger.debug("Registering tool %s", name)
        self._tools[name] = func

    def has_tool(self, name: str) -> bool:
        return name in self._tools

    def call(self, name: str, args: Dict[str, Any]) -> Any:
        if name not in self._tools:
            raise KeyError(f"Tool not registered: {name}")
        return self._tools[name](args)

    def names(self) -> list[str]:
        return sorted(self._tools.keys())
