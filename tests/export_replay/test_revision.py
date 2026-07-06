import json

import pytest

from living_narrative.export_replay.revision import (
    CHAPTER_PROMPT_TEMPLATE_NAME,
    DEFAULT_REVISION_PROFILE,
    NOTES_PROMPT_TEMPLATE_NAME,
    ChapterRevisionOutput,
    NovelDraftParseError,
    RevisionNotes,
    RevisionNotesError,
    parse_novel_draft,
    render_revised_novel,
    revise_novel,
)
from living_narrative.llm.errors import ProviderConnectionError, StructuredOutputError

_SAMPLE_DRAFT = """\
# 霧の駅 — 小説風ドラフト(自動生成)

> このプレイセッションのログから自動生成した初稿です。人手の推敲を前提とします。

## 第1章: 駅 — 事件発生

天井の亀裂から水滴が落ちる。遠雷のような街のざわめきが聞こえる。

## 第2章: 駅 — 捜査開始

天井の亀裂から水滴が落ちる。二人は捜査を始めた。

## 第3章: 駅 — 解決

事件は解決した。
"""


class FakeGateway:
    def __init__(self, results=None, errors=None):
        self.results = results or {}
        self.errors = errors or {}
        self.calls = []

    def complete(self, binding_key, messages, response_schema, prompt_template_name):
        self.calls.append(
            {
                "binding_key": binding_key,
                "messages": messages,
                "schema": response_schema,
                "prompt_template_name": prompt_template_name,
            }
        )
        index = len(self.calls)
        if index in self.errors:
            raise self.errors[index]
        return self.results[index]


def _payload(call):
    return json.loads(call["messages"][1]["content"])


def _default_notes():
    return RevisionNotes(
        repeated_phrases=["天井の亀裂から水滴"],
        style_issues=[],
        continuity_notes=[],
    )


# --- parse/render round trip -------------------------------------------------


def test_parse_novel_draft_extracts_preamble_and_chapters_in_order():
    preamble, chapters = parse_novel_draft(_SAMPLE_DRAFT)

    assert "霧の駅" in preamble
    assert [title for title, _ in chapters] == [
        "駅 — 事件発生",
        "駅 — 捜査開始",
        "駅 — 解決",
    ]
    assert "天井の亀裂から水滴が落ちる。遠雷のような街のざわめきが聞こえる。" in chapters[0][1]
    assert "事件は解決した。" in chapters[2][1]


def test_parse_novel_draft_raises_on_missing_chapter_headings():
    with pytest.raises(NovelDraftParseError):
        parse_novel_draft("# タイトルだけ\n\n本文だけで見出しがない\n")


def test_render_revised_novel_round_trips_chapter_count_and_titles():
    preamble, chapters = parse_novel_draft(_SAMPLE_DRAFT)

    rendered = render_revised_novel(preamble, chapters)
    reparsed_preamble, reparsed_chapters = parse_novel_draft(rendered)

    assert reparsed_preamble == preamble
    assert len(reparsed_chapters) == len(chapters)
    assert [title for title, _ in reparsed_chapters] == [title for title, _ in chapters]
    assert "## 第1章:" in rendered
    assert "## 第2章:" in rendered
    assert "## 第3章:" in rendered


# --- revise_novel two-stage flow --------------------------------------------


def test_revise_novel_makes_one_notes_call_then_one_call_per_chapter():
    _, chapters = parse_novel_draft(_SAMPLE_DRAFT)
    notes = _default_notes()
    gateway = FakeGateway(
        results={
            1: notes,
            2: ChapterRevisionOutput(chapter_text="整えた一章"),
            3: ChapterRevisionOutput(chapter_text="整えた二章"),
            4: ChapterRevisionOutput(chapter_text="整えた三章"),
        }
    )

    revised_chapters, returned_notes = revise_novel(chapters, gateway)

    assert len(gateway.calls) == 4
    assert gateway.calls[0]["schema"] is RevisionNotes
    assert gateway.calls[0]["prompt_template_name"] == NOTES_PROMPT_TEMPLATE_NAME
    assert all(call["schema"] is ChapterRevisionOutput for call in gateway.calls[1:])
    assert all(
        call["prompt_template_name"] == CHAPTER_PROMPT_TEMPLATE_NAME for call in gateway.calls[1:]
    )
    assert all(call["binding_key"] == DEFAULT_REVISION_PROFILE for call in gateway.calls)
    assert returned_notes is notes
    assert [text for _, text in revised_chapters] == ["整えた一章", "整えた二章", "整えた三章"]


