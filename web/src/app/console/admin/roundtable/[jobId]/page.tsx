"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { DebateTimeline } from "@/components/prediction/debate-timeline";
import { useRoundtableEvents } from "@/lib/realtime";

const PHASES = [
  "选场提名",
  "匿名互阅",
  "选场终投",
  "独立预测",
  "匿名辩论",
  "比分终投",
  "组单提案",
  "组单辩论",
  "方案终投",
] as const;

interface Participant {
  id: string;
  ai_instance_id: string;
  provider_family: string;
  codename: string;
  nickname?: string;
  model_id?: string;
  provider_name?: string;
  enabled?: boolean;
  connection_test_status?: string;
  health_status?: string;
  auth_status?: string;
}

interface JobResponse {
  job?: {
    id: string;
    state: string;
    state_version: number;
    config_snapshot?: Record<string, unknown>;
  } | null;
  participants?: Participant[];
  match_runs?: Array<{ id: string; match_id: string; state: string }>;
}

export default function RoundtableLivePage() {
  const params = useParams<{ jobId: string }>();
  const jobId = params.jobId;
  const { events, connectionState, error, reconnect } =
    useRoundtableEvents(jobId);
  const [job, setJob] = useState<JobResponse>({});
  const [loadError, setLoadError] = useState("");
  const [action, setAction] = useState<"skip" | "terminate" | null>(null);
  const [reason, setReason] = useState("");
  const [actionStatus, setActionStatus] = useState("");
  const [actionRunning, setActionRunning] = useState(false);

  useEffect(() => {
    let active = true;
    void fetch(`/api/admin/roundtables/${encodeURIComponent(jobId)}`, {
      cache: "no-store",
    })
      .then(async (response) => {
        const body = (await response.json()) as JobResponse & {
          detail?: string;
        };
        if (!response.ok)
          throw new Error(body.detail ?? "roundtable_read_failed");
        return body;
      })
      .then((body) => {
        if (active) setJob(body);
      })
      .catch((reason) => {
        if (active)
          setLoadError(
            reason instanceof Error ? reason.message : "roundtable_read_failed",
          );
      });
    return () => {
      active = false;
    };
  }, [jobId]);

  const participants = job.participants ?? [];
  const currentPhase = useMemo(() => {
    const latest = events.at(-1)?.payload?.phase;
    const index =
      latest === "select_nomination"
        ? 0
        : latest === "select_debate"
          ? 1
          : latest === "select_vote"
            ? 2
            : events.length
              ? 3
              : 0;
    return Math.min(index, PHASES.length - 1);
  }, [events]);

  async function confirmAction() {
    if (!reason.trim()) {
      setActionStatus("必须填写原因，才能写入不可删除的执行审计。");
      return;
    }
    if (!action) return;
    setActionRunning(true);
    try {
      const response = await fetch(
        `/api/admin/roundtables/${encodeURIComponent(jobId)}/${action === "terminate" ? "terminate" : "skip-debate"}`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            confirmed: true,
            reason,
            expected_state_version: job.job?.state_version ?? 0,
          }),
        },
      );
      const body = (await response.json()) as {
        detail?: string;
        error?: string;
      };
      if (!response.ok)
        throw new Error(
          body.detail ?? body.error ?? "roundtable_control_failed",
        );
      setActionStatus(
        action === "terminate"
          ? "终止请求已写入数据库；已产生内容将冻结并保留。"
          : "跳过请求已写入数据库；圆桌将进入后续阶段。",
      );
      setAction(null);
      setReason("");
      const refreshed = await fetch(
        `/api/admin/roundtables/${encodeURIComponent(jobId)}`,
        { cache: "no-store" },
      );
      if (refreshed.ok) setJob((await refreshed.json()) as JobResponse);
    } catch (reasonValue) {
      setActionStatus(
        `操作失败：${reasonValue instanceof Error ? reasonValue.message : "unknown_error"}`,
      );
    } finally {
      setActionRunning(false);
    }
  }

  return (
    <main className="admin-main">
      <Link
        className="button secondary back-link"
        href="/console/admin/roundtable"
      >
        返回发起推演
      </Link>
      <header className="admin-page-heading">
        <div>
          <p className="eyebrow">系统管理 · 推演直播 · PRD 15.2</p>
          <h1>圆桌 {job.job?.id ?? jobId}</h1>
          <p>
            任务、参与者和事件均来自数据库；重连后先补拉持久事件，再继续接收实时通知。
          </p>
        </div>
        <span
          className={
            connectionState === "error" ? "status-chip warning" : "status-chip"
          }
        >
          {connectionState === "subscribed"
            ? "直播已连接"
            : connectionState === "error"
              ? "连接失败"
              : "正在连接"}
        </span>
      </header>

      {loadError ? (
        <div className="inline-callout danger" role="alert">
          <strong>任务读取失败</strong>
          <p>{loadError}</p>
        </div>
      ) : null}
      <section className="data-table-card">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">阶段进度</p>
            <h2>
              {events.length
                ? PHASES[currentPhase]
                : "等待 Worker 首个持久事件"}
            </h2>
          </div>
          <span className="status-chip">
            {events.length} 条持久化事件 · 状态 {job.job?.state ?? "读取中"}
          </span>
        </div>
        <ol className="flex gap-2 overflow-x-auto pb-2" aria-label="圆桌阶段">
          {PHASES.map((phase, index) => (
            <li
              className={`shrink-0 rounded-full border px-3 py-2 text-xs font-bold ${index < currentPhase ? "border-[#3f7a4e] bg-[#edf6ef] text-[#315f3d]" : index === currentPhase ? "border-[#c0613b] bg-[#f7ece5] text-[#9f4d2f]" : "border-stone-200 text-stone-500"}`}
              key={phase}
            >
              {String(index + 1).padStart(2, "0")} · {phase}
            </li>
          ))}
        </ol>
      </section>

      <section
        className="sync-strategy-grid"
        aria-label="数据库中的 AI 实例状态"
      >
        {participants.length ? (
          participants.map((participant) => (
            <article key={participant.id}>
              <p className="eyebrow">
                {participant.provider_name ?? participant.provider_family} ·{" "}
                {participant.codename}
              </p>
              <strong>
                {participant.health_status === "passed" ? "已就绪" : "待处理"}
              </strong>
              <span>
                {participant.nickname ?? participant.ai_instance_id} ·{" "}
                {participant.model_id ?? "模型随快照冻结"}
              </span>
            </article>
          ))
        ) : (
          <article>
            <p className="eyebrow">参与者</p>
            <strong>读取中</strong>
            <span>尚未取得数据库投影</span>
          </article>
        )}
      </section>

      {error ? (
        <div className="inline-callout danger" role="alert">
          <strong>事件补拉失败</strong>
          <p>{error.message}。页面不会用静态事件冒充直播数据。</p>
          <button
            className="button secondary"
            type="button"
            onClick={reconnect}
          >
            重新连接
          </button>
        </div>
      ) : null}
      <DebateTimeline events={events} title="圆桌实时事件" live />

      <section className="data-table-card">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">熔断控制</p>
            <h2>所有人工干预都必须保留原因</h2>
          </div>
          <span className="status-chip warning">高风险操作</span>
        </div>
        <div className="flex flex-wrap gap-3">
          <button
            className="button secondary"
            type="button"
            onClick={() => setAction("skip")}
          >
            跳过辩论直接终投
          </button>
          <button
            className="button secondary"
            type="button"
            onClick={() => setAction("terminate")}
          >
            终止本场圆桌
          </button>
          <Link className="button primary inline" href="/console/admin/publish">
            完成后进入发布审核
          </Link>
        </div>
        {actionStatus ? (
          <p className="form-message" role="status">
            {actionStatus}
          </p>
        ) : null}
      </section>

      {action ? (
        <div className="confirm-overlay" role="presentation">
          <section
            role="dialog"
            aria-modal="true"
            aria-labelledby="roundtable-control-title"
          >
            <p className="eyebrow">二次确认</p>
            <h2 id="roundtable-control-title">
              {action === "terminate" ? "终止本场圆桌？" : "跳过辩论直接终投？"}
            </h2>
            <p>
              {action === "terminate"
                ? "已产生内容会冻结并进入公开审计；不会生成预测卡。"
                : "未完成的辩论轮次将标记为跳过，随后进入终投。"}
            </p>
            <label>
              <span>操作原因</span>
              <textarea
                value={reason}
                onChange={(event) => setReason(event.target.value)}
                placeholder="填写原因以写入执行审计"
              />
            </label>
            <div>
              <button
                className="button secondary"
                type="button"
                onClick={() => setAction(null)}
              >
                取消
              </button>
              <button
                className="button primary inline"
                type="button"
                disabled={actionRunning}
                onClick={() => void confirmAction()}
              >
                {actionRunning ? "正在写入…" : "确认操作"}
              </button>
            </div>
          </section>
        </div>
      ) : null}
    </main>
  );
}
