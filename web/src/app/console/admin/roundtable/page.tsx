"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import type { ProviderConnectionRecord, ProviderRecord } from "../lineup/model";

type Mode = "autonomous" | "specified";

interface MatchRecord {
  match_id: string;
  competition: string;
  home_team: string;
  away_team: string;
  kickoff_at: string;
  sales_cutoff_at?: string | null;
  state: string;
}

interface MatchResponse {
  matches?: MatchRecord[];
  freshness_state?: string;
  error?: string;
}

interface ProviderResponse {
  providers?: ProviderRecord[];
  error?: string;
}

interface RoundtableInstance {
  id: string;
  label: string;
  model: string;
  provider: string;
  connection: ProviderConnectionRecord;
  enabled: boolean;
  qualified: boolean;
  availability: string;
}

function localDate(): string {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
}

function connectionQualified(
  provider: ProviderRecord,
  connection: ProviderConnectionRecord,
  instance: ProviderRecord["connections"][number]["instances"][number],
): boolean {
  const cli =
    connection.execution_mode === "cli" ||
    connection.execution_mode === "codex_cli";
  return Boolean(
    provider.enabled &&
    connection.enabled &&
    connection.test_status === "passed" &&
    connection.health?.status === "passed" &&
    (!cli || connection.health.auth_status === "authenticated") &&
    instance.enabled,
  );
}

