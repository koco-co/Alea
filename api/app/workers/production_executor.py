"""Production phase executor for the API and administrator-configured CLI runtimes.

The worker receives only frozen identifiers and configuration snapshots. Secrets are
loaded from the encrypted provider-secrets table at execution time and never enter
Celery payloads or logs. Database writes are idempotent on the phase business key.
"""

from __future__ import annotations

import hashlib
import json
import os
import socket
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from app.providers.catalog import get_api_provider
from app.providers.cli import CliProvider
from app.providers.contract import ProviderFailure, ProviderRequest
from app.runtime import ProviderFactory
from app.secrets.envelope import EnvelopeEncryption
from app.workers.tasks import (
    PhaseCommand,
    PhaseExecutionStore,
    PhaseHandler,
    PhaseOutcome,
    RoundtablePhase,
)


def create_phase_executor() -> Any:
    """Factory named by ``ALEA_PHASE_EXECUTOR_FACTORY`` in production."""

    from app.workers.tasks import PhaseExecutor

    return PhaseExecutor(
        store=PostgresPhaseExecutionStore(),
        handler=ProviderPhaseHandler(),
    )


class PostgresPhaseExecutionStore(PhaseExecutionStore):
    def __init__(self, *, lease_seconds: int = 180) -> None:
        self.database_url = os.getenv("DATABASE_URL_ALEA_WORKER", "").strip()
        if not self.database_url:
            raise RuntimeError("DATABASE_URL_ALEA_WORKER is required")
        self.lease_seconds = max(30, min(900, lease_seconds))

    async def claim(self, command: PhaseCommand, *, celery_task_id: str | None) -> bool:
        import psycopg

        owner = (celery_task_id or f"worker:{socket.gethostname()}")[:200]
        with psycopg.connect(self.database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    select status::text, lease_until
                    from roundtable_phase_runs
                    where business_idempotency_key = %s
                    for update
                    """,
                    (command.business_idempotency_key,),
                )
                row = cursor.fetchone()
                if row is None:
                    raise RuntimeError("phase_run_not_found")
                status, lease_until = row
                if status == "succeeded":
                    return False
                if (
                    status == "running"
                    and lease_until is not None
                    and lease_until > datetime.now(UTC)
                ):
                    return False
                cursor.execute(
                    """
                    update roundtable_phase_runs
                    set status = 'running', lease_owner = %s,
                        lease_until = now() + (%s * interval '1 second'),
                        started_at = coalesce(started_at, now()),
                        attempt = attempt + 1, error_code = null,
                        error_detail_redacted = null
                    where business_idempotency_key = %s
                    """,
                    (owner, self.lease_seconds, command.business_idempotency_key),
                )
                if command.phase is RoundtablePhase.REVIEW_PREDICTION:
                    context_id = str(command.payload.get("postmatch_review_context_id", "")).strip()
                    if context_id:
                        cursor.execute(
                            """
                            update public.settlement_reviews
                            set state='running', error_code=null
                            where context_id=%s::uuid and state='scheduled'
                            """,
                            (context_id,),
                        )
            connection.commit()
        return True

    async def commit_success(self, command: PhaseCommand, outcome: PhaseOutcome) -> None:
        import psycopg

        stored_phase = {
            RoundtablePhase.VOTE_SCORE: "score_vote",
            RoundtablePhase.VOTE_BET: "bet_vote",
        }.get(command.phase, command.phase.value)
        payload = json.dumps(dict(outcome.payload), ensure_ascii=False, separators=(",", ":"))
        usage = json.dumps(dict(outcome.usage or {}), ensure_ascii=False, separators=(",", ":"))
        with psycopg.connect(self.database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    select id, job_id, match_run_id
                    from roundtable_phase_runs
                    where business_idempotency_key = %s
                    for update
                    """,
                    (command.business_idempotency_key,),
                )
                phase_run = cursor.fetchone()
                if phase_run is None:
                    raise RuntimeError("phase_run_not_found")
                phase_run_id, job_id, match_run_id = phase_run
                cursor.execute(
                    """
                    insert into roundtable_results
                      (id, phase_run_id, job_id, match_run_id, ai_instance_id,
                       phase, output_schema_key, output_schema_version,
                       payload, payload_hash, usage)
                    values (%s::uuid, %s::uuid, %s::uuid, %s::uuid, %s::uuid,
                            %s, %s, 1, %s::jsonb, %s, %s::jsonb)
                    on conflict (phase_run_id) do nothing
                    """,
                    (
                        outcome.result_id,
                        phase_run_id,
                        job_id,
                        match_run_id,
                        command.instance_id,
                        stored_phase,
                        f"roundtable.{stored_phase}",
                        payload,
                        outcome.payload_hash,
                        usage,
                    ),
                )
                inserted = cursor.rowcount == 1
                if inserted:
                    cursor.execute(
                        """
                        insert into execution_audits
                          (job_id, first_success_result_id, reason, normalized_payload_hash)
                        values (%s::uuid, %s::uuid, %s, %s)
                        on conflict (job_id) do nothing
                        """,
                        (
                            job_id,
                            outcome.result_id,
                            "first_provider_phase_success",
                            outcome.payload_hash,
                        ),
                    )
                cursor.execute(
                    """
                    update roundtable_phase_runs
                    set status = 'succeeded', provider_request_id = %s,
                        finished_at = now(), lease_owner = null, lease_until = null
                    where business_idempotency_key = %s and status <> 'succeeded'
                    """,
                    (outcome.provider_request_id, command.business_idempotency_key),
                )
                if inserted:
                    self._append_event(
                        cursor,
                        str(job_id),
                        "roundtable.phase_succeeded",
                        {
                            "phase": command.phase.value,
                            "match_id": command.match_id,
                            "instance_id": command.instance_id,
                            "status": "succeeded",
                        },
                    )
                    self._advance(cursor, str(job_id), match_run_id, command)
            connection.commit()

    async def append_failure(
        self, command: PhaseCommand, *, code: str, detail_redacted: str
    ) -> None:
        import psycopg

        with psycopg.connect(self.database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    update roundtable_phase_runs
                    set status = 'failed', error_code = %s,
                        error_detail_redacted = %s, finished_at = now(),
                        lease_owner = null, lease_until = null
                    where business_idempotency_key = %s and status <> 'succeeded'
                    returning job_id, match_run_id
                    """,
                    (code[:100], detail_redacted[:500], command.business_idempotency_key),
                )
                row = cursor.fetchone()
                if row is not None:
                    job_id, match_run_id = row
                    self._append_event(
                        cursor,
                        str(job_id),
                        "roundtable.phase_failed",
                        {
                            "phase": command.phase.value,
                            "match_id": command.match_id,
                            "instance_id": command.instance_id,
                            "status": "failed",
                            "error_code": code[:100],
                        },
                    )
                    self._advance(cursor, str(job_id), match_run_id, command)
            connection.commit()

    def _append_event(
        self, cursor: Any, job_id: str, event_type: str, payload: Mapping[str, Any]
    ) -> None:
        cursor.execute(
            "select alea_worker_append_roundtable_event(%s::uuid, %s, %s::jsonb)",
            (job_id, event_type, json.dumps(dict(payload), ensure_ascii=False)),
        )

    def _advance(self, cursor: Any, job_id: str, match_run_id: Any, command: PhaseCommand) -> None:
        unit_filter = (
            "match_run_id = %s::uuid" if match_run_id is not None else "match_run_id is null"
        )
        args: tuple[Any, ...] = (job_id, command.phase.value, command.round_number)
        if match_run_id is not None:
            args += (str(match_run_id),)
        cursor.execute(
            f"""
            select count(*) filter (where status = 'succeeded'),
                   count(*) filter (where status in ('succeeded', 'failed')),
                   count(*)
            from roundtable_phase_runs
            where job_id = %s::uuid and phase = %s and round_number = %s
              and {unit_filter}
            """,
            args,
        )
        successful, terminal, total = cursor.fetchone()
        if terminal != total:
            return
        if successful < 3:
            if command.phase is RoundtablePhase.REVIEW_PREDICTION:
                cursor.execute(
                    """
                    update public.settlement_reviews
                    set state='failed', error_code='review_quorum_not_met'
                    where settlement_run_id in (
                      select settlement_run_id
                      from public.postmatch_review_contexts
                      where notarized_prediction_id in (
                        select id from public.notarized_predictions where job_id=%s::uuid
                      )
                    )
                    """,
                    (job_id,),
                )
                self._append_event(
                    cursor,
                    job_id,
                    "roundtable.review_failed",
                    {"successful": successful, "required": 3, "reason": "no_quorum"},
                )
            elif match_run_id is not None:
                cursor.execute(
                    "update roundtable_match_runs set state='no_quorum', state_version=state_version+1, terminal_reason='phase_quorum_not_met', updated_at=now() where id=%s::uuid and state not in ('eligible','no_quorum','terminated','failed')",
                    (str(match_run_id),),
                )
                self._append_event(
                    cursor,
                    job_id,
                    "roundtable.no_quorum",
                    {
                        "phase": command.phase.value,
                        "match_id": command.match_id,
                        "successful": successful,
                        "required": 3,
                    },
                )
                self._maybe_finish_parent(cursor, job_id)
            else:
                cursor.execute(
                    "update roundtable_jobs set state='no_quorum', state_version=state_version+1, terminal_reason='phase_quorum_not_met', updated_at=now() where id=%s::uuid and state not in ('completed','no_quorum','terminated','failed')",
                    (job_id,),
                )
                self._append_event(
                    cursor,
                    job_id,
                    "roundtable.no_quorum",
                    {"phase": command.phase.value, "successful": successful, "required": 3},
                )
            return

        next_phase = {
            RoundtablePhase.PREDICT_SCORE: RoundtablePhase.DEBATE_RESPONSE,
            RoundtablePhase.DEBATE_RESPONSE: RoundtablePhase.VOTE_SCORE,
            RoundtablePhase.FORM_BET: RoundtablePhase.DEBATE_BET,
            RoundtablePhase.DEBATE_BET: RoundtablePhase.VOTE_BET,
        }.get(command.phase)
        if next_phase is not None:
            self._enqueue_phase_set(
                cursor,
                job_id,
                str(match_run_id) if match_run_id is not None else None,
                command.match_id,
                next_phase,
                command.round_number,
            )
            if match_run_id is not None:
                self._set_match_state(cursor, str(match_run_id), next_phase)
            elif next_phase is RoundtablePhase.DEBATE_BET:
                cursor.execute(
                    "update roundtable_jobs set state='bet_debating', state_version=state_version+1, updated_at=now() where id=%s::uuid and state='bet_proposing'",
                    (job_id,),
                )
            elif next_phase is RoundtablePhase.VOTE_BET:
                cursor.execute(
                    "update roundtable_jobs set state='bet_voting', state_version=state_version+1, updated_at=now() where id=%s::uuid and state='bet_debating'",
                    (job_id,),
                )
        elif command.phase is RoundtablePhase.VOTE_SCORE and match_run_id is not None:
            cursor.execute(
                "update roundtable_match_runs set state='eligible', state_version=state_version+1, quorum_instance_count=3, quorum_provider_count=(select count(distinct provider_family) from roundtable_participants where job_id=%s::uuid), updated_at=now() where id=%s::uuid",
                (job_id, str(match_run_id)),
            )
            self._maybe_enqueue_bet(cursor, job_id)
        elif command.phase is RoundtablePhase.VOTE_BET:
            cursor.execute(
                "update roundtable_jobs set state='notarizing', state_version=state_version+1, updated_at=now() where id=%s::uuid and state='bet_voting'",
                (job_id,),
            )
            cursor.execute("select notarize_roundtable(%s::uuid)", (job_id,))
            self._append_event(
                cursor,
                job_id,
                "roundtable.published_pending",
                {"status": "notarized", "publish_after": "sales_cutoff"},
            )
        elif command.phase is RoundtablePhase.REVIEW_PREDICTION:
            cursor.execute(
                """
                update public.settlement_reviews sr
                set state='completed', completed_at=now(), error_code=null
                where sr.context_id = %s::uuid
                """,
                (str(command.payload.get("postmatch_review_context_id", "")),),
            )
            self._append_event(
                cursor,
                job_id,
                "roundtable.review_completed",
                {
                    "phase": command.phase.value,
                    "successful": successful,
                    "required": 3,
                    "postmatch_review_context_id": command.payload.get(
                        "postmatch_review_context_id"
                    ),
                },
            )

    def _set_match_state(self, cursor: Any, match_run_id: str, phase: RoundtablePhase) -> None:
        state = {
            RoundtablePhase.DEBATE_RESPONSE: "debating",
            RoundtablePhase.VOTE_SCORE: "score_voting",
        }.get(phase)
        if state:
            cursor.execute(
                "update roundtable_match_runs set state=%s, state_version=state_version+1, updated_at=now() where id=%s::uuid",
                (state, match_run_id),
            )

    def _enqueue_phase_set(
        self,
        cursor: Any,
        job_id: str,
        match_run_id: str | None,
        match_id: str | None,
        phase: RoundtablePhase,
        round_number: int,
    ) -> None:
        cursor.execute(
            "select ai_instance_id, frozen_config from roundtable_participants where job_id=%s::uuid order by codename",
            (job_id,),
        )
        for instance_id, participant_config in cursor.fetchall():
            key = f"{job_id}:{match_id or '-'}:{phase.value}:{round_number}:{instance_id}"
            cursor.execute(
                """
                insert into roundtable_phase_runs (job_id, match_run_id, ai_instance_id, phase, round_number, attempt, business_idempotency_key, status)
                values (%s::uuid, %s::uuid, %s::uuid, %s, %s, 1, %s, 'pending') on conflict (business_idempotency_key) do nothing returning id
                """,
                (job_id, match_run_id, str(instance_id), phase.value, round_number, key),
            )
            row = cursor.fetchone()
            if row is None:
                continue
            phase_run_id = str(row[0])
            self._enqueue_outbox(
                cursor,
                job_id,
                match_run_id,
                match_id,
                phase,
                round_number,
                str(instance_id),
                phase_run_id,
                participant_config,
            )

    def _enqueue_outbox(
        self,
        cursor: Any,
        job_id: str,
        match_run_id: str | None,
        match_id: str | None,
        phase: RoundtablePhase,
        round_number: int,
        instance_id: str,
        phase_run_id: str,
        participant_config: Mapping[str, Any],
    ) -> None:
        key = f"{job_id}:{match_id or '-'}:{phase.value}:{round_number}:{instance_id}"
        payload = {
            "job_id": job_id,
            "match_id": match_id,
            "phase": phase.value,
            "round_number": round_number,
            "instance_id": instance_id,
            "payload": {
                "phase_run_id": phase_run_id,
                "match_run_id": match_run_id,
                "participant_config": dict(participant_config),
            },
        }
        cursor.execute(
            "insert into outbox_events (topic, business_idempotency_key, payload) values ('roundtable.phase', %s, %s::jsonb) on conflict (business_idempotency_key) do nothing",
            ("phase:" + key, json.dumps(payload, ensure_ascii=False)),
        )

    def _maybe_enqueue_bet(self, cursor: Any, job_id: str) -> None:
        cursor.execute(
            "select count(*) filter (where state='eligible'), count(*) filter (where state in ('eligible','no_quorum','terminated','failed')), count(*) from roundtable_match_runs where job_id=%s::uuid",
            (job_id,),
        )
        eligible, terminal, total = cursor.fetchone()
        if terminal != total or eligible == 0:
            if terminal == total and eligible == 0:
                cursor.execute(
                    "update roundtable_jobs set state='no_quorum', state_version=state_version+1, terminal_reason='no_eligible_match_after_vote', updated_at=now() where id=%s::uuid and state not in ('completed','no_quorum','terminated','failed')",
                    (job_id,),
                )
            return
        cursor.execute(
            "select 1 from roundtable_phase_runs where job_id=%s::uuid and phase='form_bet' limit 1",
            (job_id,),
        )
        if cursor.fetchone() is not None:
            return
        cursor.execute(
            "update roundtable_jobs set state='bet_proposing', state_version=state_version+1, updated_at=now() where id=%s::uuid",
            (job_id,),
        )
        self._enqueue_phase_set(cursor, job_id, None, None, RoundtablePhase.FORM_BET, 0)

    def _maybe_finish_parent(self, cursor: Any, job_id: str) -> None:
        cursor.execute(
            "select count(*) filter (where state='eligible'), count(*) filter (where state in ('eligible','no_quorum','terminated','failed')), count(*) from roundtable_match_runs where job_id=%s::uuid",
            (job_id,),
        )
        eligible, terminal, total = cursor.fetchone()
        if terminal == total and eligible == 0:
            cursor.execute(
                "update roundtable_jobs set state='no_quorum', state_version=state_version+1, terminal_reason='all_match_runs_no_quorum', updated_at=now() where id=%s::uuid",
                (job_id,),
            )


class ProviderPhaseHandler(PhaseHandler):
    async def __call__(self, command: PhaseCommand) -> PhaseOutcome:
        import psycopg
        from psycopg.rows import dict_row

        with psycopg.connect(
            os.environ["DATABASE_URL_ALEA_WORKER"], row_factory=dict_row
        ) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    select i.model_id, i.timeout_seconds, i.reasoning_level,
                           c.id as connection_id, c.version, c.execution_mode::text,
                           c.runtime_key, c.api_url, c.executable_path,
                           p.key as provider_key, p.family,
                           s.ciphertext, s.ciphertext_nonce, s.wrapped_dek,
                           s.wrapped_dek_nonce, s.kek_version, s.secret_tail
                    from ai_instances i
                    join provider_connections c on c.id=i.connection_id
                    join ai_providers p on p.id=i.provider_id
                    left join provider_secrets s on s.connection_id=c.id and s.connection_version=c.version
                    where i.id=%s::uuid
                    """,
                    (command.instance_id,),
                )
                record = cursor.fetchone()
                review_context: Mapping[str, Any] | None = None
                review_context_id = command.payload.get("postmatch_review_context_id")
                if command.phase is RoundtablePhase.REVIEW_PREDICTION:
                    if not isinstance(review_context_id, str) or not review_context_id.strip():
                        raise ProviderFailure(
                            "postmatch_review_context_missing",
                            "post-match review context is missing",
                            retryable=False,
                        )
                    cursor.execute(
                        "select id, payload from public.postmatch_review_contexts where id=%s::uuid",
                        (review_context_id,),
                    )
                    context_row = cursor.fetchone()
                    if context_row is None or not isinstance(context_row["payload"], Mapping):
                        raise ProviderFailure(
                            "postmatch_review_context_not_found",
                            "post-match review context is not available",
                            retryable=False,
                        )
                    review_context = context_row["payload"]
        if record is None:
            raise ProviderFailure(
                "provider_instance_not_found", "provider instance not found", retryable=False
            )
        provider = self._provider(record)
        request = ProviderRequest(
            request_id=uuid4(),
            business_idempotency_key=command.business_idempotency_key,
            input_snapshot_id=_optional_uuid(
                review_context.get("prediction", {}).get("input_snapshot_id")
                if review_context is not None
                else None
            ),
            postmatch_review_context_snapshot_id=_optional_uuid(
                str(command.payload.get("postmatch_review_context_id"))
                if command.phase is RoundtablePhase.REVIEW_PREDICTION
                else None
            ),
            methodology_review_context_snapshot_id=None,
            history_context_version_id=None,
            lesson_set_version_id=None,
            model_id=str(record["model_id"]),
            connection_version=int(record["version"]),
            identity_prompt_version=1,
            core_methodology_version=1,
            phase_prompt_version=1,
            output_schema_version=1,
            tool_contract_version=1,
            generation_parameter_version=1,
            timeout_seconds=int(record["timeout_seconds"]),
            max_output_tokens=1200,
        )
        context = {
            "output_schema": {"type": "object", "additionalProperties": True},
            "messages": [
                {
                    "role": "system",
                    "content": "Return one JSON object only. Do not use tools, commands, files, MCP, or web access.",
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "phase": command.phase.value,
                            "match_id": command.match_id,
                            "payload": dict(command.payload),
                        },
                        ensure_ascii=False,
                        default=str,
                    ),
                },
            ],
        }
        if review_context is not None:
            context["postmatch_review"] = dict(review_context)
        method = getattr(provider, command.phase.value, None)
        if not callable(method):
            raise ProviderFailure(
                "provider_phase_unsupported",
                "provider does not support this phase",
                retryable=False,
            )
        result = await method(context, request)
        payload = dict(result.output)
        payload_hash = hashlib.sha256(
            json.dumps(
                payload, sort_keys=True, ensure_ascii=False, default=str, separators=(",", ":")
            ).encode()
        ).hexdigest()
        return PhaseOutcome(
            result_id=str(uuid4()),
            payload_hash=payload_hash,
            provider_request_id=result.provider_request_id,
            payload=payload,
            usage=result.usage.model_dump(mode="json"),
        )

    @staticmethod
    def _provider(record: Mapping[str, Any]) -> Any:
        mode = str(record["execution_mode"])
        if mode in {"cli", "codex_cli"}:
            return CliProvider(
                runtime_key=str(record["runtime_key"]),
                executable_path=str(record["executable_path"]),
            )
        definition = get_api_provider(str(record["provider_key"]))
        secret = ""
        if record["ciphertext"] is not None:
            secret = EnvelopeEncryption().decrypt(
                record,
                connection_id=str(record["connection_id"]),
                connection_version=int(record["version"]),
            )
        return ProviderFactory().create(
            definition.adapter,
            api_key=secret,
            base_url=str(record["api_url"]),
            requires_api_key=definition.requires_api_key,
            allow_local_http=definition.allow_local_http,
            supports_json_schema=definition.supports_json_schema,
        )


def _optional_uuid(value: Any) -> UUID | None:
    if value is None or not str(value).strip():
        return None
    try:
        return UUID(str(value))
    except ValueError:
        return None
