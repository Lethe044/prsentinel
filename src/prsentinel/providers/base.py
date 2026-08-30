"""Common interface every model provider implements.

Keeping this interface tiny (one method) is deliberate. It means adding a
new provider is a small, self contained change, and it keeps the reviewer
logic completely provider agnostic.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class ProviderError(Exception):
    """Raised when a provider cannot produce a response.

    The message should be safe to show directly to the user, since it is
    surfaced as-is in the CLI output and in PR comments.
    """


class BaseProvider(ABC):
    name: str = "base"
    default_model: str = ""

    def __init__(self, api_key: str | None = None, model: str | None = None,
                 api_base: str | None = None, timeout: int = 60):
        self.api_key = api_key
        self.model = model or self.default_model
        self.api_base = api_base
        self.timeout = timeout

    @abstractmethod
    def complete(self, system_prompt: str, user_prompt: str) -> str:
        """Sends the prompts to the model and returns the raw text response.

        Implementations should raise ProviderError with a clear, actionable
        message on any failure (missing key, network error, bad response
        shape) rather than letting a raw exception propagate.
        """
        raise NotImplementedError

    def requires_api_key(self) -> bool:
        return True
