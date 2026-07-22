export default function PredictionsPage() {
  return (
    <main className="console-main research-page">
      <div className="page-heading research-heading">
        <div>
          <p className="eyebrow">太玄问机 · 今日推演</p>
          <h1>真实公证投影与圆桌回放。</h1>
          <p>
            只展示由授权竞彩 Offer、真实 Provider 执行与公证账本产生的记录。
          </p>
        </div>
        <div className="source-badges">
          <span>AI 推演数据</span>
          <span>来源：授权竞彩 Offer · 等待真实投影</span>
        </div>
      </div>
      <nav className="page-tabs" aria-label="推演视图">
        <a className="active" href="#today">
          今日推演
        </a>
        <a href="#history">历史推演</a>
        <a href="#states">生命周期状态</a>
      </nav>
      <div className="list-meta">
        <strong>今日 — 张</strong>
        <span>未取得可展示的公证预测</span>
      </div>
      <aside className="source-boundary">
        <strong>数据边界</strong>
        <div>
          <b>竞彩销售、首发、伤停、裁判与技术统计尚未取得可信快照</b>
          <span>相关字段统一显示待确认；不生成场次编号、赔率或命中结果。</span>
        </div>
      </aside>
      <div id="today" className="wide-empty-state">
        <strong>暂无可公开展示的预测</strong>
        <p>只有满足法定人数并完成公证的真实圆桌，才会出现在这里。</p>
      </div>
      <section className="wide-empty-state" id="history">
        <strong>暂无可核验的历史推演</strong>
        <p>官方赛果确认并完成真实结算后，记录才会进入历史筛选与模型统计。</p>
      </section>
    </main>
  );
}
