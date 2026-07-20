from __future__ import annotations

import json

import pytest

from app.sources.importer import ImportPayloadError, parse_import_document


def fixture_document() -> dict[str, object]:
    return {
        "fixture_kind": "sporttery_sales_fixture",
        "fixture": True,
        "sporttery_sale_scope": True,
        "parser_version": "fixture-v1",
        "provenance_note": "Artificial Gate 0 parser fixture; not official sales data.",
        "records": [
            {
                "source_record_key": "fixture:2030-01-01:001",
                "sporttery_match_number": "FIXTURE-001",
                "business_date": "2030-01-01",
                "observed_at": "2030-01-01T08:00:00+08:00",
                "competition": {
                    "source_key": "fixture-world-cup",
                    "name": "世界杯 Fixture",
                    "country_code": "INT",
                    "competition_type": "cup",
                },
                "season": {
                    "source_key": "fixture-world-cup-2030",
                    "name": "2030 Fixture",
                    "starts_on": "2030-01-01",
                    "ends_on": "2030-12-31",
                },
                "home_team": {
                    "source_key": "fixture-home",
                    "name": "Fixture 主队",
                    "country_code": "TST",
                },
                "away_team": {
                    "source_key": "fixture-away",
                    "name": "Fixture 客队",
                    "country_code": "TST",
                },
                "kickoff_at": "2030-01-01T20:00:00+08:00",
                "sales_cutoff_at": "2030-01-01T19:55:00+08:00",
                "sales_status": "closed",
                "odds": [
                    {
                        "play_type": "HAD",
                        "values": {"H": "1.80", "D": "3.20", "A": "4.10"},
                        "observed_at": "2030-01-01T08:00:00+08:00",
                    }
                ],
            }
        ],
    }


def test_json_fixture_import_is_normalized_and_hashed_deterministically() -> None:
    content = json.dumps(fixture_document(), ensure_ascii=False)
    first = parse_import_document(content, content_format="json")
    second = parse_import_document(content, content_format="json")
    record = first["records"][0]

    assert first == second
    assert record["sporttery_match_number"] == "FIXTURE-001"
    assert len(record["raw_content_hash"]) == 64
    assert record["parser_version"] == "fixture-v1"


@pytest.mark.parametrize(
    "patch",
    [
        {"fixture": False},
        {"sporttery_sale_scope": False},
        {"fixture_kind": "generic_football"},
    ],
)
def test_import_rejects_unlabelled_or_out_of_scope_data(patch: dict[str, object]) -> None:
    document = {**fixture_document(), **patch}
    with pytest.raises(ImportPayloadError, match="invalid_fixture_import"):
        parse_import_document(json.dumps(document), content_format="json")


def test_csv_fixture_import_supports_admin_migration_path() -> None:
    csv_content = "\n".join(
        [
            (
                "source_record_key,sporttery_match_number,business_date,observed_at,"
                "competition_json,home_team_json,away_team_json,kickoff_at,"
                "sales_cutoff_at,sales_status"
            ),
            (
                "fixture:2030-01-01:001,FIXTURE-001,2030-01-01,2030-01-01T08:00:00+08:00,"
                '"{""source_key"":""fixture-cup"",""name"":""杯赛 Fixture"",'
                '""country_code"":""INT"",""competition_type"":""cup""}",'
                '"{""source_key"":""home"",""name"":""Fixture 主队"",""country_code"":""TST""}",'
                '"{""source_key"":""away"",""name"":""Fixture 客队"",""country_code"":""TST""}",'
                "2030-01-01T20:00:00+08:00,2030-01-01T19:55:00+08:00,closed"
            ),
        ]
    )
    parsed = parse_import_document(csv_content, content_format="csv")
    assert parsed["parser_version"] == "fixture-csv-v1"
    assert len(parsed["records"]) == 1
