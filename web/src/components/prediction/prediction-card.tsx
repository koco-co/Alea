import Link from "next/link";

export interface PredictionProjection {
  matchLabel: string;
  competitionLabel: string;
  kickoffLabel: string;
  scoreLabel?: string | null;
  halfTimeLabel?: string | null;
  consensusLabel?: string | null;
  statusLabel: string;
  auditLabel?: string | null;
  jobId?: string | null;
}

export function PredictionCard({
  compact = false,
  projection,
}: {
  compact?: boolean;
  projection?: PredictionProjection | null;
}) {
  if (!projection) {
    return (
      <article className={`prediction-card ${compact ? "compact" : ""}`}>
        <section
          className="prediction-consensus-layer no-quorum"
          aria-label="暂无真实公证投影"
        >
          <div className="prediction-score">
            <strong>— : —</strong>
            <span>等待后端投影</span>
          </div>
          <div className="prediction-decision">
            <span>暂无真实预测</span>
            <strong>未读取到可公开的公证记录</strong>
            <small>只有授权竞彩 Offer 与真实 Provider 结果才会展示</small>
          </div>
        </section>
        <footer className="prediction-actions-layer">
          <span>不使用固定球队、比分、票数或 Provider 文案</span>
          <Link className="button secondary" href="/console/fixtures">
            查看真实赛程
          </Link>
          <button
            className="button primary prediction-disabled"
            type="button"
            disabled
          >
            暂无可采用方案
          </button>
        </footer>
      </article>
    );
  }

  return (
    <article className={`prediction-card ${compact ? "compact" : ""}`}>
      <header className="prediction-fixture-layer">
        <div>
          <span>{projection.competitionLabel}</span>
          <h2>{projection.matchLabel}</h2>
          <p>{projection.kickoffLabel}</p>
        </div>
        <span className="status-chip">{projection.statusLabel}</span>
      </header>
      <section className="prediction-consensus-layer" aria-label="共识结论">
        <div className="prediction-score">
          <strong>{projection.scoreLabel ?? "— : —"}</strong>
          <span>{projection.halfTimeLabel ?? "半场待确认"}</span>
        </div>
        <div className="prediction-decision">
          <span>真实公证投影</span>
          <strong>{projection.consensusLabel ?? "等待共识"}</strong>
          <small>{projection.statusLabel}</small>
        </div>
      </section>
      <footer className="prediction-actions-layer">
        <span>{projection.auditLabel ?? "执行审计已脱敏"}</span>
        {projection.jobId ? (
          <Link
            className="button secondary"
            href={`/console/predictions/${projection.jobId}`}
          >
            查看圆桌回放
          </Link>
        ) : null}
      </footer>
    </article>
  );
}
