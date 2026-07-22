import Link from "next/link";

import { PredictionCard } from "@/components/prediction/prediction-card";
import { RoundtableEventReplay } from "@/components/prediction/roundtable-event-replay";

export default async function PredictionDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return (
    <main className="console-main detail-page">
      <Link className="button secondary back-link" href="/console/predictions">
        返回今日推演
      </Link>
      <header className="detail-heading">
        <div>
          <p className="eyebrow">推演详情 · 辩论回放</p>
          <h1>公证记录 {id.toUpperCase()}</h1>
          <p>
            只有真实数据库事件、Provider receipt 和公证记录完成后才会展示回放。
          </p>
        </div>
        <span className="status-chip warning">等待真实记录</span>
      </header>
      <PredictionCard compact />
      <div className="debate-detail-grid">
        <RoundtableEventReplay jobId={id} />
        <aside className="notary-panel">
          <p className="eyebrow">公证摘要</p>
          <strong>等待真实公证数据</strong>
          <p>
            读取完成后只展示脱敏引用，不包含 Provider
            密钥、成本、请求头或内部错误正文。
          </p>
        </aside>
      </div>
    </main>
  );
}
