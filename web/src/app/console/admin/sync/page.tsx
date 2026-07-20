"use client";

import { useState } from "react";

const initialLogs = [
  ["20:08", "FIFA · Match 104", "成功", "版本未变化"],
  ["19:42", "赛前阵容 · Match 104", "失败", "可信来源未连接"],
  ["19:30", "竞彩销售快照 · 今日", "跳过", "连接尚未配置"],
] as const;

export default function SyncPage() {
  const [scope, setScope] = useState("today");
  const [running, setRunning] = useState(false);
  const [logs, setLogs] = useState<readonly (readonly string[])[]>(initialLogs);
  const run = () => {
    setRunning(true);
    setTimeout(() => {
      setLogs([
        [
          "刚刚",
          scope === "today" ? "今日全部来源" : "指定日期 · 2026-07-20",
          "部分失败",
          "阵容来源仍未连接",
        ],
        ...logs,
      ]);
      setRunning(false);
    }, 650);
  };
  return (
    <main className="admin-main">
      <header className="admin-page-heading">
        <div>
          <p className="eyebrow">系统管理 · 数据同步 · PRD 15.5</p>
          <h1>先验证来源，再允许事实进入推演。</h1>
          <p>
            手动任务、失败恢复与冲突裁定全部写入只追加日志；未确认赛果不会触发结算或复盘。
          </p>
        </div>
        <span className="status-chip warning">2 项待确认</span>
      </header>
      <section className="sync-strategy-grid">
        <article>
          <p className="eyebrow">赛程 / 赔率</p>
          <strong>每 30 分钟</strong>
          <span>临近停售自动加密</span>
        </article>
        <article>
          <p className="eyebrow">赛果</p>
          <strong>赛后轮询</strong>
          <span>多源一致后确认</span>
        </article>
        <article>
          <p className="eyebrow">最近成功</p>
          <strong>20:08</strong>
          <span>赛事身份未变化</span>
        </article>
      </section>
      <section className="data-table-card sync-actions">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">手动触发</p>
            <h2>选择同步范围</h2>
          </div>
          <span className="status-chip">所有操作写入审计</span>
        </div>
        <div className="sync-controls">
          <div className="segmented-control">
            {[
              ["today", "同步今日"],
              ["date", "指定日期"],
              ["match", "指定比赛"],
            ].map(([value, label]) => (
              <button
                type="button"
                className={scope === value ? "active" : ""}
                key={value}
                onClick={() => setScope(value)}
              >
                {label}
              </button>
            ))}
          </div>
          {scope === "date" ? (
            <input type="date" defaultValue="2026-07-20" />
          ) : null}
          {scope === "match" ? <input placeholder="输入 Match ID" /> : null}
          <button
            className="button primary inline"
            type="button"
            disabled={running}
            onClick={run}
          >
            {running ? "同步中…" : "开始同步"}
          </button>
        </div>
      </section>
      <section className="conflict-panel">
        <div>
          <p className="eyebrow">赛果冲突 · 待确认</p>
          <h2>西班牙 vs 阿根廷</h2>
          <p>
            来源 A 尚未返回赛果，来源 B
            标记比赛未开始。结算、排行与复盘保持冻结。
          </p>
        </div>
        <div className="conflict-values">
          <span>
            FIFA <strong>待赛</strong>
          </span>
          <span>
            供应商 B <strong>来源缺失</strong>
          </span>
        </div>
        <button className="button secondary" type="button">
          打开裁定记录
        </button>
      </section>
      <section className="data-table-card">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">只追加审计</p>
            <h2>同步日志</h2>
          </div>
          <span className="status-chip">成功、失败与重试均保留</span>
        </div>
        <div className="data-table sync-table" role="table">
          <div className="data-table-row data-table-head" role="row">
            <span>时间</span>
            <span>范围</span>
            <span>结果</span>
            <span>失败原因 / 操作</span>
          </div>
          {logs.map((log, index) => (
            <div
              className="data-table-row"
              role="row"
              key={`${log[0]}-${index}`}
            >
              <span className="mono-value">{log[0]}</span>
              <strong>{log[1]}</strong>
              <span
                className={
                  log[2] === "成功"
                    ? "positive-copy"
                    : log[2] === "失败" || log[2] === "部分失败"
                      ? "negative-copy"
                      : "muted"
                }
              >
                {log[2]}
              </span>
              <span>
                {log[3]}{" "}
                {log[2] === "失败" ? (
                  <button className="text-button" type="button" onClick={run}>
                    重试
                  </button>
                ) : null}
              </span>
            </div>
          ))}
        </div>
      </section>
    </main>
  );
}
