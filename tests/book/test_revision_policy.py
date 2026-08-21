from __future__ import annotations

from living_narrative.book.chapters import ChapterCandidate
from living_narrative.book.coordinator import (
    apply_book_plan_proposal,
    record_chapter_candidate,
    start_chapter_production,
)
from living_narrative.book.lineage import load_chapter_lineage
from living_narrative.book.planning import StoryBible, build_book_plan_proposal
from living_narrative.book.review import (
    ChapterReview,
    ChapterReviewDecision,
    ChapterReviewMetrics,
    SemanticContinuityAssessment,
    SemanticContinuityFinding,
)
from living_narrative.book.revision_policy import RevisionAction, decide_revision_policy
from living_narrative.workspace.init import create_project


def _review(*findings: SemanticContinuityFinding) -> ChapterReview:
    return ChapterReview(
        chapter_id="chapter_001",
        decision=ChapterReviewDecision.REVISE,
        metrics=ChapterReviewMetrics(body_units=20, min_units=10, max_units=100),
        semantic=SemanticContinuityAssessment(findings=list(findings)),
    )


def _finding(category: str, severity: str = "block") -> SemanticContinuityFinding:
    return SemanticContinuityFinding(
        code=f"{category}_finding",
        category=category,
        severity=severity,
        subject_ids=["subject_001"],
        evidence_sources=["candidate"],
        evidence="reader-safe evidence",
        repair_instruction="repair this concern",
    )


def _workspace(tmp_path):
    project_yaml = create_project(tmp_path / "book", title="Book")
    workspace = project_yaml.parent / "workspace"
    proposal = build_book_plan_proposal(
        StoryBible.model_validate(
            {
                "premise": "霧の駅から帰還する。",
                "audience": "mystery readers",
                "acts": [
                    {
                        "id": "act_001",
                        "promise": "異常を知る。",
                        "chapter_ids": ["chapter_001"],
                    }
                ],
                "chapters": [
                    {
                        "id": "chapter_001",
                        "act_id": "act_001",
                        "planned_goal": "時刻表の矛盾を発見する。",
                        "target_word_range": {"min_words": 10, "max_words": 100},
                    }
                ],
            }
        )
    )
    apply_book_plan_proposal(workspace, proposal)
    return workspace


def test_revision_policy_maps_each_finding_category_to_explicit_action():
    decision = decide_revision_policy(
        _review(
            _finding("point_of_view"),
            _finding("required_thread"),
            _finding("act_promise"),
        )
    )

    assert [item.action.value for item in decision.findings] == [
        "part_revise",
        "replan",
        "act_redesign",
    ]
    assert decision.action is RevisionAction.ACT_REDESIGN
    assert decision.requires_author_action is True


def test_revision_policy_warn_is_advisory_without_author_action_requirement():
    decision = decide_revision_policy(_review(_finding("foreshadowing", severity="warn")))

    assert decision.action is RevisionAction.PART_REVISE
    assert decision.requires_author_action is False


def test_recorded_attempt_persists_revision_policy_decision_in_immutable_lineage(tmp_path):
    workspace = _workspace(tmp_path)
    candidate = ChapterCandidate(
        chapter_id="chapter_001",
        source_turns=[1],
        markdown="# chapter_001\n\n澪は時刻表の矛盾を見つけた。\n",
    )
    review = _review(_finding("required_thread"))

    start_chapter_production(workspace, "chapter_001")
    record_chapter_candidate(workspace, candidate, review)

    lineage = load_chapter_lineage(workspace / "books" / "chapters", "chapter_001")
    persisted = lineage.attempts[0].revision_decision
    assert persisted is not None
    assert persisted.action is RevisionAction.REPLAN
    assert persisted.findings[0].finding_code == "required_thread_finding"
