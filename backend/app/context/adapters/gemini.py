"""Gemini provider adapter."""

from ..provider_registry import BaseProviderAdapter


class GeminiProviderAdapter(BaseProviderAdapter):
    name = "gemini"
    default_openrouter_model = "google/gemini-pro-1.5"
