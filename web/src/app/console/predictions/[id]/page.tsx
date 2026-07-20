import Link from "next/link";

import { DebateTimeline } from "@/components/prediction/debate-timeline";
import { PredictionCard } from "@/components/prediction/prediction-card";
import type { RoundtableEvent } from "@/lib/realtime";

const events: RoundtableEvent[] = [
  {
    job_id: "n8c4-02",
    event_seq: 1,
    event_type: "selection_verified",
    created_at: "2026-07-19T12:00:00+08:00",
    payload: {
      phase: "selection",
      message: "FIFA Match 104 入围；赛事身份与开球时间已核验。",
      sources: ["FIFA · 采集 2026-07-19"],
    },
  },
  {
    job_id: "n8c4-02",
    event_seq: 2,
    event_type: "prediction",
    created_at: "2026-07-19T12:03:00+08:00",
    payload: {
      phase: "prediction",
      speaker_codename: "选手 B",
      message: "初稿预测 1:1（半场 0:1），置信度 61%。",
    },
  },
  {
    job_id: "n8c4-02",
    event_seq: 3,
    event_type: "claim_verified",
    created_at: "2026-07-19T12:06:00+08:00",
    payload: {
      phase: "debate",
      speaker_codename: "选手 C",
      message: "西班牙为欧洲冠军；阿根廷为卫冕世界冠军与南美冠军。",
      sources: ["FIFA · 采集 2026-07-19"],
    },
  },
  {
    job_id: "n8c4-02",
    event_seq: 4,
    event_type: "vote_changed",
    created_at: "2026-07-19T12:09:00+08:00",
    payload: {
      phase: "debate",
      speaker_codename: "选手 D",
      message: "零封假设过强，改为保留阿根廷一球。",
      previous_vote: "2:0",
      new_vote: "2:1",
    },
  },
  {
    job_id: "n8c4-02",
    event_seq: 5,
    event_type: "score_vote",
    created_at: "2026-07-19T12:12:00+08:00",
    payload: {
      phase: "score_vote",
      message: "比分终投完成：西班牙 2:1 阿根廷，半场 1:0。",
      consensus: 71,
    },
  },
  {
    job_id: "n8c4-02",
    event_seq: 6,
    event_type: "bet_vote",
    created_at: "2026-07-19T12:15:00+08:00",
    payload: {
      phase: "bet_vote",
      message: "竞彩销售数据待确认，本场仅推演，未形成竞猜方案。",
      consensus: 71,
    },
  },
  {
    job_id: "n8c4-02",
    event_seq: 7,
    event_type: "notarization",
    created_at: "2026-07-19T12:16:00+08:00",
    payload: {
      phase: "notarization",
      message: "公证示例 N8C4-02 已冻结；发布与否不改变本记录。",
    },
  },
];

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
        <DebateTimeline events={events} title="匿名交锋改变了最终结论" />
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
