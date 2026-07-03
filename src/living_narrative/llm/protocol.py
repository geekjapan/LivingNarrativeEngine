"""Provider protocol used by all engine LLM calls."""

from typing import Any, Protocol

from pydantic import BaseModel


class Provider(Protocol):
    def complete(
        self,
        messages: list[dict[str, Any]],
        response_schema: type[BaseModel],
        **params: Any,
    ) -> BaseModel:
        """Return a validated ``response_schema`` instance."""
