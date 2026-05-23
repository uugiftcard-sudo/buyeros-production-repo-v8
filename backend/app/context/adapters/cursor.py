"""Cursor coding provider adapter."""

from ..provider_registry import BaseProviderAdapter


class CursorProviderAdapter(BaseProviderAdapter):
    name = "cursor"
    default_openrouter_model = "anthropic/claude-sonnet-4.5"
