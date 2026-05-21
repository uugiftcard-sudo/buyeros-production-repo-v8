"""DeepSeek provider adapter."""

from ..provider_registry import BaseProviderAdapter


class DeepSeekProviderAdapter(BaseProviderAdapter):
    name = "deepseek"
    default_openrouter_model = "deepseek/deepseek-chat"
