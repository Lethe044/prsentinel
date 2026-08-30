from __future__ import annotations

import requests

from prsentinel.providers.base import BaseProvider, ProviderError

API_URL = "https://api.openai.com/v1/chat/completions"


class OpenAIProvider(BaseProvider):
    """Optional, paid provider for people who want to use their own OpenAI
    key instead of a free tier model. Never required to use PR Sentinel.
    """

    name = "openai"
    default_model = "gpt-4o-mini"

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        if not self.api_key:
            raise ProviderError(
                "OpenAI requires your own API key. Set OPENAI_API_KEY, or "
                "switch to a free provider such as groq, gemini, or ollama."
            )

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
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
            raise ProviderError(f"Could not reach OpenAI: {exc}") from exc

        if response.status_code == 401:
            raise ProviderError("OpenAI rejected the API key. Check OPENAI_API_KEY.")
        if response.status_code == 429:
            raise ProviderError(
                "OpenAI rate limit or quota reached for this key."
            )
        if response.status_code >= 400:
            raise ProviderError(
                f"OpenAI returned an error ({response.status_code}): "
                f"{response.text[:300]}"
            )

        data = response.json()
        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as exc:
            raise ProviderError(
                "OpenAI returned an unexpected response shape."
            ) from exc
