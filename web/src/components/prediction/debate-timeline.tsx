"use client";

import { useId } from "react";

import type { RoundtableEvent } from "@/lib/realtime";

import { summarizeTimeline } from "./timeline-summary";

const PHASES = [
  ["selection", "选场"],
  ["prediction", "独立预测"],
  ["debate", "匿名辩论"],
  ["score_vote", "比分终投"],
  ["bet_proposal", "组单提案"],
  ["bet_debate", "组单辩论"],
  ["bet_vote", "方案终投"],
  ["notarization", "公证"],
] as const;

export interface DebateTimelineProps {
  events: RoundtableEvent[];
  title?: string;
  live?: boolean;
  className?: string;
}

export function DebateTimeline({
  events,
  title = "匿名圆桌时间线",
  live = false,
  className = "",
}: DebateTimelineProps) {
  const instanceId = useId().replaceAll(":", "");
  const titleId = `${instanceId}-debate-timeline-title`;
  const ordered = [...events].sort(
    (left, right) => left.event_seq - right.event_seq,
  );
  const phases = PHASES.filter(([phase]) =>
    ordered.some((event) => eventPhase(event) === phase),
  );
  const voteChanges = ordered.filter(isVoteChange);
  const firstConsensus = readPercent(
    ordered.find(hasConsensus)?.payload.consensus,
  );
  const finalConsensus = readPercent(
    ordered.findLast(hasConsensus)?.payload.consensus,
  );
  const notarized = ordered.some((event) => {
    const type = event.event_type.toLowerCase();
    return type.includes("notar") || event.payload.status === "notarized";
  });
  const timelineSummary = summarizeTimeline({
    firstConsensus,
    finalConsensus,
    voteChanges: voteChanges.length,
    notarized,
  });

  return (
    <section
      aria-live={live ? "polite" : undefined}
      aria-labelledby={titleId}
      className={`overflow-hidden rounded-3xl border border-stone-200 bg-[#fffdf8] shadow-[0_18px_60px_rgb(69_56_43/8%)] ${className}`}
    >
      <header className="flex flex-col gap-5 bg-[#2a2622] px-5 py-6 text-[#fffdf8] sm:flex-row sm:items-start sm:justify-between sm:px-7">
        <div>
          <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-[0.14em] text-[#d7cfc4]">
            {live ? (
              <span
                className="h-2 w-2 animate-pulse rounded-full bg-[#c0613b]"
                aria-hidden
              />
            ) : null}
            {live ? "推演直播" : "圆桌回放"}
          </div>
          <h2
            id={titleId}
            className="mt-2 font-serif text-2xl font-medium sm:text-3xl"
          >
            {title}
          </h2>
        </div>
        <div className="rounded-2xl border border-white/15 bg-white/5 px-4 py-3 text-right">
          <strong className="font-mono text-xl">
            {timelineSummary.headline}
          </strong>
          <small className="mt-1 block text-[#d7cfc4]">
            {timelineSummary.detail}
          </small>
        </div>
      </header>

      {phases.length ? (
        <nav
          aria-label="圆桌阶段锚点"
          className="border-b border-stone-200 px-5 py-3 sm:px-7"
        >
          <ol className="flex gap-2 overflow-x-auto pb-1">
            {phases.map(([phase, label], index) => (
              <li key={phase} className="shrink-0">
                <a
                  className="inline-flex min-h-10 items-center rounded-full border border-stone-200 px-3 text-xs font-bold text-stone-600 transition hover:border-[#c0613b] hover:text-[#9f4d2f]"
                  href={`#${instanceId}-debate-phase-${phase}`}
                >
                  {String(index + 1).padStart(2, "0")} · {label}
                </a>
              </li>
            ))}
          </ol>
        </nav>
      ) : null}

      <div className="px-5 py-3 sm:px-7">
        {ordered.length ? (
          <ol className="relative before:absolute before:bottom-6 before:left-[5px] before:top-6 before:w-px before:bg-stone-200">
            {ordered.map((event, index) => {
              const phase = eventPhase(event);
              const previousPhase = index
                ? eventPhase(ordered[index - 1])
                : null;
              const phaseStart = phase !== previousPhase;
              return (
                <li
                  className={`relative border-b border-stone-200 py-5 pl-7 last:border-0 ${
                    isVoteChange(event) ? "rounded-2xl bg-[#f7ece5] pr-4" : ""
                  }`}
                  id={
                    phaseStart && phase
                      ? `${instanceId}-debate-phase-${phase}`
                      : undefined
                  }
                  key={`${event.job_id}-${event.event_seq}`}
                >
                  <span
                    aria-hidden
                    className={`absolute left-0 top-[1.8rem] h-[11px] w-[11px] rounded-full border-2 border-[#fffdf8] ring-1 ring-stone-200 ${
                      isVoteChange(event)
                        ? "bg-[#c0613b]"
                        : event.event_type.includes("verified")
                          ? "bg-[#3f7a4e]"
                          : "bg-stone-400"
                    }`}
                  />
                  <article>
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <h3 className="text-sm font-bold text-stone-900">
                        {eventTitle(event)}
                      </h3>
                      <time
                        className="font-mono text-[11px] text-stone-500"
                        dateTime={event.created_at}
                      >
                        {formatTime(event.created_at)} · #{event.event_seq}
                      </time>
                    </div>
                    <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-stone-600">
                      {eventMessage(event)}
                    </p>
                    {isVoteChange(event) ? <VoteChange event={event} /> : null}
                    <SourceBadge event={event} />
                  </article>
                </li>
              );
            })}
          </ol>
        ) : (
          <div className="py-16 text-center" role="status">
            <p className="font-serif text-xl text-stone-800">
              等待首个圆桌事件
            </p>
            <p className="mt-2 text-sm text-stone-500">
              订阅建立后会先补拉持久事件，再按序追加直播。
            </p>
          </div>
        )}
      </div>
    </section>
  );
}

function VoteChange({ event }: { event: RoundtableEvent }) {
  const previous = displayValue(event.payload.previous_vote) ?? "原判断";
  const next = displayValue(event.payload.new_vote) ?? "新判断";
  return (
    <div className="mt-3 flex flex-wrap items-center gap-2 font-mono text-sm font-bold text-[#9f4d2f]">
      <s className="text-stone-500">{previous}</s>
      <span aria-hidden>→</span>
      <span>{next}</span>
    </div>
  );
}

function SourceBadge({ event }: { event: RoundtableEvent }) {
  const tooltipId = `${useId().replaceAll(":", "")}-sources`;
  const sources = sourceLabels(event);
  const verified =
    event.event_type.includes("verified") ||
    event.payload.claim_status === "verified";
  if (!sources.length) {
    return event.event_type.includes("claim") ? (
      <span className="mt-3 inline-flex rounded-full bg-amber-50 px-2.5 py-1 text-[11px] font-bold text-amber-800">
        未经证实 · 未广播
      </span>
    ) : null;
  }
  return (
    <div className="group relative mt-3 inline-block">
      <button
        aria-describedby={tooltipId}
        className="rounded-full border border-stone-200 bg-white px-2.5 py-1 text-[11px] font-bold text-stone-600 hover:border-[#c0613b]"
        type="button"
      >
        {verified ? "来源已核验" : "查看来源"} · {sources.length}
      </button>
      <div
        className="z-10 mt-2 hidden w-[min(320px,75vw)] rounded-xl border border-stone-200 bg-[#f4f1ea] p-3 text-xs leading-5 text-stone-700 shadow-lg group-focus-within:block group-hover:block sm:absolute sm:left-0"
        id={tooltipId}
        role="tooltip"
      >
        <strong className="block text-stone-900">证据来源</strong>
        <ul className="mt-1 list-disc pl-4">
          {sources.map((source) => (
            <li key={source}>{source}</li>
          ))}
        </ul>
      </div>
    </div>
  );
}

function eventPhase(event: RoundtableEvent): string | null {
  const phase = readString(event.payload.phase);
  if (phase) return normalizePhase(phase);
  const type = event.event_type.toLowerCase();
  if (type.includes("select")) return "selection";
  if (type.includes("score_vote")) return "score_vote";
  if (type.includes("predict")) return "prediction";
  if (type.includes("bet_propos")) return "bet_proposal";
  if (type.includes("bet_debat")) return "bet_debate";
  if (type.includes("bet_vot")) return "bet_vote";
  if (type.includes("notar")) return "notarization";
  if (
    type.includes("debat") ||
    type.includes("claim") ||
    type.includes("vote_changed")
  )
    return "debate";
  return null;
}

function normalizePhase(value: string): string {
  const phase = value.toLowerCase();
  if (phase.startsWith("select")) return "selection";
  if (phase.includes("score") && phase.includes("vot")) return "score_vote";
  if (phase.includes("predict")) return "prediction";
  if (phase.includes("bet") && phase.includes("propos")) return "bet_proposal";
  if (phase.includes("bet") && phase.includes("debat")) return "bet_debate";
  if (phase.includes("bet") && phase.includes("vot")) return "bet_vote";
  if (phase.includes("notar")) return "notarization";
  if (phase.includes("debat")) return "debate";
  return phase;
}

function eventTitle(event: RoundtableEvent): string {
  const speaker = readString(event.payload.speaker_codename);
  const type = event.event_type.toLowerCase();
  if (isVoteChange(event)) return `${speaker ?? "匿名选手"} · 公开改票`;
  if (type.includes("claim_verified")) return "事实核验通过";
  if (type.includes("claim_rejected")) return "事实核验未通过";
  if (type.includes("notar")) return "公证账本已冻结";
  if (speaker) return `${speaker} · ${phaseLabel(eventPhase(event))}`;
  return phaseLabel(eventPhase(event)) || event.event_type;
}

function eventMessage(event: RoundtableEvent): string {
  return (
    readString(event.payload.message) ??
    readString(event.payload.reason) ??
    readString(event.payload.status) ??
    "事件已写入不可变审计记录。"
  );
}

function phaseLabel(phase: string | null): string {
  return PHASES.find(([key]) => key === phase)?.[1] ?? "圆桌事件";
}

function isVoteChange(event: RoundtableEvent): boolean {
  return (
    event.event_type.toLowerCase().includes("vote_changed") ||
    event.payload.stance === "change"
  );
}

function hasConsensus(event: RoundtableEvent): boolean {
  return readPercent(event.payload.consensus) !== null;
}

function sourceLabels(event: RoundtableEvent): string[] {
  const raw = event.payload.sources ?? event.payload.source_record_ids;
  if (!Array.isArray(raw)) return [];
  return raw
    .map(displayValue)
    .filter((value): value is string => Boolean(value));
}

function displayValue(value: unknown): string | null {
  if (typeof value === "string" || typeof value === "number")
    return String(value);
  if (typeof value === "object" && value !== null) {
    const record = value as Record<string, unknown>;
    return (
      readString(record.label) ??
      readString(record.name) ??
      readString(record.id)
    );
  }
  return null;
}

function readString(value: unknown): string | null {
  return typeof value === "string" && value.trim() ? value : null;
}

function readPercent(value: unknown): number | null {
  if (typeof value !== "number" || !Number.isFinite(value)) return null;
  const percent = value <= 1 ? value * 100 : value;
  return Math.round(percent);
}

function formatTime(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.valueOf())
    ? value
    : new Intl.DateTimeFormat("zh-CN", {
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
      }).format(date);
}
