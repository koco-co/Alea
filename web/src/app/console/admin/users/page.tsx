"use client";

import { useMemo, useState } from "react";

const seedUsers = [
  { id: "u1", name: "林舟", email: "lin@example.com", role: "普通用户", status: "正常", joined: "2026-07-02" },
  { id: "u2", name: "周岚", email: "lan@example.com", role: "普通用户", status: "已禁用", joined: "2026-06-18" },
  { id: "u3", name: "系统管理员", email: "admin@alea.local", role: "管理员", status: "正常", joined: "2026-05-01" },
] as const;

type ManagedUser = {
  id: string;
  name: string;
  email: string;
  role: "普通用户" | "管理员";
  status: "正常" | "已禁用";
  joined: string;
};

export default function UsersPage() {
  const [users, setUsers] = useState<ManagedUser[]>(seedUsers.map((user) => ({ ...user })));
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("all");
  const [pending, setPending] = useState<string | null>(null);
  const visible = useMemo(() => users.filter((user) => (!query || `${user.name}${user.email}`.toLowerCase().includes(query.toLowerCase())) && (status === "all" || user.status === status)), [users, query, status]);
  const target = users.find((user) => user.id === pending);
  const confirm = () => { if (!target) return; setUsers((items) => items.map((user) => user.id === target.id ? { ...user, status: user.status === "正常" ? "已禁用" : "正常" } : user)); setPending(null); };
  return <main className="admin-main"><header className="admin-page-heading"><div><p className="eyebrow">系统管理 · 用户管理</p><h1>角色权限要可见，每次变化都要留痕。</h1><p>禁用与恢复不删除历史预测、公证、积分、盈亏或审计记录。</p></div><span className="status-chip">{users.length} 个账户</span></header><div className="user-filters"><label><span>搜索用户</span><input type="search" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="姓名或邮箱" /></label><label><span>账户状态</span><select value={status} onChange={(event) => setStatus(event.target.value)}><option value="all">全部状态</option><option>正常</option><option>已禁用</option></select></label></div><section className="data-table-card"><div className="data-table user-table" role="table"><div className="data-table-row data-table-head" role="row"><span>用户</span><span>角色</span><span>状态</span><span>加入时间</span><span>操作</span></div>{visible.map((user) => <div className="data-table-row" role="row" key={user.id}><div className="user-identity"><img src="/assets/icons/user-round.svg" alt="" /><span><strong>{user.name}</strong><small>{user.email}</small></span></div><span>{user.role}</span><span className={user.status === "正常" ? "positive-copy" : "negative-copy"}>{user.status}</span><time>{user.joined}</time><button className="button secondary" type="button" disabled={user.role === "管理员"} onClick={() => setPending(user.id)}>{user.status === "正常" ? "禁用" : "恢复"}</button></div>)}</div>{!visible.length ? <div className="wide-empty-state"><strong>没有符合条件的用户</strong><p>调整搜索词或状态筛选后再试。</p></div> : null}</section><section className="audit-strip"><p className="eyebrow">最近操作</p><div><strong>恢复账户 · 周岚</strong><span>系统管理员 · 2026-07-18 14:32</span><span className="status-chip">已记录</span></div></section>{target ? <div className="confirm-overlay" role="presentation"><section role="dialog" aria-modal="true" aria-labelledby="confirm-title"><p className="eyebrow">二次确认</p><h2 id="confirm-title">{target.status === "正常" ? "禁用" : "恢复"} {target.name}？</h2><p>{target.status === "正常" ? "该用户将立即无法登录，但历史数据与审计记录会保留。" : "该用户将恢复登录与普通用户权限。"}</p><label><span>操作原因</span><input placeholder="填写原因以写入审计" /></label><div><button className="button secondary" type="button" onClick={() => setPending(null)}>取消</button><button className="button primary inline" type="button" onClick={confirm}>确认{target.status === "正常" ? "禁用" : "恢复"}</button></div></section></div> : null}</main>;
}
