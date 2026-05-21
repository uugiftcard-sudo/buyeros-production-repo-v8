"""MiniMax provider adapter."""

from ..provider_registry import BaseProviderAdapter


class MiniMaxProviderAdapter(BaseProviderAdapter):
    name = "minimax"
    default_openrouter_model = "minimax/minimax-01"
