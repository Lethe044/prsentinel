from __future__ import annotations

import requests

from prsentinel.providers.base import BaseProvider, ProviderError

API_URL = "https://api.groq.com/openai/v1/chat/completions"


class GroqProvider(BaseProvider):
    name = "groq"
    default_model = "llama-3.3-70b-versatile"

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        if not self.api_key:
            raise ProviderError(
                "Groq requires an API key. Get a free one at "
                "https://console.groq.com/keys and set GROQ_API_KEY."
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
            raise ProviderError(f"Could not reach Groq: {exc}") from exc

        if response.status_code == 401:
            raise ProviderError("Groq rejected the API key. Check GROQ_API_KEY.")
        if response.status_code == 429:
            raise ProviderError(
                "Groq rate limit reached. Lower the request rate or wait a "
                "moment before retrying."
            )
        if response.status_code >= 400:
            raise ProviderError(
                f"Groq returned an error ({response.status_code}): "
                f"{response.text[:300]}"
            )

        data = response.json()
        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as exc:
            raise ProviderError(
                "Groq returned an unexpected response shape."
            ) from exc