def test_revise_novel_uses_the_given_binding_key_profile():
    _, chapters = parse_novel_draft(_SAMPLE_DRAFT)
    gateway = FakeGateway(
        results={
            1: _default_notes(),
            2: ChapterRevisionOutput(chapter_text="a"),
            3: ChapterRevisionOutput(chapter_text="b"),
            4: ChapterRevisionOutput(chapter_text="c"),
        }
    )

    revise_novel(chapters, gateway, profile="narrator")

    assert all(call["binding_key"] == "narrator" for call in gateway.calls)


def test_revise_novel_passes_revision_notes_and_neighbor_context_to_each_chapter():
    _, chapters = parse_novel_draft(_SAMPLE_DRAFT)
    notes = _default_notes()
    gateway = FakeGateway(
        results={
            1: notes,
            2: ChapterRevisionOutput(chapter_text="a"),
            3: ChapterRevisionOutput(chapter_text="b"),
            4: ChapterRevisionOutput(chapter_text="c"),
        }
    )

    revise_novel(chapters, gateway)

    first_chapter_payload = _payload(gateway.calls[1])
    assert first_chapter_payload["revision_notes"] == notes.model_dump()
    assert first_chapter_payload["previous_chapter_tail"] == ""
    assert first_chapter_payload["next_chapter_head"] == chapters[1][1][:200]

    middle_chapter_payload = _payload(gateway.calls[2])
    assert middle_chapter_payload["previous_chapter_tail"] == chapters[0][1][-200:]
    assert middle_chapter_payload["next_chapter_head"] == chapters[2][1][:200]

    last_chapter_payload = _payload(gateway.calls[3])
    assert last_chapter_payload["previous_chapter_tail"] == chapters[1][1][-200:]
    assert last_chapter_payload["next_chapter_head"] == ""


def test_revise_novel_falls_back_to_original_chapter_on_chapter_failure():
    _, chapters = parse_novel_draft(_SAMPLE_DRAFT)
    gateway = FakeGateway(
        results={1: _default_notes(), 3: ChapterRevisionOutput(chapter_text="整えた二章")},
        errors={2: ProviderConnectionError(provider_name="mock", model="m", error="down")},
    )

    revised_chapters, _ = revise_novel([chapters[0], chapters[1]], gateway)

    assert chapters[0][1] in revised_chapters[0][1]
    assert "<!-- revision failed: original kept -->" in revised_chapters[0][1]
    assert revised_chapters[1][1] == "整えた二章"


@pytest.mark.parametrize(
    "error",
    [
        ProviderConnectionError(provider_name="mock", model="m", error="down"),
        StructuredOutputError(
            provider_name="mock", model="m", schema_name="ChapterRevisionOutput", last_error="bad"
        ),
    ],
)
def test_revise_novel_chapter_fallback_handles_any_known_failure_kind(error):
    _, chapters = parse_novel_draft(_SAMPLE_DRAFT)
    gateway = FakeGateway(results={1: _default_notes()}, errors={2: error})

    revised_chapters, _ = revise_novel([chapters[0]], gateway)

    assert "<!-- revision failed: original kept -->" in revised_chapters[0][1]


def test_revise_novel_raises_revision_notes_error_on_stage_one_failure():
    _, chapters = parse_novel_draft(_SAMPLE_DRAFT)
    gateway = FakeGateway(
        errors={1: ProviderConnectionError(provider_name="mock", model="m", error="down")}
    )

    with pytest.raises(RevisionNotesError):
        revise_novel(chapters, gateway)

    # stage 1 failing must not make any per-chapter calls at all.
    assert len(gateway.calls) == 1


def test_revise_novel_raises_revision_notes_error_on_stage_one_structured_output_failure():
    _, chapters = parse_novel_draft(_SAMPLE_DRAFT)
    gateway = FakeGateway(
        errors={
            1: StructuredOutputError(
                provider_name="mock", model="m", schema_name="RevisionNotes", last_error="bad json"
            )
        }
    )

    with pytest.raises(RevisionNotesError):
        revise_novel(chapters, gateway)
