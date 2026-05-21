"""Perplexity provider adapter."""

from ..provider_registry import BaseProviderAdapter


class PerplexityProviderAdapter(BaseProviderAdapter):
    name = "perplexity"
    default_openrouter_model = "perplexity/sonar"
