"""OpenAI-compatible provider using the OpenAI SDK."""

import os
from time import perf_counter, sleep
from typing import Any

from pydantic import BaseModel

from living_narrative.llm.errors import ProviderConnectionError
from living_narrative.llm.metadata import MetadataRecorder
from living_narrative.llm.structured import (
    RawCompletion,
    complete_structured,
    compute_prompt_hash,
    require_prompt_template_name,
    schema_instruction_message,
)
from living_narrative.state.models import LLMConfig


class OpenAICompatibleProvider:
    provider_name = "openai-compatible"

    def __init__(
        self,
        config: LLMConfig,
        *,
        api_key_env: str = "OPENAI_API_KEY",
        api_key: str | None = None,
        client: Any | None = None,
        recorder: MetadataRecorder | None = None,
        profile_name: str | None = None,
        sleep_seconds: tuple[float, float] = (0.1, 0.2),
    ) -> None:
        self.config = config
        self.api_key_env = api_key_env
        self.api_key = api_key or os.environ.get(self.api_key_env)
        self.client = client or self._build_client()
        self.recorder = recorder
        self.profile_name = profile_name
        self.sleep_seconds = sleep_seconds

    def _build_client(self) -> Any:
        from openai import OpenAI

        return OpenAI(
            api_key=self.api_key,
            base_url=self.config.base_url,
            timeout=self.config.timeout_seconds,
        )

    def complete(
        self,
        messages: list[dict[str, Any]],
        response_schema: type[BaseModel],
        **params: Any,
    ) -> BaseModel:
        prompt_template_name = require_prompt_template_name(params)
        augmented = [*messages, schema_instruction_message(response_schema)]
        prompt_hash = compute_prompt_hash(augmented)
        return complete_structured(
            raw_complete=self._raw_complete,
            messages=augmented,
            response_schema=response_schema,
            provider_name=self.provider_name,
            model=self.config.model,
            prompt_template_name=prompt_template_name,
            prompt_hash=prompt_hash,
            profile_name=self.profile_name,
            recorder=self.recorder,
            secrets=[self.api_key],
        )

    def _raw_complete(self, messages: list[dict[str, Any]]) -> RawCompletion:
        last_error: object = "request failed"
        request_count = 0
        duration = 0.0
        for index in range(3):
            request_count += 1
            started = perf_counter()
            try:
                response = self.client.chat.completions.create(
                    model=self.config.model,
                    messages=messages,
                    timeout=self.config.timeout_seconds,
                )
            except transient_errors() as exc:
                duration += perf_counter() - started
                last_error = exc
                if index < 2:
                    sleep(self.sleep_seconds[index])
                    continue
                raise ProviderConnectionError(
                    provider_name=self.provider_name,
                    model=self.config.model,
                    error=last_error,
                    secrets=[self.api_key],
                ) from exc

            duration += perf_counter() - started
            choice = response.choices[0]
            content = choice.message.content or ""
            usage = getattr(response, "usage", None)
            return RawCompletion(
                text=content,
                duration_seconds=duration,
                prompt_tokens=getattr(usage, "prompt_tokens", None),
                completion_tokens=getattr(usage, "completion_tokens", None),
                total_tokens=getattr(usage, "total_tokens", None),
                request_count=request_count,
            )
        raise ProviderConnectionError(
            provider_name=self.provider_name,
            model=self.config.model,
            error=last_error,
            secrets=[self.api_key],
        )


def transient_errors() -> tuple[type[BaseException], ...]:
    try:
        from openai import APIConnectionError, APITimeoutError

        return (APIConnectionError, APITimeoutError, TimeoutError, ConnectionError)
    except ImportError:
        return (TimeoutError, ConnectionError)
