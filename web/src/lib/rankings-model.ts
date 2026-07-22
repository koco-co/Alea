export type RankingRow = {
  ai_instance_id: string;
  display_name: string;
  formula_version_id: string;
  settled_count: number;
  participation_coverage: number;
  raw_score: number;
  smoothed_score: number;
  exact_score_rate: number;
  direction_rate: number;
  total_goals_rate: number;
  half_full_rate: number;
  eligible_for_rank: boolean;
  eligibility_reasons: string[];
  rank: number | null;
};

const numericFields = [
  "settled_count",
  "participation_coverage",
  "raw_score",
  "smoothed_score",
  "exact_score_rate",
  "direction_rate",
  "total_goals_rate",
  "half_full_rate",
] as const;

export function normalizeRankingRows(value: unknown): RankingRow[] {
  if (!Array.isArray(value)) return [];
  return value.filter(isRankingRow).map((row) => {
    const normalized = { ...row } as Record<string, unknown>;
    for (const field of numericFields) {
      normalized[field] = Number(row[field]);
    }
    return normalized as RankingRow;
  });
}

function isRankingRow(value: unknown): value is RankingRow {
  if (!value || typeof value !== "object") return false;
  const row = value as Record<string, unknown>;
  return (
    typeof row.ai_instance_id === "string" &&
    typeof row.display_name === "string" &&
    typeof row.formula_version_id === "string" &&
    typeof row.eligible_for_rank === "boolean" &&
    Array.isArray(row.eligibility_reasons) &&
    (typeof row.rank === "number" || row.rank === null) &&
    numericFields.every((field) => {
      const parsed = Number(row[field]);
      return row[field] !== null && Number.isFinite(parsed);
    })
  );
}

export function rankingEmptyState(
  status: "loading" | "ready" | "error",
  count: number,
) {
  if (status === "loading") return "正在加载排行榜";
  if (status === "error") return "排行榜暂时无法加载";
  if (count === 0) return "暂无已结算的公证预测";
  return `${count} 个模型`;
}
