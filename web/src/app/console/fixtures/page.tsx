"use client";

import { useMemo, useState } from "react";

import { MatchRow } from "@/components/fixtures/match-row";

const match = {
  id: "104",
  competition: "2026 FIFA 世界杯",
  round: "决赛",
  kickoff: "03:00",
  home: "西班牙",
  away: "阿根廷",
  homeFlag: "/assets/teams/flag-spain.png",
  awayFlag: "/assets/teams/flag-argentina.png",
  prediction: "2 : 1 · 半场 1 : 0",
};

export default function FixturesPage() {
  const [day, setDay] = useState("today");
  const [status, setStatus] = useState("all");
  const [query, setQuery] = useState("");
  const showMatch = useMemo(() => day === "today" && (status === "all" || status === "presale") && (!query || `${match.home}${match.away}`.includes(query.trim())), [day, status, query]);

  return (
    <main className="console-main research-page fixtures-page">
      <div className="page-heading research-heading"><div><p className="eyebrow">赛程研究台 · 北京时间</p><h1>世界杯决赛赛前研究。</h1><p>仅展示已核对的赛事身份与固定 AI 原型输出；官方竞彩信息和外部研究源未接入时保持空缺。</p></div><span className="status-chip warning">来源未连接</span></div>
      <div className="date-switcher" aria-label="日期切换">{[["previous", "前一日", "7 月 19 日"], ["today", "比赛日", "7 月 20 日"], ["next", "后一日", "7 月 21 日"]].map(([value, label, date]) => <button className={day === value ? "active" : ""} key={value} onClick={() => setDay(value)} type="button"><strong>{label}</strong><span>{date}</span></button>)}<button type="button" onClick={() => setDay("custom")}>指定日期</button></div>
      <div className="fixture-filters"><div className="segmented-control" aria-label="状态筛选">{[["all", "全部"], ["presale", "赛前"], ["pending", "待确认"], ["settled", "已结束"]].map(([value, label]) => <button className={status === value ? "active" : ""} key={value} onClick={() => setStatus(value)} type="button">{label}</button>)}</div><label><span>赛事</span><select><option>全部赛事</option><option>2026 FIFA 世界杯</option></select></label><label className="fixture-search"><span>球队搜索</span><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="搜索西班牙或阿根廷" /></label></div>
      <section className="fixture-group"><header><strong>2026 FIFA 世界杯</strong><span>决赛 · 赛果待定</span></header>{showMatch ? <MatchRow {...match} /> : <div className="wide-empty-state"><strong>当前筛选下没有可核验赛程</strong><p>切回比赛日与“全部”状态，或清除球队搜索后查看已确认赛事。</p><button className="button secondary" onClick={() => { setDay("today"); setStatus("all"); setQuery(""); }} type="button">重置筛选</button></div>}</section>
    </main>
  );
}
