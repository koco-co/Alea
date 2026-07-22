import type { CalculatorMode } from "./match-selector";

export function TicketCardImage({
  mode,
  multiplier,
}: {
  mode: CalculatorMode;
  multiplier: number;
}) {
  void mode;
  void multiplier;
  return (
    <div className="ticket-card-image" id="ticket-card-image">
      <header>
        <div>
          <strong>Alea · 方案预览</strong>
        </div>
        <span>不可生成</span>
      </header>
      <div className="wide-empty-state">
        <strong>等待真实竞彩销售数据</strong>
        <p>
          比赛、玩法、赔率、销售窗口和 Provider 结果全部来自已核验后台数据。
        </p>
      </div>
      <footer>
        <strong>理性研究</strong>
        <p>没有真实 Offer 和完整审计证据时，不生成方案卡。</p>
      </footer>
    </div>
  );
}

export async function createTicketCardBlob(): Promise<Blob> {
  throw new Error("真实方案卡数据尚未加载");
}
