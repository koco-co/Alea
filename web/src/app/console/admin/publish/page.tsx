export default function PublishPage() {
  return (
    <main className="admin-main">
      <header className="admin-page-heading">
        <div>
          <p className="eyebrow">系统管理 · 发布审核 · PRD 15.3</p>
          <h1>真实公证投影进入审核后，才允许发布。</h1>
          <p>
            页面只显示从数据库读取的草稿，不生成固定比赛、票数、公证编号或审核结果。
          </p>
        </div>
        <span className="status-chip warning">暂无真实草稿</span>
      </header>
      <section className="wide-empty-state">
        <strong>暂无可审核的真实预测草稿</strong>
        <p>完成法定人数圆桌、公证和授权销售状态校验后，草稿才会投影到这里。</p>
      </section>
    </main>
  );
}
