from __future__ import annotations

import os
from dataclasses import dataclass, field

import psycopg
import pytest

from pathlib import Path

MIGRATION = (
    Path(__file__).parents[2] / "supabase" / "migrations" / "20260720043525_realtime_triggers.sql"
)


def test_realtime_migration_records_platform_owned_policy_block() -> None:
    sql_text = MIGRATION.read_text(encoding="utf-8")
    assert "after insert on roundtable_events" in sql_text
    assert "supabase_realtime_admin" in sql_text
    assert "private-channel read policy must therefore be installed" in sql_text
    assert "grant execute on function can_read_roundtable_topic(text) to authenticated" in sql_text
    assert "for insert\nto authenticated" not in sql_text.casefold()


@dataclass
class EventBuffer:
    last_event_seq: int = 0
    events: dict[int, dict[str, object]] = field(default_factory=dict)
    needs_backfill: bool = False

    def accept(self, event: dict[str, object]) -> bool:
        seq = int(event["event_seq"])
        if seq <= self.last_event_seq or seq in self.events:
            return False
        if seq > self.last_event_seq + 1:
            self.needs_backfill = True
        self.events[seq] = event
        while self.last_event_seq + 1 in self.events:
            self.last_event_seq += 1
        self.needs_backfill = any(seq > self.last_event_seq + 1 for seq in self.events)
        return True


def test_subscribe_then_backfill_deduplicates_race() -> None:
    buffer = EventBuffer(last_event_seq=1)
    assert buffer.accept({"event_seq": 3, "source": "broadcast"})
    assert buffer.needs_backfill
    assert buffer.accept({"event_seq": 2, "source": "backfill"})
    assert buffer.last_event_seq == 3
    assert not buffer.needs_backfill
    assert not buffer.accept({"event_seq": 3, "source": "backfill-duplicate"})


def test_reconnect_backfill_recovers_gap_in_order() -> None:
    buffer = EventBuffer(last_event_seq=4)
    assert buffer.accept({"event_seq": 7})
    assert buffer.accept({"event_seq": 5})
    assert buffer.last_event_seq == 5
    assert buffer.accept({"event_seq": 6})
    assert buffer.last_event_seq == 7
    assert sorted(buffer.events) == [5, 6, 7]


def test_realtime_trigger_and_client_insert_denial_are_applied() -> None:
    database_url = os.getenv("GATE0_DATABASE_URL")
    if not database_url:
        pytest.skip("GATE0_DATABASE_URL is required for real G2 verification")
    with psycopg.connect(database_url) as connection, connection.cursor() as cursor:
        cursor.execute(
            "select count(*) from pg_trigger where tgname = 'roundtable_events_broadcast' and not tgisinternal"
        )
        assert cursor.fetchone()[0] == 1
        cursor.execute("select has_table_privilege('authenticated', 'realtime.messages', 'insert')")
        assert cursor.fetchone()[0] is False
