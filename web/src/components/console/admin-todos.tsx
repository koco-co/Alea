export function AdminTodos() {
  return (
    <section className="panel admin-todos" aria-labelledby="admin-todos-title">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">仅管理员可见</p>
          <h2 id="admin-todos-title">待办事项</h2>
        </div>
        <span className="status-dot warning">待后端投影</span>
      </div>
      <div className="todo-list">
        <p className="wide-empty-state">暂无已同步的管理员待办。</p>
      </div>
    </section>
  );
}
