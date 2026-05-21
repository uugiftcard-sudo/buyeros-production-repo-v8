"""Grok/xAI provider adapter."""

from ..provider_registry import BaseProviderAdapter


class GrokProviderAdapter(BaseProviderAdapter):
    name = "grok"
    default_openrouter_model = "x-ai/grok-2"
