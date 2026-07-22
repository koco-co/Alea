"use client";

import { useState } from "react";

const tabs = [
  { id: "teams", label: "球队", count: 0 },
  { id: "players", label: "球员", count: 0 },
  { id: "coaches", label: "教练", count: 0 },
  { id: "referees", label: "裁判", count: 0 },
] as const;

export default function WikiPage() {
  const [tab, setTab] = useState<(typeof tabs)[number]["id"]>("teams");
  const [query, setQuery] = useState("");
  return (
    <main className="console-main research-page wiki-page">
      <div className="page-heading research-heading">
        <div>
          <p className="eyebrow">赛事资料 · 资料档案</p>
          <h1>事实资料与 AI 判断，始终分开。</h1>
          <p>
            球队身份来自已核对的赛事资料；球员、教练与裁判源未接入前不生成演示人物。
          </p>
        </div>
        <span className="status-chip warning">部分来源待接入</span>
      </div>
      <div className="wiki-tabs" role="tablist" aria-label="资料类型">
        {tabs.map((item) => (
          <button
            type="button"
            role="tab"
            aria-selected={tab === item.id}
            className={tab === item.id ? "active" : ""}
            key={item.id}
            onClick={() => setTab(item.id)}
          >
            <strong>{item.label}</strong>
            <span>{item.count ? `${item.count} 份档案` : "来源待同步"}</span>
          </button>
        ))}
      </div>
      <div className="wiki-filters">
        <label>
          <span>搜索资料</span>
          <input
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder={`搜索${tabs.find((item) => item.id === tab)?.label}`}
          />
        </label>
        <label>
          <span>赛事</span>
          <select>
            <option>全部授权赛事</option>
            <option>等待来源同步</option>
          </select>
        </label>
        <label>
          <span>球队</span>
          <select disabled={tab === "teams"}>
            <option>全部球队</option>
          </select>
        </label>
      </div>
      {tab === "teams" ? (
        <section className="wiki-source-empty">
          <img src="/assets/icons/user-round.svg" alt="" />
          <p className="eyebrow">球队资料</p>
          <h2>暂无可核验的球队档案</h2>
          <p>
            {query.trim()
              ? `没有匹配“${query.trim()}”的已授权资料。`
              : "授权来源同步并完成实体映射后，球队档案会在此出现。"}
          </p>
        </section>
      ) : (
        <section className="wiki-source-empty">
          <img src="/assets/icons/user-round.svg" alt="" />
          <p className="eyebrow">
            {tabs.find((item) => item.id === tab)?.label}资料
          </p>
          <h2>可信资料源尚未接入</h2>
          <p>
            不会用虚构姓名、头像或统计填满界面。来源确认后，档案会在此自动出现。
          </p>
        </section>
      )}
    </main>
  );
}
