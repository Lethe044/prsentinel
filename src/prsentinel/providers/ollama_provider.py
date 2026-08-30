from __future__ import annotations

import requests

from prsentinel.providers.base import BaseProvider, ProviderError

DEFAULT_HOST = "http://localhost:11434"


class OllamaProvider(BaseProvider):
    """Talks to a local Ollama server. No API key, no cost, no network
    round trip outside the machine it runs on.
    """

    name = "ollama"
    default_model = "llama3.1"

    def requires_api_key(self) -> bool:
        return False

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        host = self.api_base or DEFAULT_HOST
        url = f"{host.rstrip('/')}/api/chat"
        payload = {
            "model": self.model,
            "stream": False,
            "format": "json",
            "options": {"temperature": 0.1},
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }

        try:
            response = requests.post(url, json=payload, timeout=self.timeout)
        except requests.RequestException as exc:
            raise ProviderError(
                "Could not reach Ollama. Is it running? Start it with "
                f"'ollama serve' and make sure '{self.model}' is pulled "
                f"('ollama pull {self.model}'). Original error: {exc}"
            ) from exc

        if response.status_code == 404:
            raise ProviderError(
                f"Ollama does not have the model '{self.model}' pulled. "
                f"Run 'ollama pull {self.model}' first."
            )
        if response.status_code >= 400:
            raise ProviderError(
                f"Ollama returned an error ({response.status_code}): "
                f"{response.text[:300]}"
            )

        data = response.json()
        try:
            return data["message"]["content"]
        except KeyError as exc:
            raise ProviderError(
                "Ollama returned an unexpected response shape."
            ) from exc
