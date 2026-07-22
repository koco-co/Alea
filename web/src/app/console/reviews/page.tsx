export default function ReviewsPage() {
  return (
    <main className="console-main research-page reviews-page">
      <div className="page-heading research-heading">
        <div>
          <p className="eyebrow">赛后复盘 · 败因沉淀</p>
          <h1>把“为什么错”变成下一次的规则。</h1>
          <p>仅展示已审核发布且能回溯到真实赛果、圆桌和审计证据的复盘。</p>
        </div>
        <span className="status-chip warning">等待真实复盘</span>
      </div>
      <div className="wide-empty-state">
        <strong>暂无可核验的真实复盘</strong>
        <p>官方赛果、结算和复盘审核记录完成后，内容才会进入这里。</p>
      </div>
    </main>
  );
}
