"""Structured output validation and retry."""

import hashlib
import json
import re
from collections.abc import Callable
from dataclasses import dataclass
from json import JSONDecodeError
from time import perf_counter
from typing import Any

from pydantic import BaseModel, ValidationError

from living_narrative.llm.errors import StructuredOutputError
from living_narrative.llm.metadata import CallMetadata, MetadataRecorder


@dataclass(frozen=True)
class RawCompletion:
    text: str
    duration_seconds: float = 0
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    request_count: int = 1


RawComplete = Callable[[list[dict[str, Any]]], RawCompletion]


def require_prompt_template_name(params: dict[str, Any]) -> str:
    name = params.get("prompt_template_name")
    if not isinstance(name, str) or not name:
        raise ValueError("prompt_template_name is required")
    return name


def compute_prompt_hash(messages: list[dict[str, Any]]) -> str:
    payload = json.dumps(messages, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def extract_json(text: str) -> Any:
    block = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL | re.IGNORECASE)
    candidate = block.group(1).strip() if block else text.strip()
    try:
        return json.loads(candidate)
    except JSONDecodeError:
        pass

    decoder = json.JSONDecoder()
    starts = [index for index, char in enumerate(candidate) if char in "[{"]
    for start in starts:
        try:
            value, _ = decoder.raw_decode(candidate[start:])
            return value
        except JSONDecodeError:
            continue
    raise ValueError("response did not contain valid JSON")


def validate_json_response(text: str, response_schema: type[BaseModel]) -> BaseModel:
    return response_schema.model_validate(extract_json(text))


def schema_instruction_message(response_schema: type[BaseModel]) -> dict[str, str]:
    schema = json.dumps(response_schema.model_json_schema(), ensure_ascii=False)
    return {
        "role": "user",
        "content": (
            "Respond with a single JSON object that validates against this JSON Schema. "
            "Output only the JSON object — no prose, no code fences.\n" + schema
        ),
    }


def _retry_messages(
    messages: list[dict[str, Any]],
    raw_text: str,
    error: object,
) -> list[dict[str, Any]]:
    return [
        *messages,
        {"role": "assistant", "content": raw_text},
        {
            "role": "user",
            "content": (
                f"Return only JSON matching the requested schema. Validation error: {error}"
            ),
        },
    ]


def _add_optional(left: int | None, right: int | None) -> int | None:
    if left is None and right is None:
        return None
    return (left or 0) + (right or 0)


def complete_structured(
    *,
    raw_complete: RawComplete,
    messages: list[dict[str, Any]],
    response_schema: type[BaseModel],
    provider_name: str,
    model: str,
    prompt_template_name: str,
    prompt_hash: str,
    profile_name: str | None = None,
    recorder: MetadataRecorder | None = None,
    secrets: list[str | None] | None = None,
    max_retries: int = 2,
) -> BaseModel:
    attempts = 0
    request_count = 0
    duration = 0.0
    prompt_tokens = completion_tokens = total_tokens = None
    current_messages = list(messages)
    last_error: object = "no response"

    for _ in range(max_retries + 1):
        attempts += 1
        started = perf_counter()
        raw = raw_complete(current_messages)
        duration += raw.duration_seconds or (perf_counter() - started)
        request_count += raw.request_count
        prompt_tokens = _add_optional(prompt_tokens, raw.prompt_tokens)
        completion_tokens = _add_optional(completion_tokens, raw.completion_tokens)
        total_tokens = _add_optional(total_tokens, raw.total_tokens)
        try:
            result = validate_json_response(raw.text, response_schema)
        except (ValueError, ValidationError) as exc:
            last_error = exc
            current_messages = _retry_messages(current_messages, raw.text, exc)
            continue
        if recorder is not None:
            recorder(
                CallMetadata(
                    provider_name=provider_name,
                    model=model,
                    duration_seconds=duration,
                    prompt_template_name=prompt_template_name,
                    prompt_hash=prompt_hash,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=total_tokens,
                    profile_name=profile_name,
                    request_count=request_count,
                )
            )
        return result

    if recorder is not None:
        recorder(
            CallMetadata(
                provider_name=provider_name,
                model=model,
                duration_seconds=duration,
                prompt_template_name=prompt_template_name,
                prompt_hash=prompt_hash,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                profile_name=profile_name,
                request_count=request_count,
            )
        )
    raise StructuredOutputError(
        provider_name=provider_name,
        model=model,
        schema_name=response_schema.__name__,
        last_error=last_error,
        secrets=secrets,
    )
