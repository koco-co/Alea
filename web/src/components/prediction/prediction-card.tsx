import Link from "next/link";

import { ConsensusRing } from "./consensus-ring";
import { VoteBar, type VoteAgent } from "./vote-bar";

const primaryVotes: VoteAgent[] = [
  { name: "Claude-1", logo: "/assets/vendors/anthropic.svg", score: 88, reason: "事实缺失时降低零封假设，保留阿根廷一球。" },
  { name: "GPT-1", logo: "/assets/vendors/openai.svg", score: 86, reason: "欧洲冠军与卫冕冠军的对抗更接近小分差。" },
  { name: "Gemini-1", logo: "/assets/vendors/gemini.svg", score: 82, reason: "在现有可信快照下，2:1 是更稳健的模型判断。" },
  { name: "DeepSeek-1", logo: "/assets/vendors/deepseek.svg", instance: 1, score: 79, reason: "经过互相质询后从 2:0 改票到 2:1。" },
  { name: "Qwen-1", logo: "/assets/vendors/qwen.svg", score: 77, reason: "终投接受单球差结论。" },
];

const secondaryVotes: VoteAgent[] = [
  { name: "DeepSeek-2", logo: "/assets/vendors/deepseek.svg", instance: 2, score: 76, reason: "模型仍倾向平局，事实性陈述未引用缺失信息。" },
];

export function PredictionCard({ compact = false }: { compact?: boolean }) {
  return (
    <article className={`prediction-card ${compact ? "compact" : ""}`}>
      <header className="prediction-fixture-layer">
        <div className="prediction-flags" aria-hidden="true">
          <img src="/assets/teams/flag-spain.png" alt="" />
          <img src="/assets/teams/flag-argentina.png" alt="" />
        </div>
        <div>
          <span>2026 FIFA 世界杯 · 第 104 场 · 决赛</span>
          <h2>西班牙 vs 阿根廷</h2>
          <p>北京时间 7 月 20 日 03:00 · New York New Jersey Stadium</p>
        </div>
        <span className="status-chip warning">待竞彩销售数据确认</span>
      </header>

      <section className="prediction-consensus-layer" aria-label="共识结论">
        <div className="prediction-score">
          <strong>2 : 1</strong>
          <span>半场 1 : 0</span>
        </div>
        <ConsensusRing value={71} />
        <div className="prediction-decision">
          <span>固定 AI 原型输出</span>
          <strong>西班牙 2:1 阿根廷</strong>
          <small>终投预测 · 待赛果确认</small>
          <p>本场仅推演 · 竞彩销售数据待确认，尚未形成可采用方案</p>
        </div>
      </section>

      {!compact ? (
        <section className="prediction-vote-layer" aria-labelledby="vote-title">
          <div className="layer-heading"><div><span>终投分布</span><h3 id="vote-title">匿名票权冻结后揭示身份</h3></div><span className="status-chip">3 位改票</span></div>
          <VoteBar score="2 : 1" agents={primaryVotes} />
          <VoteBar score="1 : 1" agents={secondaryVotes} />
          <VoteBar score="2 : 0" agents={[{ name: "Kimi-1", logo: "/assets/vendors/kimi.png", score: 73, reason: "保留初稿判断，未使用未核验伤停信息。" }]} />
          <p className="vote-help">聚焦或点按头像可查看实例、综合准确分与投票理由；金色描边表示高准确分实例。</p>
        </section>
      ) : null}

      <footer className="prediction-actions-layer">
        <span>公证示例 N8C4-02 · AI 推演数据</span>
        <Link className="button secondary" href="/console/predictions/n8c4-02">圆桌辩论</Link>
        <button className="button primary prediction-disabled" type="button" disabled title="待竞彩销售数据确认">采用方案</button>
        <Link className="button secondary" href="/console/calculator?from=consensus">共识配置</Link>
      </footer>
    </article>
  );
}
