export interface TimelineSummaryInput {
  firstConsensus: number | null;
  finalConsensus: number | null;
  voteChanges: number;
  notarized: boolean;
}

export interface TimelineSummary {
  headline: string;
  detail: string;
}

export function summarizeTimeline(
  input: TimelineSummaryInput,
): TimelineSummary {
  const { firstConsensus, finalConsensus, voteChanges, notarized } = input;
  if (firstConsensus !== null && finalConsensus !== null) {
    const delta = finalConsensus - firstConsensus;
    return {
      headline: `${firstConsensus}% → ${finalConsensus}%`,
      detail: `${voteChanges} 位改票 · 共识增益 ${delta > 0 ? `+${delta}` : delta}pt`,
    };
  }
  if (notarized) {
    return {
      headline: "已公证",
      detail: `${voteChanges} 位改票 · 公证账本已冻结`,
    };
  }
  return {
    headline: "等待终投",
    detail: `${voteChanges} 位改票 · 事件持续补拉`,
  };
}
