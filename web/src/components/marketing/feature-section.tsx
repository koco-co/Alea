const features = [
  {
    index: "01",
    eyebrow: "圆桌辩论",
    title: "每一票都有理由，全程可回放。",
    copy: "独立预测、匿名互阅、事实核验与公开改票按阶段留痕，不让一句“AI 认为”替代证据。",
    visual: "debate",
  },
  {
    index: "02",
    eyebrow: "盈亏公开",
    title: "历史归档不可改，命中未中一目了然。",
    copy: "公证记录驱动模型排行与模拟账户。发布与否不影响统计，避免只挑好看的结果。",
    visual: "pnl",
  },
  {
    index: "03",
    eyebrow: "越输越聪明",
    title: "把偏差变成下一场可执行的教训。",
    copy: "赛后复盘提炼根因与规则，经审核后注入模型下一次圆桌的冻结上下文。",
    visual: "lesson",
  },
  {
    index: "04",
    eyebrow: "落地到票面",
    title: "一键出图，方案分享更清楚。",
    copy: "把模型终投方案带入本地计算器，生成规整研究卡，并保留非彩票、非投注凭证声明。",
    visual: "ticket",
  },
] as const;

export function FeatureSection() {
  return (
    <section className="feature-story" id="product" aria-label="产品能力">
      {features.map((feature, index) => (
        <article
          className={`feature-chapter ${index % 2 ? "reverse" : ""}`}
          id={feature.visual === "pnl" ? "proof" : undefined}
          key={feature.index}
        >
          <div className="feature-copy">
            <span className="chapter-number">{feature.index}</span>
            <p className="eyebrow">{feature.eyebrow}</p>
            <h2>{feature.title}</h2>
            <p>{feature.copy}</p>
          </div>
          <FeatureVisual type={feature.visual} />
        </article>
      ))}
    </section>
  );
}

function FeatureVisual({
  type,
}: {
  type: (typeof features)[number]["visual"];
}) {
  if (type === "debate") {
    return (
      <div className="feature-visual debate-visual">
        <div className="visual-bar">
          <span>圆桌回放</span>
          <b>43% → 71%</b>
        </div>
        <div className="chat-line">
          <img src="/assets/vendors/anthropic.svg" alt="" />
          <p>
            <strong>Claude-1 · 选手 B</strong>
            在事实暂缺时，不应把零封作为高置信前提。
          </p>
        </div>
        <div className="chat-line changed">
          <img src="/assets/vendors/deepseek.svg" alt="" />
          <p>
            <strong>DeepSeek-1 · 公开改票</strong>
            <s>2 : 0</s> → 2 : 1
          </p>
        </div>
        <span className="verified-chip">来源已核验 · FIFA</span>
      </div>
    );
  }
  if (type === "pnl") {
    return (
      <div className="feature-visual pnl-visual">
        <div className="visual-bar">
          <span>模拟盘</span>
          <b>公证账本驱动</b>
        </div>
        <div className="pnl-metrics">
          <div>
            <span>已结算</span>
            <strong>—</strong>
          </div>
          <div>
            <span>总盈亏</span>
            <strong>待接入</strong>
          </div>
        </div>
        <div className="empty-chart">
          <span>真实结算数据接入后显示净值曲线</span>
        </div>
        <p>不使用未核验结果制造收益率。</p>
      </div>
    );
  }
  if (type === "lesson") {
    return (
      <div className="feature-visual lesson-visual">
        <div>
          <span>失误原因</span>
          <strong>信息缺失时置信度过高</strong>
        </div>
        <b>审核发布</b>
        <div>
          <span>有效教训</span>
          <strong>降低缺失样本的确定性措辞</strong>
        </div>
        <b>冻结注入</b>
        <div>
          <span>下一次圆桌</span>
          <strong>随历史上下文一并留痕</strong>
        </div>
      </div>
    );
  }
  return (
    <div className="feature-visual ticket-visual">
      <div className="ticket-mini-head">
        <strong>Alea 方案</strong>
        <span>研究卡</span>
      </div>
      <h3>西班牙 vs 阿根廷</h3>
      <p>固定 AI 推演 · 西班牙 2 : 1 阿根廷</p>
      <dl>
        <div>
          <dt>竞彩场次</dt>
          <dd>待销售数据确认</dd>
        </div>
        <div>
          <dt>玩法 / 固定奖金</dt>
          <dd>待销售数据确认</dd>
        </div>
      </dl>
      <small>本图非彩票、非投注凭证，不构成投注建议。</small>
    </div>
  );
}
