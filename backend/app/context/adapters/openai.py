"""OpenAI reasoning provider adapter."""

from ..provider_registry import BaseProviderAdapter


class OpenAIProviderAdapter(BaseProviderAdapter):
    name = "openai"
    default_openrouter_model = "openai/gpt-4o-mini"
