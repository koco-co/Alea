export default function MethodologyPage() {
  return (
    <main className="admin-main">
      <header className="admin-page-heading">
        <div>
          <p className="eyebrow">系统管理 · 推演方法</p>
          <h1>教训能提议改变，不能自动改变。</h1>
          <p>
            只有真实证据、无赛果泄露回测、AI
            评审和管理员确认记录才会进入发布门槛。
          </p>
        </div>
        <span className="status-chip warning">等待真实配置</span>
      </header>
      <section className="wide-empty-state">
        <strong>暂无已持久化的方法论提议</strong>
        <p>等待真实证据、回测与管理员确认记录。</p>
      </section>
      <section className="data-table-card">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">版本历史</p>
            <h2>核心方法论发布记录</h2>
          </div>
          <span className="status-chip warning">未加载</span>
        </div>
        <div className="wide-empty-state">
          <strong>不会使用静态提议或固定回测结果</strong>
          <p>接入真实方法论服务后，此处显示版本、证据、回测和审计记录。</p>
        </div>
      </section>
    </main>
  );
}
