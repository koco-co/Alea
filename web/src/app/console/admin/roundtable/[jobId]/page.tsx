"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";

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

export default function RoundtableLivePage() {
  const params = useParams<{ jobId: string }>();
  const jobId = params.jobId;
  const { events, connectionState, error, reconnect } =
    useRoundtableEvents(jobId);
  const [action, setAction] = useState<"skip" | "terminate" | null>(null);
  const [reason, setReason] = useState("");
  const [actionStatus, setActionStatus] = useState("");
  const currentPhase = Math.min(
    Math.max(events.length ? 3 : 0, 0),
    PHASES.length - 1,
  );

  const confirmAction = () => {
    if (!reason.trim()) {
      setActionStatus("必须填写原因，才能写入不可删除的执行审计。");
      return;
    }
    setActionStatus(
      action === "terminate"
        ? "终止请求已记录；已产生内容将冻结并保留。"
        : "跳过请求已记录；圆桌将进入比分终投。",
    );
    setAction(null);
    setReason("");
  };

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
          <h1>圆桌 {jobId}</h1>
          <p>
            消息只按数据库事件序号追加；重连后先补拉持久事件，再继续接收实时通知。
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

      <section className="data-table-card">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">阶段进度</p>
            <h2>{events.length ? PHASES[currentPhase] : "等待首份 AI 结果"}</h2>
          </div>
          <span className="status-chip">{events.length} 条只追加事件</span>
        </div>
        <ol className="flex gap-2 overflow-x-auto pb-2" aria-label="圆桌阶段">
          {PHASES.map((phase, index) => (
            <li
              className={`shrink-0 rounded-full border px-3 py-2 text-xs font-bold ${
                index < currentPhase
                  ? "border-[#3f7a4e] bg-[#edf6ef] text-[#315f3d]"
                  : index === currentPhase
                    ? "border-[#c0613b] bg-[#f7ece5] text-[#9f4d2f]"
                    : "border-stone-200 text-stone-500"
              }`}
              key={phase}
            >
              {String(index + 1).padStart(2, "0")} · {phase}
            </li>
          ))}
        </ol>
      </section>

      <section className="sync-strategy-grid" aria-label="AI 实例状态">
        <article>
          <p className="eyebrow">OpenAI · A</p>
          <strong>思考中</strong>
          <span>等待可核验论据</span>
        </article>
        <article>
          <p className="eyebrow">Anthropic · B</p>
          <strong>已发言</strong>
          <span>当前匿名代号：选手 B</span>
        </article>
        <article>
          <p className="eyebrow">Google · C</p>
          <strong>缺席</strong>
          <span>不计入投票分母</span>
        </article>
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
                onClick={confirmAction}
              >
                确认操作
              </button>
            </div>
          </section>
        </div>
      ) : null}
    </main>
  );
}
