export function rankingEmptyState(
  status: "loading" | "ready" | "error",
  count: number,
) {
  if (status === "loading") return "正在加载排行榜";
  if (status === "error") return "排行榜暂时无法加载";
  if (count === 0) return "暂无已结算的公证预测";
  return `${count} 个模型`;
}
