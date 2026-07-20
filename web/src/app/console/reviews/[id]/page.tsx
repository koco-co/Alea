import Link from "next/link";

const modelReviews = [
  {
    name: "远见 · OpenAI",
    judgment: "法国会依靠中场压迫控制比赛，巴西在转换阶段难以形成连续推进。",
    deviation: "将控球优势直接等同于禁区控制，忽略两翼身后空间。",
    root: "伤停与首发资料暂缺时仍沿用了完整主力阵容假设。",
  },
  {
    name: "慎思 · Anthropic",
    judgment: "比赛节奏偏慢，法国能够将风险限制在中场区域。",
    deviation: "没有充分计入巴西替补边锋的纵向冲击。",
    root: "对阵容不确定性的置信度折扣不足。",
  },
  {
    name: "深策 · DeepSeek",
    judgment: "法国定位球具备优势，预测零封并取得两个进球。",
    deviation: "定位球优势判断没有转化为实际机会，零封概率明显高估。",
    root: "把历史均值当作当场确定事实，缺少临场校正。",
  },
];

export default async function ReviewDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return (
    <main className="console-main detail-page review-detail-page">
      <Link className="button secondary back-link" href="/console/reviews">
        返回复盘记录
      </Link>
      <header className="detail-heading">
        <div>
          <p className="eyebrow">复盘详情 · {id.toUpperCase()}</p>
          <h1>法国 1 : 2 巴西</h1>
          <p>
            已审核发布 · 2026-07-18 · 教训只进入对应 AI 后续新圆桌的冻结上下文。
          </p>
        </div>
        <span className="status-chip">已发布</span>
      </header>
      <section className="review-compare-panel">
        <div className="review-score-card">
          <span>当时推演</span>
          <strong>法国 2 : 0 巴西</strong>
          <p>方向：主胜 · 置信度 68%</p>
        </div>
        <div className="review-score-card actual">
          <span>实际赛果</span>
          <strong>法国 1 : 2 巴西</strong>
          <p>90 分钟赛果 · 已确认</p>
        </div>
        <div className="review-timeline">
          <p className="eyebrow">关键事件</p>
          {[
            ["24′", "巴西右路反击率先破门"],
            ["53′", "法国定位球扳平"],
            ["78′", "巴西替补边锋完成制胜进球"],
          ].map(([time, text]) => (
            <div key={time}>
              <strong>{time}</strong>
              <span>{text}</span>
            </div>
          ))}
        </div>
      </section>
      <section className="review-section">
        <div className="section-heading">
          <div>
            <p className="eyebrow">模型复盘</p>
            <h2>每个判断单独追责</h2>
          </div>
        </div>
        <div className="model-review-list">
          {modelReviews.map((review, index) => (
            <details open={index === 0} key={review.name}>
              <summary>
                {review.name}
                <span>展开分析</span>
              </summary>
              <div>
                <article>
                  <span>我当时的判断</span>
                  <p>{review.judgment}</p>
                </article>
                <article>
                  <span>偏差在哪</span>
                  <p>{review.deviation}</p>
                </article>
                <article>
                  <span>根因分析</span>
                  <p>{review.root}</p>
                </article>
              </div>
            </details>
          ))}
        </div>
      </section>
      <div className="review-detail-grid">
        <section className="review-section">
          <p className="eyebrow">共性偏差</p>
          <h2>多数模型共同踩坑</h2>
          <div className="common-bias">
            <strong>把资料缺失当作阵容稳定</strong>
            <p>三个模型都没有把首发未确认转化为足够的置信度折扣。</p>
          </div>
          <div className="common-bias">
            <strong>控球优势与防线安全混为一谈</strong>
            <p>法国控球更多，但两翼身后空间持续暴露。</p>
          </div>
        </section>
        <section className="review-section">
          <p className="eyebrow">改进要点</p>
          <h2>可执行规则</h2>
          <div className="lesson-row">
            <div>
              <strong>首发未确认时，方向置信度上限设为 62%</strong>
              <span>归属：远见 · OpenAI</span>
            </div>
            <span className="status-chip">有效 · 已注入 2 次</span>
          </div>
          <div className="lesson-row">
            <div>
              <strong>边路速度差大于阈值时提高反击进球预期</strong>
              <span>归属：慎思 · Anthropic</span>
            </div>
            <span className="status-chip">有效 · 尚未引用</span>
          </div>
        </section>
      </div>
      <footer className="related-links">
        <Link href="/console/predictions/n8c4-02">查看原预测卡</Link>
        <Link href="/console/predictions/n8c4-02">回放匿名辩论</Link>
      </footer>
    </main>
  );
}
