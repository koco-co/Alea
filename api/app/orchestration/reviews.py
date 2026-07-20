from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from enum import StrEnum
from types import MappingProxyType
from typing import Any, Iterable, Mapping, Sequence

from app.generated.schemas import ReviewAndLessons


class ReviewStatus(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class LessonStatus(StrEnum):
    CANDIDATE = "candidate"
    ACTIVE = "active"
    ARCHIVED = "archived"


@dataclass(frozen=True, slots=True)
class PostmatchReviewContextSnapshot:
    snapshot_id: str
    notarized_prediction_id: str
    input_snapshot_id: str
    core_methodology_version: int
    lesson_set_version_id: str
    verified_roundtable_event_ids: tuple[str, ...]
    result_version_id: str
    postmatch_source_record_ids: tuple[str, ...]
    payload: Mapping[str, Any]
    content_hash: str
    frozen_at: datetime


@dataclass(frozen=True, slots=True)
class Lesson:
    lesson_id: str
    review_id: str
    ai_instance_id: str
    rule: str
    evidence: str
    category: str
    severity: str
    evidence_record_ids: tuple[str, ...]
    revision: int = 1
    status: LessonStatus = LessonStatus.CANDIDATE
    published_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class ReviewDraft:
    review_id: str
    ai_instance_id: str
    context_snapshot_id: str
    output: ReviewAndLessons
    lessons: tuple[Lesson, ...]
    status: ReviewStatus
    revision: int
    created_at: datetime
    published_at: datetime | None = None
    approved_by: str | None = None


@dataclass(frozen=True, slots=True)
class LessonSetVersion:
    version_id: str
    ai_instance_id: str
    lesson_ids: tuple[str, ...]
    rendered_rules: tuple[str, ...]
    content_hash: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class ReviewSummary:
    context_snapshot_id: str
    review_ids: tuple[str, ...]
    assessments: tuple[str, ...]
    root_causes: tuple[str, ...]
    lesson_candidates: tuple[Lesson, ...]


def freeze_postmatch_review_context(
    *,
    snapshot_id: str,
    notarized_prediction: Mapping[str, Any],
    input_snapshot: Mapping[str, Any],
    core_methodology_version: int,
    lesson_set_version_id: str,
    verified_roundtable_events: Sequence[Mapping[str, Any]],
    result_version: Mapping[str, Any],
    postmatch_sources: Sequence[Mapping[str, Any]],
    now: datetime | None = None,
) -> PostmatchReviewContextSnapshot:
    """Freeze only the historical-at-prediction context plus independently confirmed result."""

    if core_methodology_version < 1:
        raise ValueError("core_methodology_version must be positive")
    input_snapshot_id = _required_id(input_snapshot, "id", "input_snapshot_id")
    prediction_id = _required_id(notarized_prediction, "id", "notarized_prediction_id")
    result_id = _required_id(result_version, "id", "result_version_id")
    if result_version.get("status") not in {"confirmed", "adjudicated"}:
        raise ValueError("review context requires an independently confirmed result version")
    event_ids = tuple(
        _required_id(event, "id", "roundtable_event_id") for event in verified_roundtable_events
    )
    if any(
        event.get("claim_status") not in {None, "verified"} for event in verified_roundtable_events
    ):
        raise ValueError("only verified roundtable events may enter review context")
    source_ids = tuple(
        _required_id(source, "id", "source_record_id") for source in postmatch_sources
    )
    payload = {
        "notarized_prediction": dict(notarized_prediction),
        "input_snapshot": dict(input_snapshot),
        "core_methodology_version": core_methodology_version,
        "lesson_set_version_id": lesson_set_version_id,
        "verified_roundtable_events": [dict(event) for event in verified_roundtable_events],
        "result_version": dict(result_version),
        "postmatch_sources": [dict(source) for source in postmatch_sources],
    }
    content_hash = _hash_payload(payload)
    return PostmatchReviewContextSnapshot(
        snapshot_id=_nonempty(snapshot_id, "snapshot_id"),
        notarized_prediction_id=prediction_id,
        input_snapshot_id=input_snapshot_id,
        core_methodology_version=core_methodology_version,
        lesson_set_version_id=_nonempty(lesson_set_version_id, "lesson_set_version_id"),
        verified_roundtable_event_ids=event_ids,
        result_version_id=result_id,
        postmatch_source_record_ids=source_ids,
        payload=MappingProxyType(payload),
        content_hash=content_hash,
        frozen_at=_utc(now),
    )


def create_review_draft(
    *,
    review_id: str,
    ai_instance_id: str,
    snapshot: PostmatchReviewContextSnapshot,
    provider_output: Mapping[str, Any] | ReviewAndLessons,
    now: datetime | None = None,
) -> ReviewDraft:
    output = (
        provider_output
        if isinstance(provider_output, ReviewAndLessons)
        else ReviewAndLessons.model_validate(provider_output)
    )
    allowed_evidence = set(snapshot.postmatch_source_record_ids) | set(
        snapshot.verified_roundtable_event_ids
    )
    lessons: list[Lesson] = []
    for index, candidate in enumerate(output.lesson_candidates):
        unknown = set(candidate.evidence_record_ids).difference(allowed_evidence)
        if unknown:
            raise ValueError("lesson evidence must belong to the frozen review context")
        lessons.append(
            Lesson(
                lesson_id=f"{review_id}:lesson:{index + 1}",
                review_id=review_id,
                ai_instance_id=ai_instance_id,
                rule=candidate.rule,
                evidence=candidate.evidence,
                category=candidate.category,
                severity=candidate.severity,
                evidence_record_ids=tuple(candidate.evidence_record_ids),
            )
        )
    return ReviewDraft(
        review_id=_nonempty(review_id, "review_id"),
        ai_instance_id=_nonempty(ai_instance_id, "ai_instance_id"),
        context_snapshot_id=snapshot.snapshot_id,
        output=output,
        lessons=tuple(lessons),
        status=ReviewStatus.DRAFT,
        revision=1,
        created_at=_utc(now),
    )


def publish_review(
    review: ReviewDraft,
    *,
    approved_lesson_ids: Iterable[str],
    approved_by: str,
    now: datetime | None = None,
) -> ReviewDraft:
    if review.status is not ReviewStatus.DRAFT:
        raise ValueError("only a draft review can be published")
    approved = frozenset(approved_lesson_ids)
    known = {lesson.lesson_id for lesson in review.lessons}
    if not approved.issubset(known):
        raise ValueError("approved lessons must belong to this review revision")
    timestamp = _utc(now)
    lessons = tuple(
        replace(
            lesson,
            status=LessonStatus.ACTIVE if lesson.lesson_id in approved else LessonStatus.ARCHIVED,
            published_at=timestamp if lesson.lesson_id in approved else None,
        )
        for lesson in review.lessons
    )
    return replace(
        review,
        lessons=lessons,
        status=ReviewStatus.PUBLISHED,
        published_at=timestamp,
        approved_by=_nonempty(approved_by, "approved_by"),
    )


def aggregate_review_drafts(drafts: Sequence[ReviewDraft]) -> ReviewSummary:
    """Combine independently generated self-reviews without changing their evidence."""

    if not drafts:
        raise ValueError("at least one review draft is required")
    snapshot_ids = {draft.context_snapshot_id for draft in drafts}
    if len(snapshot_ids) != 1:
        raise ValueError("review drafts must use the same frozen postmatch context")
    if any(draft.status is not ReviewStatus.DRAFT for draft in drafts):
        raise ValueError("only draft revisions may be aggregated")
    root_causes = tuple(
        dict.fromkeys(cause for draft in drafts for cause in draft.output.root_causes)
    )
    return ReviewSummary(
        context_snapshot_id=drafts[0].context_snapshot_id,
        review_ids=tuple(draft.review_id for draft in drafts),
        assessments=tuple(draft.output.prediction_assessment for draft in drafts),
        root_causes=root_causes,
        lesson_candidates=tuple(lesson for draft in drafts for lesson in draft.lessons),
    )


def build_lesson_set_version(
    *,
    version_id: str,
    ai_instance_id: str,
    published_reviews: Sequence[ReviewDraft],
    now: datetime | None = None,
) -> LessonSetVersion:
    active = sorted(
        (
            lesson
            for review in published_reviews
            if review.status is ReviewStatus.PUBLISHED and review.ai_instance_id == ai_instance_id
            for lesson in review.lessons
            if lesson.status is LessonStatus.ACTIVE
        ),
        key=lambda lesson: (
            lesson.category,
            lesson.published_at or review_epoch(),
            lesson.lesson_id,
        ),
    )
    rules = tuple(lesson.rule for lesson in active)
    return LessonSetVersion(
        version_id=_nonempty(version_id, "version_id"),
        ai_instance_id=_nonempty(ai_instance_id, "ai_instance_id"),
        lesson_ids=tuple(lesson.lesson_id for lesson in active),
        rendered_rules=rules,
        content_hash=_hash_payload(
            {"lesson_ids": [lesson.lesson_id for lesson in active], "rules": rules}
        ),
        created_at=_utc(now),
    )


def archive_lesson(lesson: Lesson) -> Lesson:
    return replace(lesson, status=LessonStatus.ARCHIVED, revision=lesson.revision + 1)


def review_epoch() -> datetime:
    return datetime(1970, 1, 1, tzinfo=UTC)


def _required_id(value: Mapping[str, Any], key: str, name: str) -> str:
    identifier = value.get(key)
    if not isinstance(identifier, str):
        raise ValueError(f"{name} must be present")
    return _nonempty(identifier, name)


def _nonempty(value: str, name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{name} must not be empty")
    return normalized


def _hash_payload(value: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _utc(value: datetime | None) -> datetime:
    timestamp = value or datetime.now(UTC)
    if timestamp.tzinfo is None:
        raise ValueError("timestamps must be timezone-aware")
    return timestamp.astimezone(UTC)
