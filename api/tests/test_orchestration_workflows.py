from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from app.orchestration.methodology import (
    BacktestAttempt,
    LessonEvidence,
    MethodologyTriggerSettings,
    ProposalStatus,
    aggregate_methodology_proposals,
    evaluate_paired_backtest,
    resolve_methodology_review,
)
from app.orchestration.notifications import (
    NotificationKind,
    NotificationPreference,
    generate_notifications,
    ticket_terminal_notification,
)
from app.orchestration.phases.debate import (
    anonymize_and_shuffle_messages,
    assign_codenames,
)
from app.orchestration.phases.select import (
    build_rest_announcement_draft,
    resolve_selection_phase,
)
from app.orchestration.reviews import (
    LessonStatus,
    build_lesson_set_version,
    create_review_draft,
    freeze_postmatch_review_context,
    publish_review,
)
from app.orchestration.voting import CandidateVote, SelectionVote


def test_ticket_notification_is_emitted_once_after_all_legs_finish() -> None:
    pending = ticket_terminal_notification(
        user_id="user-1",
        ticket_id="ticket-1",
        settlement_run_id="settlement-1",
        leg_states=["hit", "waiting"],
        title="方案已结算",
        body="查看结果",
        payload={},
    )
    assert pending is None

    candidate = ticket_terminal_notification(
        user_id="user-1",
        ticket_id="ticket-1",
        settlement_run_id="settlement-1",
        leg_states=["hit", "miss"],
        title="方案已结算",
        body="查看结果",
        payload={},
    )
    assert candidate is not None
    preference = NotificationPreference("user-1", frozenset({NotificationKind.TICKET_SETTLED}))
    generated = generate_notifications(
        [candidate, candidate], {"user-1": preference}, now=datetime.now(UTC)
    )
    assert len(generated) == 1


def test_review_only_injects_published_active_lessons() -> None:
    snapshot = freeze_postmatch_review_context(
        snapshot_id="review-context-1",
        notarized_prediction={"id": "prediction-1"},
        input_snapshot={"id": "input-1"},
        core_methodology_version=3,
        lesson_set_version_id="lesson-set-2",
        verified_roundtable_events=[{"id": "event-1", "claim_status": "verified"}],
        result_version={"id": "result-1", "status": "confirmed"},
        postmatch_sources=[{"id": "source-1"}],
    )
    draft = create_review_draft(
        review_id="review-1",
        ai_instance_id="ai-1",
        snapshot=snapshot,
        provider_output={
            "prediction_assessment": "低估了风格克制。",
            "root_causes": ["style"],
            "lesson_candidates": [
                {
                    "rule": ("遇到高压逼抢时，下调后场出球不稳球队的方向置信度。"),
                    "evidence": "赛后事件显示持续被压迫。",
                    "category": "style_interaction",
                    "severity": "high",
                    "evidence_record_ids": ["source-1"],
                }
            ],
        },
    )
    published = publish_review(
        draft,
        approved_lesson_ids=[draft.lessons[0].lesson_id],
        approved_by="admin-1",
    )
    assert published.lessons[0].status is LessonStatus.ACTIVE
    lesson_set = build_lesson_set_version(
        version_id="lesson-set-3",
        ai_instance_id="ai-1",
        published_reviews=[published],
    )
    assert lesson_set.lesson_ids == (draft.lessons[0].lesson_id,)


def test_methodology_requires_three_matches_and_twenty_backtest_samples() -> None:
    lessons = [
        LessonEvidence(
            lesson_id=f"lesson-{index}",
            review_id=f"review-{index}",
            match_id=f"match-{index}",
            ai_instance_id="ai-1",
            category="style_interaction",
            rule="遇到高压逼抢时降低方向置信度",
        )
        for index in range(3)
    ]
    proposals = aggregate_methodology_proposals(
        lessons, MethodologyTriggerSettings(), now=datetime.now(UTC)
    )
    assert len(proposals) == 1

    attempts = _backtest_attempts(match_count=19)
    with pytest.raises(ValueError, match="at least 20"):
        evaluate_paired_backtest(attempts, attempts_per_instance=2, bootstrap_iterations=100)


def test_methodology_support_at_sixty_percent_requires_admin_confirmation() -> None:
    votes = [
        CandidateVote("a", "openai", "support", Decimal("80"), Decimal("1")),
        CandidateVote("b", "anthropic", "support", Decimal("80"), Decimal("1")),
        CandidateVote("c", "openai", "oppose", Decimal("80"), Decimal("1")),
    ]
    result = resolve_methodology_review(votes)
    assert result.proposal_status is ProposalStatus.PENDING_ADMIN_CONFIRMATION


def test_zero_selection_creates_rest_draft_and_codenames_stay_anonymous() -> None:
    votes = [
        SelectionVote("a", "openai", "m1", False, Decimal("70"), "12:00"),
        SelectionVote("b", "anthropic", "m1", False, Decimal("70"), "12:00"),
        SelectionVote("c", "openai", "m1", False, Decimal("70"), "12:00"),
    ]
    result = resolve_selection_phase(votes, maximum_matches=3)
    announcement = build_rest_announcement_draft(
        job_id="job-1", business_date=date(2026, 7, 20), result=result
    )
    assert announcement is not None
    assert announcement.title == "今日休战"

    mapping = assign_codenames(["a", "b", "c"], codename_seed="fixed")
    messages = anonymize_and_shuffle_messages(
        [{"instance_id": "a", "message": "A"}, {"instance_id": "b", "message": "B"}],
        codename_map=mapping,
        own_instance_id="a",
        shuffle_seed="fixed-shuffle",
        match_id="m1",
        round_number=1,
    )
    assert {message["speaker_codename"] for message in messages} == {
        "self",
        mapping["b"],
    }


def _backtest_attempts(*, match_count: int) -> list[BacktestAttempt]:
    attempts: list[BacktestAttempt] = []
    for match_index in range(match_count):
        for attempt_index in range(2):
            for variant, value in (("OLD", Decimal("0")), ("NEW", Decimal("1"))):
                attempts.append(
                    BacktestAttempt(
                        sample_id=f"match-{match_index}",
                        instance_id="ai-1",
                        attempt_index=attempt_index,
                        variant=variant,
                        metrics={"exact_score": value},
                        valid_output=True,
                        execution_succeeded=True,
                    )
                )
    return attempts
