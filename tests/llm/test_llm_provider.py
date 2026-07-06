from types import SimpleNamespace

import pytest
from pydantic import BaseModel

from living_narrative.llm import (
    FixtureResponseError,
    ProviderConnectionError,
    StructuredOutputError,
    compute_prompt_hash,
    create_provider,
    resolve_llm_profile,
)
from living_narrative.llm.metadata import build_prompt_record, build_turn_meta
from living_narrative.llm.structured import RawCompletion, complete_structured
from living_narrative.state.models import LLMConfig, ProjectConfig


class SampleResponse(BaseModel):
    text: str
    score: int


def project_config() -> ProjectConfig:
    return ProjectConfig.model_validate(
        {
            "id": "mist_station",
            "title": "霧の駅",
            "genre": "mystery",
            "tone": "quiet",
            "autonomy_level": "assist",
            "user_mode": "assistant_gm",
            "random_seed": "seed",
            "renderer": "novel",
            "llm": {"provider": "mock", "model": "mock-default"},
            "llm_profiles": {"large": {"provider": "mock", "model": "mock-large"}},
            "llm_bindings": {"character:char_002": "large"},
            "workspace": {
                "root": "workspace",
                "state": "workspace/state",
                "runs": "workspace/runs",
                "exports": "workspace/exports",
            },
        }
    )


def messages(text: str = "Return a sample") -> list[dict[str, str]]:
    return [{"role": "user", "content": text}]


def test_resolves_character_binding_and_role_fallback():
    project = project_config()
    character = resolve_llm_profile(project, "character:char_002")
    role = resolve_llm_profile(project, "world_simulator")

    assert character.name == "large"
    assert character.config.model == "mock-large"
    assert role.name == "default"
    assert role.config.model == "mock-default"


def test_registry_rejects_unknown_provider():
    with pytest.raises(ValueError, match="available providers"):
        create_provider(LLMConfig(provider="missing", model="x"))


def test_structured_output_success_and_metadata():
    calls = []

    result = complete_structured(
        raw_complete=lambda _: RawCompletion('{"text": "ok", "score": 2}', total_tokens=5),
        messages=messages(),
        response_schema=SampleResponse,
        provider_name="fake",
        model="fake-model",
        prompt_template_name="sample-template",
        prompt_hash=compute_prompt_hash(messages()),
        recorder=calls.append,
    )

    assert result == SampleResponse(text="ok", score=2)
    assert calls[0].prompt_template_name == "sample-template"
    assert calls[0].total_tokens == 5
    assert build_turn_meta(calls)["llm_tokens_total"] == 5


def test_structured_output_retries_then_succeeds():
    raw = iter(["not json", '{"text": "ok", "score": 3}'])

    result = complete_structured(
        raw_complete=lambda _: RawCompletion(next(raw)),
        messages=messages(),
        response_schema=SampleResponse,
        provider_name="fake",
        model="fake-model",
        prompt_template_name="sample-template",
        prompt_hash=compute_prompt_hash(messages()),
    )

    assert result.score == 3


def test_structured_output_raises_after_retry_limit_and_scrubs_secret():
    def raw(_: list[dict[str, str]]) -> RawCompletion:
        return RawCompletion("api-secret is still not json")

    with pytest.raises(StructuredOutputError) as raised:
        complete_structured(
            raw_complete=raw,
            messages=messages(),
            response_schema=SampleResponse,
            provider_name="fake",
            model="fake-model",
            prompt_template_name="sample-template",
            prompt_hash=compute_prompt_hash(messages()),
            secrets=["api-secret"],
        )

    assert "api-secret" not in str(raised.value)


def test_mock_provider_deterministic_across_profiles_and_scripted_response():
    prompt_hash = compute_prompt_hash(messages())
    scripted = {"SampleResponse": {prompt_hash: {"text": "scripted", "score": 9}}}
    calls = []
    first = create_provider(
        LLMConfig(provider="mock", model="a"),
        random_seed="seed",
        scripted_responses=scripted,
        recorder=calls.append,
        profile_name="first",
    )
    second = create_provider(LLMConfig(provider="mock", model="b"), random_seed="seed")

    assert (
        first.complete(messages(), SampleResponse, prompt_template_name="sample").text == "scripted"
    )
    first_generated = first.complete(
        [{"role": "user", "content": "x"}], SampleResponse, prompt_template_name="x"
    )
    second_generated = second.complete(
        [{"role": "user", "content": "x"}],
        SampleResponse,
        prompt_template_name="x",
    )
    assert first_generated
    assert second_generated == first_generated
    assert calls[0].profile_name == "first"


