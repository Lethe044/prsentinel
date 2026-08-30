"""Provider registry.

Adding a new provider means writing one class with a `complete` method and
adding it to PROVIDERS below. Nothing else in the codebase needs to change.
"""

from __future__ import annotations

from prsentinel.providers.anthropic_provider import AnthropicProvider
from prsentinel.providers.base import BaseProvider, ProviderError
from prsentinel.providers.gemini_provider import GeminiProvider
from prsentinel.providers.groq_provider import GroqProvider
from prsentinel.providers.ollama_provider import OllamaProvider
from prsentinel.providers.openai_provider import OpenAIProvider

PROVIDERS: dict[str, type[BaseProvider]] = {
    "groq": GroqProvider,
    "gemini": GeminiProvider,
    "ollama": OllamaProvider,
    "openai": OpenAIProvider,
    "anthropic": AnthropicProvider,
}

FREE_PROVIDERS = ("groq", "gemini", "ollama")
PAID_PROVIDERS = ("openai", "anthropic")


def get_provider(
    name: str,
    api_key: str | None,
    model: str | None,
    api_base: str | None = None,
) -> BaseProvider:
    provider_cls = PROVIDERS.get(name)
    if provider_cls is None:
        available = ", ".join(sorted(PROVIDERS))
        raise ProviderError(f"Unknown provider '{name}'. Available: {available}")
    return provider_cls(api_key=api_key, model=model, api_base=api_base)


__all__ = [
    "PROVIDERS",
    "FREE_PROVIDERS",
    "PAID_PROVIDERS",
    "get_provider",
    "BaseProvider",
    "ProviderError",
]
