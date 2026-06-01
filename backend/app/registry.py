"""Consolidated registries for agents, tools, and providers.

This module provides a unified registry system for BuyerOS.
Replaces both registry.py and context/provider_registry.py patterns.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, Optional, Type

logger = logging.getLogger(__name__)


class Registry[T]:
    """Generic registry for any type of objects."""

    def __init__(self, name: str = "registry") -> None:
        self._name = name
        self._items: Dict[str, T] = {}

    def register(self, name: str, item: T) -> None:
        """Register an item with a name."""
        if name in self._items:
            logger.warning("Overwriting existing item '%s' in %s", name, self._name)
        logger.debug("Registering %s: %s", self._name, name)
        self._items[name] = item

    def get(self, name: str) -> T:
        """Get an item by name."""
        if name not in self._items:
            raise KeyError(f"{self._name}: '{name}' not found")
        return self._items[name]

    def get_or_default(self, name: str, default: T) -> T:
        """Get an item or return default if not found."""
        return self._items.get(name, default)

    def has(self, name: str) -> bool:
        """Check if item exists."""
        return name in self._items

    def unregister(self, name: str) -> bool:
        """Unregister an item."""
        if name in self._items:
            del self._items[name]
            return True
        return False

    def list_all(self) -> list[str]:
        """List all registered names."""
        return list(self._items.keys())

    def clear(self) -> None:
        """Clear all items."""
        self._items.clear()


# Pre-configured registries
agent_registry = Registry[Any]("agent")
tool_registry = Registry[Callable[..., Any]]("tool")
provider_registry = Registry[Any]("provider")


def register_agent(name: str, agent: Any) -> None:
    """Register an agent."""
    agent_registry.register(name, agent)


def get_agent(name: str) -> Any:
    """Get an agent by name."""
    return agent_registry.get(name)


def register_tool(name: str, tool: Callable[..., Any]) -> None:
    """Register a tool function."""
    tool_registry.register(name, tool)


def get_tool(name: str) -> Callable[..., Any]:
    """Get a tool by name."""
    return tool_registry.get(name)


def register_provider(name: str, provider: Any) -> None:
    """Register a provider."""
    provider_registry.register(name, provider)


def get_provider(name: str) -> Any:
    """Get a provider by name."""
    return provider_registry.get(name)
