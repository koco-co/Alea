export const ROUND_TABLE_PHASES = [
  "选场提名",
  "匿名互阅",
  "选场终投",
  "独立预测",
  "匿名辩论",
  "比分终投",
  "组单提案",
  "组单辩论",
  "方案终投",
] as const;

const PHASE_INDEX: Record<string, number> = {
  select_nomination: 0,
  select_debate: 1,
  select_vote: 2,
  predict_score: 3,
  prediction: 3,
  debate_response: 4,
  debate: 4,
  vote_score: 5,
  score_vote: 5,
  form_bet: 6,
  debate_bet: 7,
  vote_bet: 8,
  bet_vote: 8,
  notarization: 8,
  notarized: 8,
  publish: 8,
};

export function roundtablePhaseIndex(
  latestPhase: string | undefined,
  hasEvents: boolean,
): number {
  if (!hasEvents) return 0;
  if (!latestPhase) return ROUND_TABLE_PHASES.length - 1;
  return Math.min(
    PHASE_INDEX[latestPhase] ?? ROUND_TABLE_PHASES.length - 1,
    ROUND_TABLE_PHASES.length - 1,
  );
}
