import Link from "next/link";

const todos = [
  ["待发布", "2", "/console/admin/publish"],
  ["待裁定赛果", "1", "/console/admin/settings?tab=results"],
  ["同步失败", "1", "/console/admin/sync?status=failed"],
  ["方法论提议", "3", "/console/admin/settings/methodology"],
] as const;

export function AdminTodos() {
  return (
    <section className="panel admin-todos" aria-labelledby="admin-todos-title">
      <div className="panel-heading"><div><p className="eyebrow">仅管理员可见</p><h2 id="admin-todos-title">待办事项</h2></div><span className="status-dot warning">7 项</span></div>
      <div className="todo-list">
        {todos.map(([label, count, href]) => <Link href={href} key={label}><span>{label}</span><strong>{count}</strong></Link>)}
      </div>
    </section>
  );
}
