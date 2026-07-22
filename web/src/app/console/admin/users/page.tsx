"use client";

import { useEffect, useMemo, useState } from "react";

type ManagedUser = {
  id: string;
  name: string;
  email: string;
  role: "普通用户" | "管理员";
  status: "正常" | "已禁用" | "待同意";
  joined: string;
};

type UserRecord = {
  id: string;
  name: string;
  email: string | null;
  role: "user" | "admin";
  status: "active" | "pending_consent" | "disabled";
  joined: string;
};
type UserResponse = { items?: UserRecord[] };

const roleLabel = (role: UserRecord["role"]) =>
  role === "admin" ? "管理员" : "普通用户";
const statusLabels: Record<UserRecord["status"], ManagedUser["status"]> = {
  active: "正常",
  disabled: "已禁用",
  pending_consent: "待同意",
};
const statusLabel = (status: UserRecord["status"]): ManagedUser["status"] =>
  statusLabels[status];

export default function UsersPage() {
  const [users, setUsers] = useState<ManagedUser[]>([]);
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("all");
  const [pending, setPending] = useState<string | null>(null);
  const [reason, setReason] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const fetchUsers = async (): Promise<ManagedUser[]> => {
    const response = await fetch("/api/admin/users", { cache: "no-store" });
    if (!response.ok) throw new Error("users_unavailable");
    const payload = (await response.json()) as UserResponse;
    return (payload.items ?? []).map((user) => ({
      id: user.id,
      name: user.name,
      email: user.email ?? "未提供邮箱",
      role: roleLabel(user.role),
      status: statusLabel(user.status),
      joined: new Date(user.joined).toLocaleDateString("zh-CN"),
    }));
  };
  const loadUsers = async () => {
    setLoading(true);
    setError(null);
    try {
      setUsers(await fetchUsers());
    } catch {
      setError("用户数据暂不可用；未加载任何演示账户。");
      setUsers([]);
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => {
    let cancelled = false;
    void fetchUsers()
      .then((nextUsers) => {
        if (!cancelled) setUsers(nextUsers);
      })
      .catch(() => {
        if (!cancelled) {
          setError("用户数据暂不可用；未加载任何演示账户。");
          setUsers([]);
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);
  const visible = useMemo(
    () =>
      users.filter(
        (user) =>
          (!query ||
            `${user.name}${user.email}`
              .toLowerCase()
              .includes(query.toLowerCase())) &&
          (status === "all" || user.status === status),
      ),
    [users, query, status],
  );
  const target = users.find((user) => user.id === pending);
  const confirm = async () => {
    if (!target) return;
    if (!reason.trim()) {
      setError("请填写操作原因，原因会写入管理员审计记录。");
      return;
    }
    const action = target.status === "正常" ? "disable" : "restore";
    try {
      const response = await fetch(`/api/admin/users/${target.id}/${action}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ confirmed: true, reason: reason.trim() }),
      });
      if (!response.ok) throw new Error("user_status_update_failed");
      setPending(null);
      setReason("");
      setNotice(
        action === "disable"
          ? "账户已禁用并记录审计。"
          : "账户已恢复并记录审计。",
      );
      await loadUsers();
    } catch {
      setError("账户状态更新失败，数据库没有被前端假保存覆盖。");
    }
  };
  return (
    <main className="admin-main">
      <header className="admin-page-heading">
        <div>
          <p className="eyebrow">系统管理 · 用户管理</p>
          <h1>角色权限要可见，每次变化都要留痕。</h1>
          <p>禁用与恢复不删除历史预测、公证、积分、盈亏或审计记录。</p>
        </div>
        <span className="status-chip">
          {loading ? "加载中" : `${users.length} 个账户`}
        </span>
      </header>
      {error ? <div className="inline-callout danger">{error}</div> : null}
      {notice ? <div className="inline-callout">{notice}</div> : null}
      <div className="user-filters">
        <label>
          <span>搜索用户</span>
          <input
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="姓名或邮箱"
          />
        </label>
        <label>
          <span>账户状态</span>
          <select
            value={status}
            onChange={(event) => setStatus(event.target.value)}
          >
            <option value="all">全部状态</option>
            <option>正常</option>
            <option>已禁用</option>
          </select>
        </label>
      </div>
      <section className="data-table-card">
        <div className="data-table user-table" role="table">
          <div className="data-table-row data-table-head" role="row">
            <span>用户</span>
            <span>角色</span>
            <span>状态</span>
            <span>加入时间</span>
            <span>操作</span>
          </div>
          {visible.map((user) => (
            <div className="data-table-row" role="row" key={user.id}>
              <div className="user-identity">
                <img src="/assets/icons/user-round.svg" alt="" />
                <span>
                  <strong>{user.name}</strong>
                  <small>{user.email}</small>
                </span>
              </div>
              <span>{user.role}</span>
              <span
                className={
                  user.status === "正常" ? "positive-copy" : "negative-copy"
                }
              >
                {user.status}
              </span>
              <time>{user.joined}</time>
              <button
                className="button secondary"
                type="button"
                disabled={user.role === "管理员" || user.status === "待同意"}
                onClick={() => setPending(user.id)}
              >
                {user.status === "正常" ? "禁用" : "恢复"}
              </button>
            </div>
          ))}
        </div>
        {!loading && !visible.length ? (
          <div className="wide-empty-state">
            <strong>{error ? "暂无可展示的用户" : "没有符合条件的用户"}</strong>
            <p>
              {error
                ? "请确认管理员 API 与数据库已就绪。"
                : "调整搜索词或状态筛选后再试。"}
            </p>
          </div>
        ) : null}
      </section>
      {target ? (
        <div className="confirm-overlay" role="presentation">
          <section
            role="dialog"
            aria-modal="true"
            aria-labelledby="confirm-title"
          >
            <p className="eyebrow">二次确认</p>
            <h2 id="confirm-title">
              {target.status === "正常" ? "禁用" : "恢复"} {target.name}？
            </h2>
            <p>
              {target.status === "正常"
                ? "该用户将立即无法登录，但历史数据与审计记录会保留。"
                : "该用户将恢复登录与普通用户权限。"}
            </p>
            <label>
              <span>操作原因</span>
              <input
                value={reason}
                onChange={(event) => setReason(event.target.value)}
                placeholder="填写原因以写入审计"
              />
            </label>
            <div>
              <button
                className="button secondary"
                type="button"
                onClick={() => setPending(null)}
              >
                取消
              </button>
              <button
                className="button primary inline"
                type="button"
                onClick={confirm}
              >
                确认{target.status === "正常" ? "禁用" : "恢复"}
              </button>
            </div>
          </section>
        </div>
      ) : null}
    </main>
  );
}
