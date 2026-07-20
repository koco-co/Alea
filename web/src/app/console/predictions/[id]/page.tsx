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
          <p>回放展示真实身份，并保留它们在辩论当时使用的匿名代号。</p>
        </div>
        <span className="status-chip">待赛果确认</span>
      </header>
      <PredictionCard compact />
      <div className="debate-detail-grid">
        <RoundtableEventReplay jobId={id} />
        <aside className="notary-panel">
          <p className="eyebrow">公证摘要</p>
          <strong>N8C4-02</strong>
          <dl>
            <div>
              <dt>冻结阵容</dt>
              <dd>LINEUP-7.4</dd>
            </div>
            <div>
              <dt>输入快照</dt>
              <dd>INPUT-M104-20260719</dd>
            </div>
            <div>
              <dt>票权版本</dt>
              <dd>VOTE-7.1</dd>
            </div>
            <div>
              <dt>规则版本</dt>
              <dd>SPORTTERY-2026.07</dd>
            </div>
          </dl>
          <p>
            只展示脱敏引用，不包含 Provider 密钥、成本、请求头或内部错误正文。
          </p>
        </aside>
      </div>
    </main>
  );
}
