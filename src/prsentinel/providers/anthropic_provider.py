from __future__ import annotations

import requests

from prsentinel.providers.base import BaseProvider, ProviderError

API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"


class AnthropicProvider(BaseProvider):
    """Optional, paid provider for people who want to use their own
    Anthropic key instead of a free tier model. Never required to use
    PR Sentinel.
    """

    name = "anthropic"
    default_model = "claude-haiku-4-5-20251001"

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        if not self.api_key:
            raise ProviderError(
                "Anthropic requires your own API key. Set ANTHROPIC_API_KEY, "
                "or switch to a free provider such as groq, gemini, or "
                "ollama."
            )

        payload = {
            "model": self.model,
            "max_tokens": 2048,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_prompt}],
        }
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": ANTHROPIC_VERSION,
            "Content-Type": "application/json",
        }

        try:
            response = requests.post(
                self.api_base or API_URL,
                json=payload,
                headers=headers,
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise ProviderError(f"Could not reach Anthropic: {exc}") from exc

        if response.status_code == 401:
            raise ProviderError(
                "Anthropic rejected the API key. Check ANTHROPIC_API_KEY."
            )
        if response.status_code == 429:
            raise ProviderError(
                "Anthropic rate limit or quota reached for this key."
            )
        if response.status_code >= 400:
            raise ProviderError(
                f"Anthropic returned an error ({response.status_code}): "
                f"{response.text[:300]}"
            )

        data = response.json()
        try:
            return "".join(
                block.get("text", "")
                for block in data.get("content", [])
                if block.get("type") == "text"
            )
        except (KeyError, IndexError) as exc:
            raise ProviderError(
                "Anthropic returned an unexpected response shape."
            ) from exc
