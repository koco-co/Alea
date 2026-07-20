"use client";

import { DebateTimeline } from "@/components/prediction/debate-timeline";
import { useRoundtableEvents } from "@/lib/realtime";

export function RoundtableEventReplay({ jobId }: { jobId: string }) {
  const { events, connectionState, error, reconnect } =
    useRoundtableEvents(jobId);

  return (
    <div>
      <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
        <span className="status-chip">
          {connectionState === "subscribed"
            ? `实时已连接 · ${events.length} 条事件`
            : connectionState === "error"
              ? "事件读取失败"
              : "正在连接事件流"}
        </span>
        {error ? (
          <button
            className="button secondary"
            type="button"
            onClick={reconnect}
          >
            重试补拉
          </button>
        ) : null}
      </div>
      {error ? (
        <p className="form-message error" role="alert">
          无法读取圆桌事件（{error.message}）。页面未使用本地回放数据。
        </p>
      ) : null}
      <DebateTimeline events={events} title="匿名交锋改变了最终结论" />
    </div>
  );
}
