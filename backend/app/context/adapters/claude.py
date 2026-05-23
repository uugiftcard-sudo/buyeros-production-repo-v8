"""Claude/Cursor-style coding provider adapter."""

from ..provider_registry import BaseProviderAdapter


class ClaudeProviderAdapter(BaseProviderAdapter):
    name = "claude"
    default_openrouter_model = "anthropic/claude-sonnet-4.5"
