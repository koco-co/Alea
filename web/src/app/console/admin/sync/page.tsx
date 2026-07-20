"use client";

import { useCallback, useEffect, useState } from "react";

interface SyncRun {
  id: string;
  source_name: string;
  status: string;
  scope: Record<string, unknown>;
  parser_version: string;
  records_seen: number;
  records_accepted: number;
  records_conflicted: number;
  attempt: number;
  last_error_code?: string | null;
  completed_at?: string | null;
  created_at: string;
}

interface Conflict {
  id: string;
  match_id?: string | null;
  field_path: string;
  candidate_source_record_ids: string[];
  created_at: string;
}

function responseError(body: unknown, fallback: string): string {
  if (body && typeof body === "object") {
    const detail = (body as { detail?: unknown }).detail;
    if (typeof detail === "string") return detail;
    const error = (body as { error?: unknown }).error;
    if (typeof error === "string") return error;
  }
  return fallback;
}

function statusLabel(status: string): string {
  return (
    {
      succeeded: "成功",
      failed: "失败",
      pending: "等待",
      running: "运行中",
      paused: "已暂停",
      cancelled: "已取消",
    }[status] ?? status
  );
}

export default function SyncPage() {
  const [scope, setScope] = useState("today");
  const [businessDate, setBusinessDate] = useState("");
  const [matchId, setMatchId] = useState("");
  const [running, setRunning] = useState(false);
  const [runs, setRuns] = useState<SyncRun[]>([]);
  const [conflicts, setConflicts] = useState<Conflict[]>([]);
  const [status, setStatus] = useState("正在读取持久化同步状态…");
  const [importing, setImporting] = useState(false);

  const load = useCallback(async () => {
    try {
      const [runsResponse, conflictsResponse] = await Promise.all([
        fetch("/api/admin/sync", { cache: "no-store" }),
        fetch("/api/admin/results/conflicts", { cache: "no-store" }),
      ]);
      const runsBody = (await runsResponse.json()) as {
        runs?: SyncRun[];
        error?: string;
      };
      const conflictsBody = (await conflictsResponse.json()) as {
        conflicts?: Conflict[];
        error?: string;
      };
      if (!runsResponse.ok) {
        throw new Error(responseError(runsBody, "sync_runs_unavailable"));
      }
      setRuns(runsBody.runs ?? []);
      setConflicts(conflictsResponse.ok ? (conflictsBody.conflicts ?? []) : []);
      setStatus("已连接真实数据库；Sporttery Web Source 未授权时保持禁用");
    } catch (error) {
      setStatus(
        `读取失败 · ${error instanceof Error ? error.message : "unknown_error"}`,
      );
    }
  }, []);

  useEffect(() => {
    // Initial admin state is an external synchronization.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load();
  }, [load]);

  async function triggerSync() {
    setRunning(true);
    setStatus("正在提交同步命令…");
    try {
      const response = await fetch("/api/admin/sync", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          scope,
          business_date: scope === "date" ? businessDate : undefined,
          match_id: scope === "match" ? matchId : undefined,
        }),
      });
      const body = (await response.json()) as {
        status?: string;
        error_code?: string;
      };
      if (!response.ok) {
        throw new Error(responseError(body, "sync_trigger_failed"));
      }
      setStatus(
        body.status === "unavailable"
          ? `同步不可用 · ${body.error_code ?? "no_authorized_data_source"}`
          : `同步命令已提交 · ${body.status ?? "pending"}`,
      );
      await load();
    } catch (error) {
      setStatus(
        `同步失败 · ${error instanceof Error ? error.message : "unknown_error"}`,
      );
    } finally {
      setRunning(false);
    }
  }

  async function importFixture(file: File | undefined) {
    if (!file) return;
    setImporting(true);
    setStatus("正在校验并导入 Gate 0 fixture…");
    try {
      const content = await file.text();
      const contentFormat = file.name.toLowerCase().endsWith(".csv")
        ? "csv"
        : "json";
      const response = await fetch("/api/admin/sync/import", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          content_format: contentFormat,
          content,
          dry_run: false,
        }),
      });
      const body = (await response.json()) as {
        status?: string;
        records_accepted?: number;
        records_conflicted?: number;
      };
      if (!response.ok || body.status !== "succeeded") {
        throw new Error(responseError(body, "fixture_import_failed"));
      }
      setStatus(
        `Fixture 已持久化 · 接受 ${body.records_accepted ?? 0} · 冲突 ${body.records_conflicted ?? 0}`,
      );
      await load();
    } catch (error) {
      setStatus(
        `导入失败 · ${error instanceof Error ? error.message : "unknown_error"}`,
      );
    } finally {
      setImporting(false);
    }
  }

  async function retryRun(runId: string) {
    setStatus("正在重试失败批次…");
    const response = await fetch(`/api/admin/sync/runs/${runId}/retry`, {
      method: "POST",
    });
    const body = (await response.json()) as unknown;
    setStatus(
      response.ok
        ? "重试已进入等待状态"
        : `重试失败 · ${responseError(body, "sync_retry_failed")}`,
    );
    await load();
  }

  return (
    <main className="admin-main">
      <header className="admin-page-heading">
        <div>
          <p className="eyebrow">系统管理 · 数据管理 · PRD 15.5</p>
          <h1>只让获准来源进入事实链。</h1>
          <p>
            Gate 0 只接受明确标注的人工 fixture。Sporttery Web Source
            在许可确认前不自动访问、不回填历史。
          </p>
        </div>
        <span className="status-chip warning">
          {conflicts.length} 项待人工确认
        </span>
      </header>

      <section className="sync-strategy-grid">
        <article>
          <p className="eyebrow">Sporttery Web</p>
          <strong>默认禁用</strong>
          <span>等待自动访问与存储许可</span>
        </article>
        <article>
          <p className="eyebrow">Gate 0 Fixture</p>
          <strong>人工导入</strong>
          <span>JSON / CSV · 哈希与解析器版本</span>
        </article>
        <article>
          <p className="eyebrow">持久化批次</p>
          <strong>{runs.length}</strong>
          <span>幂等记录可迁移、可备份</span>
        </article>
      </section>

      <section className="data-table-card sync-actions">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">手动触发</p>
            <h2>按许可降级链同步</h2>
          </div>
          <span className="status-chip">无可用来源时返回 unavailable</span>
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
            <input
              aria-label="业务日期"
              type="date"
              value={businessDate}
              onChange={(event) => setBusinessDate(event.target.value)}
            />
          ) : null}
          {scope === "match" ? (
            <input
              aria-label="Match ID"
              placeholder="输入 Match UUID"
              value={matchId}
              onChange={(event) => setMatchId(event.target.value)}
            />
          ) : null}
          <button
            className="button primary inline"
            type="button"
            disabled={
              running ||
              (scope === "date" && !businessDate) ||
              (scope === "match" && !matchId)
            }
            onClick={() => void triggerSync()}
          >
            {running ? "提交中…" : "开始同步"}
          </button>
        </div>
        <div className="inline-callout" role="status">
          {status}
        </div>
      </section>

      <section className="data-table-card">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">Gate 0 人工 Fixture</p>
            <h2>导入合法 JSON / CSV</h2>
          </div>
          <label className="button secondary inline">
            {importing ? "导入中…" : "选择文件"}
            <input
              accept=".json,.csv,application/json,text/csv"
              disabled={importing}
              hidden
              type="file"
              onChange={(event) => void importFixture(event.target.files?.[0])}
            />
          </label>
        </div>
        <p className="muted">
          文件必须声明
          fixture、竞彩足球销售范围、来源说明和解析器版本；通用足球数据会被拒绝。
        </p>
      </section>

      {conflicts.length > 0 ? (
        <section className="conflict-panel">
          <div>
            <p className="eyebrow">字段冲突 · 待确认</p>
            <h2>{conflicts[0].field_path}</h2>
            <p>
              {conflicts[0].candidate_source_record_ids.length} 个来源候选。
              人工裁定前结算、排行与复盘保持冻结。
            </p>
          </div>
          <span className="status-chip warning">
            Match {conflicts[0].match_id ?? "待映射"}
          </span>
        </section>
      ) : (
        <section className="conflict-panel">
          <div>
            <p className="eyebrow">字段冲突</p>
            <h2>当前没有待裁定记录</h2>
            <p>系统不会用演示冲突冒充真实来源冲突。</p>
          </div>
        </section>
      )}

      <section className="data-table-card">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">持久化批次</p>
            <h2>同步日志</h2>
          </div>
          <span className="status-chip">成功、失败与重试均保留</span>
        </div>
        <div className="data-table sync-table" role="table">
          <div className="data-table-row data-table-head" role="row">
            <span>时间</span>
            <span>来源 / 解析器</span>
            <span>结果</span>
            <span>记录 / 操作</span>
          </div>
          {runs.length > 0 ? (
            runs.map((run) => (
              <div className="data-table-row" role="row" key={run.id}>
                <span className="mono-value">
                  {new Date(run.created_at).toLocaleString("zh-CN")}
                </span>
                <strong>
                  {run.source_name} · {run.parser_version}
                </strong>
                <span
                  className={
                    run.status === "succeeded"
                      ? "positive-copy"
                      : run.status === "failed"
                        ? "negative-copy"
                        : "muted"
                  }
                >
                  {statusLabel(run.status)}
                </span>
                <span>
                  {run.records_accepted}/{run.records_seen}
                  {run.records_conflicted
                    ? ` · 冲突 ${run.records_conflicted}`
                    : ""}
                  {run.status === "failed" ? (
                    <button
                      className="text-button"
                      type="button"
                      onClick={() => void retryRun(run.id)}
                    >
                      重试
                    </button>
                  ) : null}
                </span>
              </div>
            ))
          ) : (
            <div className="data-table-empty">
              尚无持久化批次。可导入仓库中的 Gate 0 fixture。
            </div>
          )}
        </div>
      </section>
    </main>
  );
}
