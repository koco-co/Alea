"use client";

import { useMemo, useState } from "react";

export default function FixturesPage() {
  const [day, setDay] = useState("today");
  const [status, setStatus] = useState("all");
  const [query, setQuery] = useState("");
  const hasLiveData = useMemo(() => false, []);

  return (
    <main className="console-main research-page fixtures-page">
      <div className="page-heading research-heading">
        <div>
          <p className="eyebrow">赛程研究台 · 北京时间</p>
          <h1>真实竞彩 Offer 赛程研究。</h1>
          <p>仅展示已获授权来源返回的具体销售场次；来源不可用时保持空缺。</p>
        </div>
        <span className="status-chip warning">来源未连接</span>
      </div>
      <div className="date-switcher" aria-label="日期切换">
        {[
          ["previous", "前一日", "7 月 19 日"],
          ["today", "比赛日", "7 月 20 日"],
          ["next", "后一日", "7 月 21 日"],
        ].map(([value, label, date]) => (
          <button
            className={day === value ? "active" : ""}
            key={value}
            onClick={() => setDay(value)}
            type="button"
          >
            <strong>{label}</strong>
            <span>{date}</span>
          </button>
        ))}
        <button type="button" onClick={() => setDay("custom")}>
          指定日期
        </button>
      </div>
      <div className="fixture-filters">
        <div className="segmented-control" aria-label="状态筛选">
          {[
            ["all", "全部"],
            ["presale", "赛前"],
            ["pending", "待确认"],
            ["settled", "已结束"],
          ].map(([value, label]) => (
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
            <option>全部授权赛事</option>
          </select>
        </label>
        <label className="fixture-search">
          <span>球队搜索</span>
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="搜索西班牙或阿根廷"
          />
        </label>
      </div>
      <section className="fixture-group">
        <header>
          <strong>授权来源赛程</strong>
          <span>等待真实数据</span>
        </header>
        {!hasLiveData ? (
          <div className="wide-empty-state">
            <strong>当前没有可核验的真实竞彩场次</strong>
            <p>未取得授权数据时不会展示世界杯、联赛或固定球队示例。</p>
            <button
              className="button secondary"
              onClick={() => {
                setDay("today");
                setStatus("all");
                setQuery("");
              }}
              type="button"
            >
              重置筛选
            </button>
          </div>
        ) : null}
      </section>
    </main>
  );
}
