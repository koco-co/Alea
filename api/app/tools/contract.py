from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Any, Mapping

from pydantic import BaseModel, ConfigDict, Field


class ToolName(StrEnum):
    LIST_SELECTION_CANDIDATES = "list_selection_candidates"
    GET_MATCH_DATA = "get_match_data"
    GET_TEAM_CURRENT_SEASON_STATS = "get_team_current_season_stats"
    CHECK_WEATHER = "check_weather"
    CALCULATE_TICKET = "calculate_ticket"


class ToolPhase(StrEnum):
    SELECTION = "selection"
    MATCH = "match"
    BET = "bet"


TOOL_PHASES: Mapping[ToolName, ToolPhase] = MappingProxyType(
    {
        ToolName.LIST_SELECTION_CANDIDATES: ToolPhase.SELECTION,
        ToolName.GET_MATCH_DATA: ToolPhase.MATCH,
        ToolName.GET_TEAM_CURRENT_SEASON_STATS: ToolPhase.MATCH,
        ToolName.CHECK_WEATHER: ToolPhase.MATCH,
        ToolName.CALCULATE_TICKET: ToolPhase.BET,
    }
)


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ListSelectionCandidatesArguments(StrictModel):
    selection_scope_snapshot_id: str = Field(min_length=1)
    page_cursor: str | None


class GetMatchDataArguments(StrictModel):
    input_snapshot_id: str = Field(min_length=1)
    match_id: str = Field(min_length=1)


class GetTeamCurrentSeasonStatsArguments(StrictModel):
    input_snapshot_id: str = Field(min_length=1)
    team_id: str = Field(min_length=1)


class CheckWeatherArguments(StrictModel):
    input_snapshot_id: str = Field(min_length=1)
    match_id: str = Field(min_length=1)


class TicketSelection(StrictModel):
    match_id: str = Field(min_length=1)
    play: str = Field(pattern="^(had|hhad|crs|ttg|hafu)$")
    offer_option_ids: list[str] = Field(min_length=1)

    def model_post_init(self, __context: Any) -> None:
        if len(self.offer_option_ids) != len(set(self.offer_option_ids)):
            raise ValueError("offer_option_ids must be unique")


class CalculateTicketArguments(StrictModel):
    bet_context_snapshot_id: str = Field(min_length=1)
    selections: list[TicketSelection] = Field(min_length=1)
    pass_types: list[str] = Field(min_length=1)
    multiplier: int = Field(ge=1, le=50)

    def model_post_init(self, __context: Any) -> None:
        if len(self.pass_types) != len(set(self.pass_types)):
            raise ValueError("pass_types must be unique")
        pairs = [(selection.match_id, selection.play) for selection in self.selections]
        if len(pairs) != len(set(pairs)):
            raise ValueError("ticket selections must be unique")


ToolArguments = (
    ListSelectionCandidatesArguments
    | GetMatchDataArguments
    | GetTeamCurrentSeasonStatsArguments
    | CheckWeatherArguments
    | CalculateTicketArguments
)


@dataclass(frozen=True, slots=True)
class ToolCall:
    name: ToolName
    arguments: ToolArguments

    @property
    def phase(self) -> ToolPhase:
        return TOOL_PHASES[self.name]

    @property
    def canonical_hash(self) -> str:
        encoded = json.dumps(
            {
                "name": self.name.value,
                "arguments": self.arguments.model_dump(mode="json"),
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True, slots=True)
class ToolDefinition:
    name: ToolName
    description: str
    parameters: Mapping[str, Any]
    result_schema_ref: str


TOOL_DEFINITIONS: tuple[ToolDefinition, ...] = (
    ToolDefinition(
        ToolName.LIST_SELECTION_CANDIDATES,
        "按稳定游标读取本桌冻结的选场候选池摘要",
        {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "selection_scope_snapshot_id": {"type": "string"},
                "page_cursor": {"type": ["string", "null"]},
            },
            "required": ["selection_scope_snapshot_id", "page_cursor"],
        },
        "tools.json#/$defs/selection_candidate_page",
    ),
    ToolDefinition(
        ToolName.GET_MATCH_DATA,
        "读取指定冻结输入快照中的赛前数据，不发起实时刷新",
        {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "input_snapshot_id": {"type": "string"},
                "match_id": {"type": "string"},
            },
            "required": ["input_snapshot_id", "match_id"],
        },
        "tools.json#/$defs/match_snapshot_view",
    ),
    ToolDefinition(
        ToolName.GET_TEAM_CURRENT_SEASON_STATS,
        "从冻结输入快照读取球队当前赛季数据",
        {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "input_snapshot_id": {"type": "string"},
                "team_id": {"type": "string"},
            },
            "required": ["input_snapshot_id", "team_id"],
        },
        "tools.json#/$defs/sourced_team_stats",
    ),
    ToolDefinition(
        ToolName.CHECK_WEATHER,
        "从冻结输入快照读取该场开赛时段天气，不接受任意地点或日期",
        {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "input_snapshot_id": {"type": "string"},
                "match_id": {"type": "string"},
            },
            "required": ["input_snapshot_id", "match_id"],
        },
        "tools.json#/$defs/sourced_weather",
    ),
    ToolDefinition(
        ToolName.CALCULATE_TICKET,
        "按冻结可售项确定性计算；赔率由服务端解析，模型不得提交赔率",
        {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "bet_context_snapshot_id": {"type": "string"},
                "selections": {
                    "type": "array",
                    "minItems": 1,
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "match_id": {"type": "string"},
                            "play": {"enum": ["had", "hhad", "crs", "ttg", "hafu"]},
                            "offer_option_ids": {
                                "type": "array",
                                "minItems": 1,
                                "uniqueItems": True,
                                "items": {"type": "string"},
                            },
                        },
                        "required": ["match_id", "play", "offer_option_ids"],
                    },
                },
                "pass_types": {
                    "type": "array",
                    "minItems": 1,
                    "uniqueItems": True,
                    "items": {"type": "string"},
                },
                "multiplier": {"type": "integer", "minimum": 1, "maximum": 50},
            },
            "required": [
                "bet_context_snapshot_id",
                "selections",
                "pass_types",
                "multiplier",
            ],
        },
        "tools.json#/$defs/ticket_calculation",
    ),
)


def parse_tool_call(value: Mapping[str, Any]) -> ToolCall:
    try:
        name = ToolName(str(value["name"]))
        arguments = value["arguments"]
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("invalid tool call envelope") from exc
    if not isinstance(arguments, Mapping):
        raise ValueError("tool call arguments must be an object")
    model: type[ToolArguments]
    if name is ToolName.LIST_SELECTION_CANDIDATES:
        model = ListSelectionCandidatesArguments
    elif name is ToolName.GET_MATCH_DATA:
        model = GetMatchDataArguments
    elif name is ToolName.GET_TEAM_CURRENT_SEASON_STATS:
        model = GetTeamCurrentSeasonStatsArguments
    elif name is ToolName.CHECK_WEATHER:
        model = CheckWeatherArguments
    else:
        model = CalculateTicketArguments
    return ToolCall(name, model.model_validate(arguments))


def provider_tool_definitions(*, phase: ToolPhase) -> tuple[Mapping[str, Any], ...]:
    return tuple(
        {
            "name": definition.name.value,
            "description": definition.description,
            "parameters": dict(definition.parameters),
        }
        for definition in TOOL_DEFINITIONS
        if TOOL_PHASES[definition.name] is phase
    )
