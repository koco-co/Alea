"use client";

import Link from "next/link";
import { useMemo, useState } from "react";

const tabs = [
  { id: "teams", label: "球队", count: 2 },
  { id: "players", label: "球员", count: 0 },
  { id: "coaches", label: "教练", count: 0 },
  { id: "referees", label: "裁判", count: 0 },
] as const;

const teams = [
  { id: "spain", name: "西班牙", subtitle: "国家队 · UEFA", flag: "/assets/teams/flag-spain.png", rank: "FIFA 排名 2", form: ["w", "w", "d", "w", "w"] },
  { id: "argentina", name: "阿根廷", subtitle: "国家队 · CONMEBOL", flag: "/assets/teams/flag-argentina.png", rank: "FIFA 排名 1", form: ["w", "d", "w", "w", "w"] },
] as const;

export default function WikiPage() {
  const [tab, setTab] = useState<(typeof tabs)[number]["id"]>("teams");
  const [query, setQuery] = useState("");
  const visible = useMemo(() => teams.filter((team) => team.name.includes(query.trim())), [query]);
  return (
    <main className="console-main research-page wiki-page">
      <div className="page-heading research-heading"><div><p className="eyebrow">赛事资料 · 资料档案</p><h1>事实资料与 AI 判断，始终分开。</h1><p>球队身份来自已核对的赛事资料；球员、教练与裁判源未接入前不生成演示人物。</p></div><span className="status-chip warning">部分来源待接入</span></div>
      <div className="wiki-tabs" role="tablist" aria-label="资料类型">{tabs.map((item) => <button type="button" role="tab" aria-selected={tab === item.id} className={tab === item.id ? "active" : ""} key={item.id} onClick={() => setTab(item.id)}><strong>{item.label}</strong><span>{item.count ? `${item.count} 份档案` : "来源待同步"}</span></button>)}</div>
      <div className="wiki-filters"><label><span>搜索资料</span><input type="search" value={query} onChange={(event) => setQuery(event.target.value)} placeholder={`搜索${tabs.find((item) => item.id === tab)?.label}`} /></label><label><span>赛事</span><select><option>2026 FIFA 世界杯</option><option>全部赛事</option></select></label><label><span>球队</span><select disabled={tab === "teams"}><option>全部球队</option></select></label></div>
      {tab === "teams" ? <div className="wiki-grid">{visible.map((team) => <Link className="wiki-card" href={`/console/wiki/team/${team.id}`} key={team.id}><div className="wiki-identity"><img src={team.flag} alt={`${team.name}国旗`} /><div><span>{team.subtitle}</span><h2>{team.name}</h2><small>{team.rank}</small></div></div><div className="form-strip" aria-label="近五场战绩">{team.form.map((result, index) => <span className={result} key={`${result}-${index}`} />)}</div><footer><span>Alea 关联预测 1 场</span><strong>查看档案 →</strong></footer></Link>)}</div> : <section className="wiki-source-empty"><img src="/assets/icons/user-round.svg" alt="" /><p className="eyebrow">{tabs.find((item) => item.id === tab)?.label}资料</p><h2>可信资料源尚未接入</h2><p>不会用虚构姓名、头像或统计填满界面。来源确认后，档案会在此自动出现。</p></section>}
    </main>
  );
}
