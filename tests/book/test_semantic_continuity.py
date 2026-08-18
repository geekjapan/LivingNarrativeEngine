from __future__ import annotations

from living_narrative.book.chapters import ChapterCandidate, ChapterContext
from living_narrative.book.review import (
    SemanticContinuityAssessment,
    evaluate_semantic_continuity,
    review_chapter,
)


class _Gateway:
    def __init__(self, response: dict) -> None:
        self.response = response
        self.calls = 0

    def complete(self, binding_key, messages, response_schema, prompt_template_name):
        self.calls += 1
        return response_schema.model_validate(self.response)


def _context() -> ChapterContext:
    return ChapterContext(
        chapter_id="chapter_001",
        act_id="act_001",
        planned_goal="飢饉帳簿の矛盾を発見する。",
        required_thread_ids=["thread_famine_ledger"],
        target_min_words=10,
        target_max_words=100,
        reader_facts=["透は書庫番として目覚めた。"],
        memory_summary="透は王都の帳簿に疑念を抱いている。",
    )


def _candidate() -> ChapterCandidate:
    return ChapterCandidate(
        chapter_id="chapter_001",
        source_turns=[],
        markdown="# chapter_001\n\n透は書庫の窓を開けた。\n",
    )


def test_semantic_continuity_gate_blocks_missing_required_thread():
    assessment = evaluate_semantic_continuity(
        _context(),
        _candidate(),
        gateway=_Gateway({"required_threads_covered": [], "findings": []}),
    )
    review = review_chapter(_context(), _candidate(), semantic=assessment)

    assert assessment.required_threads_covered == []
    assert any(finding.code == "required_thread_missing" for finding in assessment.findings)
    assert review.decision.value == "revise"
    assert "required thread thread_famine_ledger is not covered" in review.reasons


def test_semantic_continuity_gate_keeps_grounded_finding_evidence():
    assessment = evaluate_semantic_continuity(
        _context(),
        _candidate(),
        gateway=_Gateway(
            {
                "required_threads_covered": ["thread_famine_ledger"],
                "findings": [
                    {
                        "code": "character_knowledge_jump",
                        "severity": "block",
                        "evidence": "透は根拠なく王都の秘密を断定する。",
                        "repair_instruction": "帳簿または会話で根拠を示す。",
                    }
                ],
            }
        ),
    )

    assert isinstance(assessment, SemanticContinuityAssessment)
    assert assessment.findings[0].evidence == "透は根拠なく王都の秘密を断定する。"
    assert assessment.findings[0].severity == "block"
