"use client";

import { useState } from "react";

import { PredictionCard } from "@/components/prediction/prediction-card";

const tabs = ["竞彩", "情报", "预测", "赛果", "复盘"] as const;
type Tab = (typeof tabs)[number];

export function FixtureDetailTabs() {
  const [active, setActive] = useState<Tab>("竞彩");
  return (
    <section className="fixture-tabs-shell">
      <div className="fixture-tabs" role="tablist" aria-label="比赛详情">
        {tabs.map((tab) => <button className={active === tab ? "active" : ""} key={tab} onClick={() => setActive(tab)} role="tab" type="button" aria-selected={active === tab}>{tab}</button>)}
      </div>
      <div className="fixture-tab-panel" role="tabpanel">
        {active === "竞彩" ? <WagerPanel /> : null}
        {active === "情报" ? <InformationPanel /> : null}
        {active === "预测" ? <PredictionCard compact /> : null}
        {active === "赛果" ? <MissingPanel title="赛果待官方确认" copy="比赛尚未开赛。完成官方赛果同步与冲突裁定后，进球事件、技术统计和最终阵容才会出现。" /> : null}
        {active === "复盘" ? <MissingPanel title="暂无可发布复盘" copy="赛果确认、卡片结算与模型复盘审核完成后，本区会显示可核验的复盘报告。" /> : null}
      </div>
    </section>
  );
}

function WagerPanel() {
  const games = ["胜平负", "让球", "比分", "总进球", "半全场"];
  return <div><header className="tab-panel-heading"><div><p className="eyebrow">竞彩 · 官方数据边界</p><h2>五种玩法均未连接数据源。</h2><p>不展示任何赔率、销售状态、期号或倒计时；数据接入并核验前仅保留明确空态。</p></div><span className="status-chip warning">来源未连接</span></header><div className="wager-grid">{games.map((game, index) => <article key={game}><span>玩法 {String(index + 1).padStart(2, "0")}</span><h3>{game}</h3><span className="status-chip warning">来源未连接</span><p>暂无官方玩法数据。</p></article>)}</div></div>;
}

function InformationPanel() {
  return <div><header className="tab-panel-heading"><div><p className="eyebrow">情报 · 可信快照边界</p><h2>身份已确认，其余赛前资料暂缺。</h2><p>近况、交锋、积分、伤停、预计首发与裁判信息都不会用演示数字补齐。</p></div></header><div className="missing-grid"><MissingPanel title="近期状态与历史交锋" copy="暂缺 · 待可信数据源接入" /><MissingPanel title="伤停与预计首发" copy="暂缺 · 待官方确认" /><MissingPanel title="积分与阵型" copy="暂缺 · 待可信快照核验" /></div></div>;
}

function MissingPanel({ title, copy }: { title: string; copy: string }) {
  return <article className="missing-panel"><span>暂缺</span><strong>{title}</strong><p>{copy}</p></article>;
}
