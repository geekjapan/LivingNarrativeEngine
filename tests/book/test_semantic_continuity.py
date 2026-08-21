from __future__ import annotations

from living_narrative.book.chapters import ChapterCandidate, ChapterContext
from living_narrative.book.review import (
    SemanticContinuityAssessment,
    evaluate_semantic_continuity,
    review_chapter,
)
from living_narrative.state.models import CharacterArcTarget


class _Gateway:
    def __init__(self, response: dict) -> None:
        self.response = response
        self.calls = 0
        self.messages: list[dict] = []

    def complete(self, binding_key, messages, response_schema, prompt_template_name):
        self.calls += 1
        self.messages = messages
        return response_schema.model_validate(self.response)


def _context() -> ChapterContext:
    return ChapterContext(
        chapter_id="chapter_001",
        act_id="act_001",
        planned_goal="飢饉帳簿の矛盾を発見する。",
        required_thread_ids=["thread_famine_ledger"],
        character_arc_targets=[
            CharacterArcTarget(
                character_id="char_001",
                delta="透は帳簿の不正を疑う勇気を得る。",
            )
        ],
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


def test_semantic_gate_v2_blocks_missing_planned_character_arc_target():
    assessment = evaluate_semantic_continuity(
        _context(),
        _candidate(),
        gateway=_Gateway(
            {
                "required_threads_covered": ["thread_famine_ledger"],
                "findings": [],
            }
        ),
    )
    review = review_chapter(_context(), _candidate(), semantic=assessment)

    finding = next(
        finding for finding in assessment.findings if finding.code == "character_arc_target_missing"
    )
    assert finding.severity == "block"
    assert finding.evidence == "planned character arc target char_001 is not covered"
    assert finding.repair_instruction == "Show or deliberately advance char_001's planned arc."
    assert review.decision.value == "revise"


def test_semantic_gate_v2_keeps_categorized_reader_safe_pov_warning():
    gateway = _Gateway(
        {
            "required_threads_covered": ["thread_famine_ledger"],
            "character_arc_target_ids_covered": ["char_001"],
            "findings": [
                {
                    "code": "pov_identity_discontinuity",
                    "category": "point_of_view",
                    "severity": "warn",
                    "subject_ids": ["char_001"],
                    "evidence_sources": ["candidate", "continuity_digest"],
                    "evidence": "透の内面独白が前章の観察者視点と接続していない。",
                    "repair_instruction": "視点転換のきっかけを本文内に示す。",
                }
            ],
        }
    )

    assessment = evaluate_semantic_continuity(_context(), _candidate(), gateway=gateway)
    review = review_chapter(_context(), _candidate(), semantic=assessment)

    finding = assessment.findings[0]
    assert finding.category == "point_of_view"
    assert finding.subject_ids == ["char_001"]
    assert finding.evidence_sources == ["candidate", "continuity_digest"]
    assert review.decision.value == "accept"
    prompt = gateway.messages[1]["content"]
    assert "Character arc targets:" in prompt
    assert "gm_vault" not in prompt


def test_semantic_gate_v2_accepts_legacy_v1_response_with_safe_defaults():
    assessment = evaluate_semantic_continuity(
        _context(),
        _candidate(),
        gateway=_Gateway(
            {
                "required_threads_covered": ["thread_famine_ledger"],
                "character_arc_target_ids_covered": ["char_001"],
                "findings": [
                    {
                        "code": "legacy_continuity_concern",
                        "severity": "warn",
                        "evidence": "帳簿の矛盾が次の行動にまだ接続していない。",
                        "repair_instruction": "透が帳簿を調べる動機を一文追加する。",
                    }
                ],
            }
        ),
    )

    finding = assessment.findings[0]
    assert finding.category.value == "other"
    assert finding.subject_ids == []
    assert finding.evidence_sources == []


def test_semantic_gate_v2_preserves_foreshadowing_and_act_promise_findings():
    assessment = evaluate_semantic_continuity(
        _context(),
        _candidate(),
        gateway=_Gateway(
            {
                "required_threads_covered": ["thread_famine_ledger"],
                "character_arc_target_ids_covered": ["char_001"],
                "findings": [
                    {
                        "code": "foreshadowing_unpaid",
                        "category": "foreshadowing",
                        "severity": "warn",
                        "subject_ids": ["thread_famine_ledger"],
                        "evidence_sources": ["candidate", "continuity_digest"],
                        "evidence": "窓の外の鐘の異常が再提示されず、既存の謎が薄れる。",
                        "repair_instruction": "鐘の異常を一度観察し、帳簿の矛盾との関係を示す。",
                    },
                    {
                        "code": "act_promise_missing",
                        "category": "act_promise",
                        "severity": "block",
                        "subject_ids": ["act_001"],
                        "evidence_sources": ["chapter_plan", "candidate"],
                        "evidence": "この章はactの約束である異常の発見を前進させていない。",
                        "repair_instruction": "異常を具体的に観察し、次章へ残る問いを置く。",
                    },
                ],
            }
        ),
    )
    review = review_chapter(_context(), _candidate(), semantic=assessment)

    assert [finding.category.value for finding in assessment.findings] == [
        "foreshadowing",
        "act_promise",
    ]
    assert [finding.severity for finding in assessment.findings] == ["warn", "block"]
    assert review.decision.value == "revise"


def test_semantic_gate_prompt_excludes_private_terms_and_absolute_paths():
    context = _context().model_copy(
        update={
            "hierarchical_continuity": "Act act_001: 透は帳簿の矛盾を見つけた。",
        }
    )
    gateway = _Gateway(
        {
            "required_threads_covered": ["thread_famine_ledger"],
            "character_arc_target_ids_covered": ["char_001"],
            "findings": [],
        }
    )

    evaluate_semantic_continuity(context, _candidate(), gateway=gateway)

    prompt = gateway.messages[1]["content"]
    for forbidden in ("gm_vault", "hidden_facts", "private_mind", "/Users/", "/home/"):
        assert forbidden not in prompt
    assert "Hierarchical continuity:" in prompt
    assert "透は帳簿の矛盾を見つけた。" in prompt
