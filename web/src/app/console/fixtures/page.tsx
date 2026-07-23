"use client";

import { useEffect, useMemo, useState } from "react";

import { MatchRow } from "@/components/fixtures/match-row";
import {
  addDays,
  beijingDate,
  dateLabel,
  kickoffLabel,
  type MatchPage,
  type MatchSummary,
} from "@/lib/matches";

type StatusFilter = "all" | "presale" | "pending" | "settled";

const statusQuery: Record<StatusFilter, string | undefined> = {
  all: undefined,
  presale: "on_sale",
  pending: "scheduled",
  settled: "settled",
};

export default function FixturesPage() {
  const today = useMemo(() => beijingDate(new Date()), []);
  const [businessDate, setBusinessDate] = useState(today);
  const [status, setStatus] = useState<StatusFilter>("all");
  const [query, setQuery] = useState("");
  const [page, setPage] = useState<MatchPage>({
    matches: [],
    freshness_state: "unavailable",
  });
  const [resolvedRequestKey, setResolvedRequestKey] = useState("");
  const [error, setError] = useState("");
  const requestKey = `${businessDate}:${status}`;
  const loading = resolvedRequestKey !== requestKey;

  useEffect(() => {
    const controller = new AbortController();
    const params = new URLSearchParams({
      business_date: businessDate,
      limit: "50",
    });
    const state = statusQuery[status];
    if (state) params.set("state", state);
    void fetch(`/api/matches?${params.toString()}`, {
      cache: "no-store",
      signal: controller.signal,
    })
      .then(async (response) => {
        const body = (await response.json()) as MatchPage & { error?: string };
        if (!response.ok) throw new Error(body.error ?? "match_list_failed");
        return body;
      })
      .then((body) => {
        setPage(body);
        setError("");
        setResolvedRequestKey(requestKey);
      })
      .catch((reason) => {
        if (reason instanceof DOMException && reason.name === "AbortError")
          return;
        setError(
          reason instanceof Error ? reason.message : "match_list_failed",
        );
        setResolvedRequestKey(requestKey);
      });
    return () => controller.abort();
  }, [businessDate, requestKey, status]);

  const matches = page.matches.filter((match) => {
    const needle = query.trim().toLocaleLowerCase();
    if (!needle) return true;
    return [match.competition, match.home_team, match.away_team]
      .join(" ")
      .toLocaleLowerCase()
      .includes(needle);
  });
  const fixtureMode = page.freshness_state === "fixture";

  return (
    <main className="console-main research-page fixtures-page">
      <div className="page-heading research-heading">
        <div>
          <p className="eyebrow">赛程研究台 · 北京时间</p>
          <h1>真实竞彩 Offer 赛程研究。</h1>
          <p>
            仅展示后台返回的具体销售场次；当前按来源业务日 {businessDate}{" "}
            筛选，开赛时间按北京时间显示。
          </p>
        </div>
        <span className="status-chip warning">
          {loading
            ? "正在读取"
            : fixtureMode
              ? "Fixture / 非生产"
              : "来源已连接"}
        </span>
      </div>
      {fixtureMode ? (
        <aside className="calculator-warning" role="status">
          <strong>Fixture / 非生产数据</strong>
          <p>
            当前记录用于验证数据链路，不代表已获授权的体彩销售
            Offer，也不会产生真实投注。
          </p>
        </aside>
      ) : null}
      <div className="date-switcher" aria-label="日期切换">
        {(
          [
            ["previous", "前一日", addDays(today, -1)],
            ["today", "比赛日", today],
            ["next", "后一日", addDays(today, 1)],
          ] as const
        ).map(([value, label, date]) => (
          <button
            className={businessDate === date ? "active" : ""}
            key={value}
            onClick={() => setBusinessDate(date)}
            type="button"
          >
            <strong>{label}</strong>
            <span>{dateLabel(date)}</span>
          </button>
        ))}
        <button type="button" onClick={() => setBusinessDate(today)}>
          回到今天
        </button>
      </div>
      <div className="fixture-filters">
        <div className="segmented-control" aria-label="状态筛选">
          {(
            [
              ["all", "全部"],
              ["presale", "赛前"],
              ["pending", "待确认"],
              ["settled", "已结束"],
            ] as const
          ).map(([value, label]) => (
            <button
              className={status === value ? "active" : ""}
              key={value}
              onClick={() => setStatus(value)}
              type="button"
            >
              {label}
            </button>
          ))}
        </div>
        <label>
          <span>赛事</span>
          <select>
            <option>全部赛事</option>
            <option>授权赛事 / Fixture</option>
          </select>
        </label>
        <label className="fixture-search">
          <span>球队搜索</span>
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="搜索球队或联赛"
          />
        </label>
      </div>
      <section className="fixture-group">
        <header>
          <strong>具体销售场次</strong>
          <span>{loading ? "读取中" : `${matches.length} 场`}</span>
        </header>
        {error ? (
          <div className="wide-empty-state" role="alert">
            <strong>赛程读取失败</strong>
            <p>{error}</p>
          </div>
        ) : matches.length ? (
          matches.map((match) => (
            <FixtureMatchRow key={match.match_id} match={match} />
          ))
        ) : (
          <div className="wide-empty-state">
            <strong>
              {loading ? "正在读取真实数据" : "当前没有可核验的竞彩场次"}
            </strong>
            <p>未取得授权数据或当前筛选无结果时，不展示固定球队示例。</p>
            <button
              className="button secondary"
              onClick={() => setQuery("")}
              type="button"
            >
              重置筛选
            </button>
          </div>
        )}
      </section>
    </main>
  );
}

function FixtureMatchRow({ match }: { match: MatchSummary }) {
  const fixture = match.fact_state === "fixture";
  return (
    <MatchRow
      id={match.match_id}
      matchNumber={match.sporttery_match_number}
      competition={match.competition}
      round={fixture ? "Fixture" : "Offer"}
      kickoff={kickoffLabel(match.kickoff_at)}
      home={match.home_team}
      away={match.away_team}
      prediction="暂无发布的预测"
      status={fixture ? "赛前 · Fixture / 非生产" : `赛前 · ${match.state}`}
      sourceLabel={fixture ? "人工导入 / 非生产" : "授权来源"}
    />
  );
}
