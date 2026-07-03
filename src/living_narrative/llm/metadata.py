"""LLM call metadata and prompt recording helpers."""

from typing import Any, Literal, Protocol

from pydantic import BaseModel, Field


class CallMetadata(BaseModel):
    provider_name: str
    model: str
    duration_seconds: float = Field(ge=0)
    prompt_template_name: str
    prompt_hash: str
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    profile_name: str | None = None
    request_count: int = Field(default=1, ge=0)


class MetadataRecorder(Protocol):
    def __call__(self, metadata: CallMetadata) -> None: ...


class PromptRecord(BaseModel):
    prompt_hash: str
    prompt_recording: Literal["full", "hash_only"] = "full"
    messages: list[dict[str, Any]] | None = None


def build_prompt_record(
    messages: list[dict[str, Any]],
    prompt_hash: str,
    prompt_recording: Literal["full", "hash_only"] = "full",
) -> PromptRecord:
    return PromptRecord(
        prompt_hash=prompt_hash,
        prompt_recording=prompt_recording,
        messages=messages if prompt_recording == "full" else None,
    )


def build_turn_meta(calls: list[CallMetadata]) -> dict[str, Any]:
    return {
        "llm_calls": [call.model_dump(exclude_none=True) for call in calls],
        "llm_tokens_total": sum(call.total_tokens or 0 for call in calls) or None,
        "models": [call.model for call in calls],
    }
