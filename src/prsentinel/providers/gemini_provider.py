from __future__ import annotations

import requests

from prsentinel.providers.base import BaseProvider, ProviderError

API_URL_TEMPLATE = (
    "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
)


class GeminiProvider(BaseProvider):
    name = "gemini"
    default_model = "gemini-2.0-flash"

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        if not self.api_key:
            raise ProviderError(
                "Gemini requires an API key. Get a free one at "
                "https://aistudio.google.com/apikey and set GEMINI_API_KEY."
            )

        url = self.api_base or API_URL_TEMPLATE.format(model=self.model)
        payload = {
            "system_instruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
            "generationConfig": {
                "temperature": 0.1,
                "responseMimeType": "application/json",
            },
        }

        try:
            response = requests.post(
                url,
                params={"key": self.api_key},
                json=payload,
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise ProviderError(f"Could not reach Gemini: {exc}") from exc

        if response.status_code == 400:
            raise ProviderError(
                f"Gemini rejected the request: {response.text[:300]}"
            )
        if response.status_code == 429:
            raise ProviderError(
                "Gemini free tier rate limit reached. Wait a moment or "
                "reduce max_files in .prsentinel.yml before retrying."
            )
        if response.status_code >= 400:
            raise ProviderError(
                f"Gemini returned an error ({response.status_code}): "
                f"{response.text[:300]}"
            )

        data = response.json()
        try:
            candidates = data["candidates"]
            parts = candidates[0]["content"]["parts"]
            return "".join(part.get("text", "") for part in parts)
        except (KeyError, IndexError) as exc:
            raise ProviderError(
                "Gemini returned an unexpected response shape, or blocked "
                "the content due to its safety filters."
            ) from exc
