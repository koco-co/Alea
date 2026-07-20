from __future__ import annotations

from enum import StrEnum
from typing import Any

from app.providers.contract import ProviderFailure, ProviderRequest, ProviderResult, Usage


class FakeMode(StrEnum):
    OK = "ok"
    TIMEOUT = "timeout"
    RATE_LIMIT = "rate_limit"
    INVALID_JSON = "invalid_json"
    REFUSAL = "refusal"


FIXTURES: dict[str, dict[str, Any]] = {
    "nominate_matches": {"nominations": [], "arguments": [], "fact_claims": []},
    "selection_debate": {"responses": [], "arguments": [], "fact_claims": []},
    "vote_matches": {"votes": []},
    "predict_score": {
        "match_id": "fixture-match",
        "full_time_score": {"home": 2, "away": 1},
        "half_time_score": {"home": 1, "away": 0},
        "alternative_scores": [{"home": 1, "away": 1}],
        "direction": "home",
        "direction_confidence": 71,
        "opponent_type": "U",
        "motivation_type": "U",
        "interaction_summary": "冻结数据不足，结论保持保守。",
        "risk_signals": ["阵容暂缺", "竞彩销售数据暂缺"],
        "arguments": [],
        "fact_claims": [],
        "missing_fields": ["lineup", "sporttery_offers"],
    },
    "debate_response": {
        "responses": [],
        "revised_full_time_score": None,
        "revised_half_time_score": None,
        "revised_direction_confidence": None,
        "arguments": [],
        "fact_claims": [],
    },
    "vote_score": {
        "match_id": "fixture-match",
        "full_time_score": {"home": 2, "away": 1},
        "half_time_score": {"home": 1, "away": 0},
        "direction": "home",
        "direction_confidence": 71,
        "reason": "基于冻结输入的测试终投。",
        "verified_fact_claim_ids": [],
    },
    "form_bet": {"decision": "no_bet", "plan_confidence": 90, "plan": None, "no_bet_reason": "缺少可核验竞彩销售数据。"},
    "debate_bet": {"decision": "no_bet", "plan_confidence": 90, "plan": None, "no_bet_reason": "缺少可核验竞彩销售数据。", "target_candidate_ids": ["candidate-no-bet"]},
    "vote_bet": {"candidate_id": "candidate-no-bet", "decision": "no_bet", "plan_confidence": 90, "reason": "保持空仓。", "verified_fact_claim_ids": []},
    "review_prediction": {"prediction_assessment": "测试复盘。", "root_causes": [], "lesson_candidates": []},
    "review_methodology": {"proposal_understanding": "测试提议。", "evidence_assessment": "证据仅用于合同测试。", "backtest_assessment": "未提供生产回测。", "risks": ["样本不足"], "decision": "oppose", "reason": "默认保持方法论不变。", "evidence_record_ids": ["fixture-evidence"], "proposed_revision": None},
}


class FakeProvider:
    def __init__(self, mode: FakeMode = FakeMode.OK) -> None:
        self.mode = mode

    async def _call(self, method: str, req: ProviderRequest) -> ProviderResult[dict[str, Any]]:
        if self.mode == FakeMode.TIMEOUT:
            raise ProviderFailure("timeout", "provider request timed out", retryable=True)
        if self.mode == FakeMode.RATE_LIMIT:
            raise ProviderFailure("rate_limited", "provider rate limited", retryable=True)
        if self.mode == FakeMode.INVALID_JSON:
            raise ProviderFailure("invalid_json", "provider returned invalid JSON", retryable=False)
        if self.mode == FakeMode.REFUSAL:
            raise ProviderFailure("refusal", "provider refused the request", retryable=False)
        return ProviderResult(
            request_id=req.request_id,
            provider_request_id=f"fake-{method}-{req.request_id}",
            model_id=req.model_id,
            output=FIXTURES[method],
            usage=Usage(input_tokens=10, output_tokens=20, total_tokens=30),
            finish_reason="stop",
            latency_ms=1,
        )

    async def nominate_matches(self, ctx: dict[str, Any], req: ProviderRequest) -> ProviderResult[dict[str, Any]]: return await self._call("nominate_matches", req)
    async def selection_debate(self, ctx: dict[str, Any], req: ProviderRequest) -> ProviderResult[dict[str, Any]]: return await self._call("selection_debate", req)
    async def vote_matches(self, ctx: dict[str, Any], req: ProviderRequest) -> ProviderResult[dict[str, Any]]: return await self._call("vote_matches", req)
    async def predict_score(self, ctx: dict[str, Any], req: ProviderRequest) -> ProviderResult[dict[str, Any]]: return await self._call("predict_score", req)
    async def debate_response(self, ctx: dict[str, Any], req: ProviderRequest) -> ProviderResult[dict[str, Any]]: return await self._call("debate_response", req)
    async def vote_score(self, ctx: dict[str, Any], req: ProviderRequest) -> ProviderResult[dict[str, Any]]: return await self._call("vote_score", req)
    async def form_bet(self, ctx: dict[str, Any], req: ProviderRequest) -> ProviderResult[dict[str, Any]]: return await self._call("form_bet", req)
    async def debate_bet(self, ctx: dict[str, Any], req: ProviderRequest) -> ProviderResult[dict[str, Any]]: return await self._call("debate_bet", req)
    async def vote_bet(self, ctx: dict[str, Any], req: ProviderRequest) -> ProviderResult[dict[str, Any]]: return await self._call("vote_bet", req)
    async def review_prediction(self, ctx: dict[str, Any], req: ProviderRequest) -> ProviderResult[dict[str, Any]]: return await self._call("review_prediction", req)
    async def review_methodology(self, ctx: dict[str, Any], req: ProviderRequest) -> ProviderResult[dict[str, Any]]: return await self._call("review_methodology", req)
