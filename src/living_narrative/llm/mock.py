"""Deterministic mock LLM provider."""

import json
import random
from pathlib import Path
from typing import Any, Literal, get_args, get_origin

import yaml
from pydantic import BaseModel, ValidationError

from living_narrative.llm.errors import FixtureResponseError
from living_narrative.llm.metadata import MetadataRecorder
from living_narrative.llm.structured import compute_prompt_hash, require_prompt_template_name
from living_narrative.state.models import LLMConfig


class MockProvider:
    provider_name = "mock"

    def __init__(
        self,
        config: LLMConfig,
        *,
        random_seed: str = "",
        scripted_responses: dict[str, Any] | None = None,
        fixture_path: Path | None = None,
        recorder: MetadataRecorder | None = None,
        profile_name: str | None = None,
    ) -> None:
        self.config = config
        self.random_seed = random_seed
        self.scripted_responses = scripted_responses or {}
        if fixture_path is not None:
            self.scripted_responses.update(load_scripted_responses(fixture_path))
        self.recorder = recorder
        self.profile_name = profile_name

    def complete(
        self,
        messages: list[dict[str, Any]],
        response_schema: type[BaseModel],
        **params: Any,
    ) -> BaseModel:
        prompt_template_name = require_prompt_template_name(params)
        prompt_hash = compute_prompt_hash(messages)
        scripted = find_scripted_response(
            self.scripted_responses,
            response_schema.__name__,
            prompt_hash,
        )
        if scripted is not None:
            try:
                result = response_schema.model_validate(scripted)
            except ValidationError as exc:
                raise FixtureResponseError(
                    provider_name=self.provider_name,
                    model=self.config.model,
                    schema_name=response_schema.__name__,
                    last_error=exc,
                ) from exc
        else:
            result = response_schema.model_validate(
                generate_value(response_schema, self.random_seed, prompt_hash)
            )

        if self.recorder is not None:
            from living_narrative.llm.metadata import CallMetadata

            self.recorder(
                CallMetadata(
                    provider_name=self.provider_name,
                    model=self.config.model,
                    duration_seconds=0,
                    prompt_template_name=prompt_template_name,
                    prompt_hash=prompt_hash,
                    profile_name=self.profile_name,
                    request_count=1,
                )
            )
        return result


def load_scripted_responses(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        if path.suffix == ".json":
            return json.load(handle)
        return yaml.safe_load(handle) or {}


def find_scripted_response(fixtures: dict[str, Any], schema_name: str, prompt_hash: str) -> Any:
    if schema_name in fixtures and isinstance(fixtures[schema_name], dict):
        return fixtures[schema_name].get(prompt_hash)
    return fixtures.get(f"{schema_name}:{prompt_hash}")


def generate_value(
    annotation: Any,
    random_seed: str,
    prompt_hash: str,
    field_name: str = "value",
) -> Any:
    origin = get_origin(annotation)
    args = get_args(annotation)
    rng = random.Random(f"{random_seed}:{prompt_hash}:{field_name}")

    if isinstance(annotation, type) and issubclass(annotation, BaseModel):
        values = {}
        for name, field in annotation.model_fields.items():
            if not field.is_required():
                values[name] = field.get_default(call_default_factory=True)
            else:
                values[name] = generate_value(field.annotation, random_seed, prompt_hash, name)
        return values
    if origin is Literal:
        return args[0]
    if origin in (list, set, tuple):
        item_type = args[0] if args else str
        return [generate_value(item_type, random_seed, prompt_hash, field_name)]
    if origin is dict:
        return {}
    if annotation is str:
        return f"{field_name}_{rng.randrange(1_000_000):06d}"
    if annotation is int:
        return rng.randrange(1, 10)
    if annotation is float:
        return round(rng.random(), 6)
    if annotation is bool:
        return bool(rng.randrange(2))
    if origin is None and annotation is Any:
        return None
    if origin is type(None) or annotation is None:
        return None
    if origin is not None and type(None) in args:
        non_none = next(arg for arg in args if arg is not type(None))
        return generate_value(non_none, random_seed, prompt_hash, field_name)
    return None