def test_mock_provider_invalid_scripted_response_fails_without_retry():
    prompt_hash = compute_prompt_hash(messages())
    provider = create_provider(
        LLMConfig(provider="mock", model="mock"),
        scripted_responses={"SampleResponse": {prompt_hash: {"text": "bad"}}},
    )

    with pytest.raises(FixtureResponseError):
        provider.complete(messages(), SampleResponse, prompt_template_name="sample")


def test_prompt_hash_changes_with_prompt_and_wrapper_uses_initial_messages():
    original = messages("template one")
    calls = []

    assert compute_prompt_hash(original) != compute_prompt_hash(messages("template two"))
    complete_structured(
        raw_complete=lambda _: RawCompletion('{"text": "ok", "score": 1}'),
        messages=original,
        response_schema=SampleResponse,
        provider_name="fake",
        model="fake-model",
        prompt_template_name="sample-template",
        prompt_hash=compute_prompt_hash(original),
        recorder=calls.append,
    )
    assert calls[0].prompt_hash == compute_prompt_hash(original)
    record = build_prompt_record(original, compute_prompt_hash(original), "hash_only")
    assert record.messages is None


class FakeCompletions:
    def __init__(self) -> None:
        self.calls = 0

    def create(self, **_: object) -> object:
        self.calls += 1
        if self.calls == 1:
            raise TimeoutError("timeout with sk-test-secret")
        return SimpleNamespace(
            choices=[
                SimpleNamespace(message=SimpleNamespace(content='{"text": "ok", "score": 4}'))
            ],
            usage=SimpleNamespace(prompt_tokens=1, completion_tokens=2, total_tokens=3),
        )


def test_openai_provider_transient_retry_and_secret_hygiene(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-secret")
    completions = FakeCompletions()
    client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
    calls = []
    provider = create_provider(
        LLMConfig(provider="openai-compatible", model="test-model", timeout_seconds=1),
        client=client,
        recorder=calls.append,
        sleep_seconds=(0, 0),
    )

    result = provider.complete(messages(), SampleResponse, prompt_template_name="sample")

    assert result.score == 4
    assert completions.calls == 2
    assert calls[0].request_count == 2
    assert "sk-test-secret" not in str(calls[0])


def test_openai_provider_raises_typed_error_without_secret(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-secret")

    class FailingCompletions:
        def create(self, **_: object) -> object:
            raise TimeoutError("timeout with sk-test-secret")

    client = SimpleNamespace(chat=SimpleNamespace(completions=FailingCompletions()))
    provider = create_provider(
        LLMConfig(provider="openai-compatible", model="test-model"),
        client=client,
        sleep_seconds=(0, 0),
    )

    with pytest.raises(ProviderConnectionError) as raised:
        provider.complete(messages(), SampleResponse, prompt_template_name="sample")

    assert "sk-test-secret" not in str(raised.value)


def test_openai_provider_appends_response_schema_to_prompt():
    captured: dict[str, object] = {}

    class RecordingCompletions:
        def create(self, **kwargs: object) -> object:
            captured.update(kwargs)
            return SimpleNamespace(
                choices=[
                    SimpleNamespace(message=SimpleNamespace(content='{"text": "ok", "score": 4}'))
                ],
                usage=SimpleNamespace(prompt_tokens=1, completion_tokens=2, total_tokens=3),
            )

    client = SimpleNamespace(chat=SimpleNamespace(completions=RecordingCompletions()))
    provider = create_provider(
        LLMConfig(provider="openai-compatible", model="test-model"),
        api_key="sk-test",
        client=client,
    )

    provider.complete(messages(), SampleResponse, prompt_template_name="sample")

    sent = captured["messages"]
    assert sent[-1]["role"] == "user"
    assert "JSON Schema" in sent[-1]["content"]
    for field in SampleResponse.model_fields:
        assert field in sent[-1]["content"]
