from __future__ import annotations

import csv
import hashlib
import io
import json
from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ImportPayloadError(ValueError):
    """Stable validation error for administrator-supplied data."""


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CompetitionInput(StrictModel):
    source_key: str = Field(min_length=1, max_length=200)
    name: str = Field(min_length=1, max_length=200)
    country_code: str = Field(min_length=2, max_length=3)
    competition_type: str = Field(default="league", min_length=1, max_length=40)


class SeasonInput(StrictModel):
    source_key: str = Field(min_length=1, max_length=200)
    name: str = Field(min_length=1, max_length=100)
    starts_on: date | None = None
    ends_on: date | None = None


class TeamInput(StrictModel):
    source_key: str = Field(min_length=1, max_length=200)
    name: str = Field(min_length=1, max_length=200)
    country_code: str = Field(min_length=2, max_length=3)


class OddsInput(StrictModel):
    play_type: Literal["HAD", "HHAD", "CRS", "TTG", "HAFU"]
    values: dict[str, Any]
    observed_at: datetime

    @field_validator("observed_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("observed_at must be timezone-aware")
        return value


class ResultInput(StrictModel):
    home_score: int = Field(ge=0)
    away_score: int = Field(ge=0)
    status: Literal["pending"] = "pending"


class FixtureMatchInput(StrictModel):
    source_record_key: str = Field(min_length=1, max_length=300)
    sporttery_match_number: str = Field(min_length=1, max_length=40)
    business_date: date
    observed_at: datetime
    source_url: str | None = Field(default=None, max_length=2048)
    competition: CompetitionInput
    season: SeasonInput | None = None
    home_team: TeamInput
    away_team: TeamInput
    kickoff_at: datetime
    sales_cutoff_at: datetime | None = None
    sales_status: Literal["scheduled", "on_sale", "closed", "cancelled", "settled"]
    odds: list[OddsInput] = Field(default_factory=list)
    result: ResultInput | None = None

    @model_validator(mode="after")
    def validate_match(self) -> FixtureMatchInput:
        if self.observed_at.tzinfo is None or self.kickoff_at.tzinfo is None:
            raise ValueError("match timestamps must be timezone-aware")
        if self.sales_cutoff_at is not None:
            if self.sales_cutoff_at.tzinfo is None:
                raise ValueError("sales_cutoff_at must be timezone-aware")
            if self.sales_cutoff_at > self.kickoff_at:
                raise ValueError("sales_cutoff_at must not exceed kickoff_at")
        if self.home_team.source_key == self.away_team.source_key:
            raise ValueError("home and away teams must differ")
        return self


class FixtureImportDocument(StrictModel):
    fixture_kind: Literal["sporttery_sales_fixture"]
    fixture: Literal[True]
    sporttery_sale_scope: Literal[True]
    parser_version: str = Field(min_length=1, max_length=100)
    provenance_note: str = Field(min_length=1, max_length=1000)
    records: list[FixtureMatchInput] = Field(min_length=1, max_length=5000)


def parse_import_document(
    content: str, *, content_format: Literal["json", "csv"]
) -> dict[str, Any]:
    if len(content.encode("utf-8")) > 10_000_000:
        raise ImportPayloadError("import_payload_too_large")
    try:
        raw = json.loads(content) if content_format == "json" else _csv_document(content)
        document = FixtureImportDocument.model_validate(raw)
    except (json.JSONDecodeError, ValueError) as exc:
        raise ImportPayloadError("invalid_fixture_import") from exc
    return {
        "fixture_kind": document.fixture_kind,
        "parser_version": document.parser_version,
        "provenance_note": document.provenance_note,
        "records": [
            _normalize_record(record, parser_version=document.parser_version)
            for record in document.records
        ],
    }


def _normalize_record(record: FixtureMatchInput, *, parser_version: str) -> dict[str, Any]:
    raw_content = record.model_dump(mode="json")
    canonical = json.dumps(
        raw_content,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return {
        **raw_content,
        "parser_version": parser_version,
        "raw_content": raw_content,
        "raw_content_hash": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
    }


def _csv_document(content: str) -> dict[str, Any]:
    reader = csv.DictReader(io.StringIO(content))
    required = {
        "source_record_key",
        "sporttery_match_number",
        "business_date",
        "observed_at",
        "competition_json",
        "home_team_json",
        "away_team_json",
        "kickoff_at",
        "sales_status",
    }
    if reader.fieldnames is None or not required.issubset(reader.fieldnames):
        raise ImportPayloadError("csv_columns_missing")
    records: list[dict[str, Any]] = []
    try:
        for row in reader:
            records.append(
                {
                    "source_record_key": row["source_record_key"],
                    "sporttery_match_number": row["sporttery_match_number"],
                    "business_date": row["business_date"],
                    "observed_at": row["observed_at"],
                    "source_url": row.get("source_url") or None,
                    "competition": json.loads(row["competition_json"]),
                    "season": json.loads(row["season_json"]) if row.get("season_json") else None,
                    "home_team": json.loads(row["home_team_json"]),
                    "away_team": json.loads(row["away_team_json"]),
                    "kickoff_at": row["kickoff_at"],
                    "sales_cutoff_at": row.get("sales_cutoff_at") or None,
                    "sales_status": row["sales_status"],
                    "odds": json.loads(row["odds_json"]) if row.get("odds_json") else [],
                    "result": json.loads(row["result_json"]) if row.get("result_json") else None,
                }
            )
    except (KeyError, json.JSONDecodeError) as exc:
        raise ImportPayloadError("invalid_csv_fixture_import") from exc
    return {
        "fixture_kind": "sporttery_sales_fixture",
        "fixture": True,
        "sporttery_sale_scope": True,
        "parser_version": "fixture-csv-v1",
        "provenance_note": "Administrator-provided Gate 0 CSV fixture; not an official sales record.",
        "records": records,
    }