export default function RoundtablePage() {
  const router = useRouter();
  const [mode, setMode] = useState<Mode>("autonomous");
  const [businessDate, setBusinessDate] = useState(localDate);
  const [scope, setScope] = useState("all");
  const [instances, setInstances] = useState<RoundtableInstance[]>([]);
  const [selectedInstances, setSelectedInstances] = useState<string[]>([]);
  const [matches, setMatches] = useState<MatchRecord[]>([]);
  const [selectedMatches, setSelectedMatches] = useState<string[]>([]);
  const [rounds, setRounds] = useState("1");
  const [candidateLimit, setCandidateLimit] = useState("8");
  const [scheduled, setScheduled] = useState(false);
  const [scheduleTime, setScheduleTime] = useState("08:00");
  const [status, setStatus] = useState<"loading" | "idle" | "starting">(
    "loading",
  );
  const [error, setError] = useState("");
  const [matchStatus, setMatchStatus] = useState("正在加载真实赛程…");

  useEffect(() => {
    let active = true;
    void fetch("/api/admin/providers", { cache: "no-store" })
      .then(async (response) => {
        const body = (await response.json()) as ProviderResponse;
        if (!response.ok) throw new Error(body.error ?? "provider_list_failed");
        return body.providers ?? [];
      })
      .then((providers) => {
        if (!active) return;
        const next: RoundtableInstance[] = [];
        for (const provider of providers) {
          const connection = provider.connections[0];
          if (!connection) continue;
          for (const instance of connection.instances) {
            const qualified = connectionQualified(
              provider,
              connection,
              instance,
            );
            next.push({
              id: instance.id,
              label: `${provider.display_name} · ${instance.nickname}`,
              model: instance.model_id,
              provider: provider.key,
              connection,
              enabled: instance.enabled,
              qualified,
              availability: qualified ? "可参赛" : "未通过资格检查",
            });
          }
        }
        setInstances(next);
        setSelectedInstances(
          next
            .filter((item) => item.qualified)
            .slice(0, 3)
            .map((item) => item.id),
        );
        setStatus("idle");
      })
      .catch((reason) => {
        if (active) {
          setError(
            `阵容加载失败：${reason instanceof Error ? reason.message : "unknown_error"}`,
          );
          setStatus("idle");
        }
      });
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (mode !== "specified") return;
    let active = true;
    void fetch(
      `/api/admin/matches?business_date=${encodeURIComponent(businessDate)}`,
      { cache: "no-store" },
    )
      .then(async (response) => {
        const body = (await response.json()) as MatchResponse;
        if (!response.ok) throw new Error(body.error ?? "match_list_failed");
        return body;
      })
      .then((body) => {
        if (!active) return;
        setMatches(body.matches ?? []);
        setSelectedMatches([]);
        setMatchStatus(
          `${body.matches?.length ?? 0} 场可选 · 数据状态 ${body.freshness_state ?? "unknown"}`,
        );
      })
      .catch((reason) => {
        if (active)
          setMatchStatus(
            `赛程加载失败：${reason instanceof Error ? reason.message : "unknown_error"}`,
          );
      });
    return () => {
      active = false;
    };
  }, [businessDate, mode]);

  const quorum = useMemo(() => {
    const selected = instances.filter((item) =>
      selectedInstances.includes(item.id),
    );
    return {
      instances: selected.length,
      providers: new Set(selected.map((item) => item.provider)).size,
    };
  }, [instances, selectedInstances]);

  const toggle = (
    id: string,
    values: string[],
    update: (next: string[]) => void,
  ) => {
    update(
      values.includes(id)
        ? values.filter((item) => item !== id)
        : [...values, id],
    );
  };

  async function start() {
    if (mode === "specified" && selectedMatches.length === 0) {
      setError("指定选场模式至少选择一场真实赛程。");
      return;
    }
    if (selectedInstances.length === 0) {
      setError("至少选择一个已启用且通过测试的真实 AI 实例。");
      return;
    }
    setError("");
    setStatus("starting");
    try {
      const response = await fetch("/api/admin/roundtables", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          mode,
          business_date: businessDate,
          competition_scope: scope,
          match_ids: selectedMatches,
          instance_ids: selectedInstances,
          rounds: Number(rounds),
          candidate_limit: Number(candidateLimit),
          scheduled,
          schedule_time: scheduleTime,
        }),
      });
      const body = (await response.json()) as {
        job_id?: string;
        detail?: string;
        error?: string;
      };
      if (!response.ok || !body.job_id)
        throw new Error(body.detail ?? body.error ?? "roundtable_start_failed");
      router.push(`/console/admin/roundtable/${body.job_id}`);
    } catch (reason) {
      setStatus("idle");
      setError(
        `发起失败：${reason instanceof Error ? reason.message : "unknown_error"}`,
      );
    }
  }

  return (
    <main className="admin-main">
      <header className="admin-page-heading">
        <div>
          <p className="eyebrow">系统管理 · 发起推演 · PRD 15.1</p>
          <h1>先冻结范围、阵容与规则，再让圆桌开始。</h1>
          <p>
            提交后由 FastAPI 事务写入任务、参与者、比赛运行、事件和
            Outbox；直播页只读取持久化状态。
          </p>
        </div>
        <span
          className={
            quorum.instances >= 2 && quorum.providers >= 2
              ? "status-chip"
              : "status-chip warning"
          }
        >
          {quorum.instances} 个实例 · {quorum.providers} 个厂商
        </span>
      </header>

      <section className="data-table-card">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">01 · 推演模式</p>
            <h2>选择自主扫描或指定比赛</h2>
          </div>
          <span className="status-chip">配置在提交时冻结</span>
        </div>
        <div className="segmented-control" aria-label="推演模式">
          <button
            className={mode === "autonomous" ? "active" : ""}
            type="button"
            onClick={() => setMode("autonomous")}
          >
            自主推演
          </button>
          <button
            className={mode === "specified" ? "active" : ""}
            type="button"
            onClick={() => setMode("specified")}
          >
            指定选场
          </button>
        </div>
        <div className="admin-form-section">
          <div className="admin-form-grid three">
            <label>
              <span>业务日期</span>
              <input
                type="date"
                value={businessDate}
                onChange={(event) => setBusinessDate(event.target.value)}
              />
            </label>
            <label>
              <span>赛事范围</span>
              <select
                value={scope}
                onChange={(event) => setScope(event.target.value)}
              >
                <option value="all">当日全部在售场次</option>
                <option value="fifa">仅 FIFA 赛事</option>
              </select>
            </label>
            <label>
              <span>排除比赛</span>
              <select defaultValue="none">
                <option value="none">不排除</option>
                <option value="missing">排除关键数据暂缺场次</option>
              </select>
            </label>
          </div>
          {mode === "specified" ? (
            <div className="switch-stack" aria-label="真实赛程多选">
              <p className="eyebrow">{matchStatus}</p>
              {matches.length ? (
                matches.map((match) => (
                  <label className="switch-row" key={match.match_id}>
                    <input
                      type="checkbox"
                      checked={selectedMatches.includes(match.match_id)}
                      onChange={() =>
                        toggle(
                          match.match_id,
                          selectedMatches,
                          setSelectedMatches,
                        )
                      }
                    />
                    <span>
                      <strong>
                        {match.home_team} vs {match.away_team}
                      </strong>
                      <small>
                        {match.competition} ·{" "}
                        {new Date(match.kickoff_at).toLocaleString("zh-CN")}
                      </small>
                    </span>
                  </label>
                ))
              ) : (
                <div className="wide-empty-state">
                  <strong>该日期暂无可选真实赛程</strong>
                  <p>请切换业务日期，或使用自主推演。</p>
                </div>
              )}
            </div>
          ) : null}
        </div>
      </section>

      <section className="data-table-card">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">02 · 选择阵容</p>
            <h2>仅启用且通过连接测试的实例可参赛</h2>
          </div>
          <Link className="button secondary" href="/console/admin/lineup">
            管理模型阵容
          </Link>
        </div>
        <div className="switch-stack">
          {status === "loading" ? (
            <p className="eyebrow">正在读取数据库阵容…</p>
          ) : instances.length ? (
            instances.map((item) => (
              <label className="switch-row" key={item.id}>
                <input
                  type="checkbox"
                  disabled={!item.qualified}
                  checked={selectedInstances.includes(item.id)}
                  onChange={() =>
                    toggle(item.id, selectedInstances, setSelectedInstances)
                  }
                />
                <span>
                  <strong>{item.label}</strong>
                  <small>
                    {item.model} · {item.availability}
                  </small>
                </span>
              </label>
            ))
          ) : (
            <div className="wide-empty-state">
              <strong>数据库中没有可用实例</strong>
              <p>先在模型阵容中完成 API/CLI 连接测试并启用实例。</p>
            </div>
          )}
        </div>
        {quorum.instances < 2 || quorum.providers < 2 ? (
          <div className="inline-callout danger" role="status">
            <strong>当前阵容未达到跨厂商法定人数</strong>
            <p>任务可以落库，但不会进入可公证、可发布状态。</p>
          </div>
        ) : null}
      </section>

      <section className="data-table-card">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">03 · 参数与定时</p>
            <h2>辩论轮数、入围上限与每日计划</h2>
          </div>
          <Link
            className="button secondary"
            href="/console/admin/settings#settings-automation"
          >
            打开版本化设置
          </Link>
        </div>
        <div className="admin-form-grid three">
          <label>
            <span>辩论轮数</span>
            <select
              value={rounds}
              onChange={(event) => setRounds(event.target.value)}
            >
              <option value="1">1 轮（默认）</option>
              <option value="2">2 轮</option>
            </select>
          </label>
          {mode === "autonomous" ? (
            <label>
              <span>入围上限</span>
              <input
                min="1"
                max="20"
                type="number"
                value={candidateLimit}
                onChange={(event) => setCandidateLimit(event.target.value)}
              />
            </label>
          ) : null}
          <label>
            <span>每日自动发起时间</span>
            <input
              type="time"
              value={scheduleTime}
              onChange={(event) => setScheduleTime(event.target.value)}
            />
          </label>
        </div>
        <label className="switch-row">
          <input
            type="checkbox"
            checked={scheduled}
            onChange={(event) => setScheduled(event.target.checked)}
          />
          <span>
            <strong>启用每日定时圆桌</strong>
            <small>
              仅保存本次任务快照中的调度意图，不会覆盖版本化系统设置。
            </small>
          </span>
        </label>
      </section>

      {error ? (
        <p className="form-message error" role="alert">
          {error}
        </p>
      ) : null}
      <button
        className="button primary inline"
        type="button"
        disabled={status === "loading" || status === "starting"}
        onClick={() => void start()}
      >
        {status === "starting" ? "正在创建圆桌…" : "发起圆桌"}
      </button>
    </main>
  );
}
