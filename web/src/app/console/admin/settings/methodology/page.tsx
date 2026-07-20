"use client";

import { useState } from "react";

const proposals = [
  {
    title: "雨战总进球预期下调",
    evidence: "4 场比赛 · 7 条有效教训",
    ai: "涉及 3 个 AI 实例",
    status: "待审",
  },
  {
    title: "首发缺失时限制置信度",
    evidence: "5 场比赛 · 9 条有效教训",
    ai: "涉及 5 个 AI 实例",
    status: "回测中",
  },
  {
    title: "高位防线的转换风险修正",
    evidence: "3 场比赛 · 5 条有效教训",
    ai: "涉及 2 个 AI 实例",
    status: "待管理员确认",
  },
] as const;

export default function MethodologyPage() {
  const [selected, setSelected] = useState(0);
  const [state, setState] = useState("待审");
  const proposal = proposals[selected];
  return (
    <main className="admin-main">
      <header className="admin-page-heading">
        <div>
          <p className="eyebrow">系统管理 · 推演方法</p>
          <h1>教训能提议改变，不能自动改变。</h1>
          <p>证据聚合、无赛果泄露回测、AI 评审和管理员确认共同构成发布门槛。</p>
        </div>
        <span className="status-chip">methodology-v1.3</span>
      </header>
      <section className="method-thresholds">
        <div>
          <span>跨比赛重复</span>
          <strong>≥ 3 场</strong>
        </div>
        <div>
          <span>相关教训累计</span>
          <strong>≥ 5 条</strong>
        </div>
        <div>
          <span>单 AI 连续犯错</span>
          <strong>≥ 5 场</strong>
        </div>
        <div>
          <span>证据回看窗口</span>
          <strong>全部有效历史</strong>
        </div>
        <button className="button secondary" type="button">
          配置阈值
        </button>
      </section>
      <div className="method-layout">
        <section className="proposal-list">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">方法论提议</p>
              <h2>待审队列</h2>
            </div>
          </div>
          {proposals.map((item, index) => (
            <button
              className={
                selected === index ? "proposal-item active" : "proposal-item"
              }
              type="button"
              key={item.title}
              onClick={() => {
                setSelected(index);
                setState(item.status);
              }}
            >
              <span className="status-chip">{item.status}</span>
              <strong>{item.title}</strong>
              <small>{item.evidence}</small>
              <small>{item.ai}</small>
            </button>
          ))}
        </section>
        <section className="proposal-detail">
          <header>
            <div>
              <p className="eyebrow">提议详情 · {state}</p>
              <h2>{proposal.title}</h2>
              <p>
                将“降雨量达到中雨且场地排水一般”作为独立条件，下调总进球期望并降低大比分方向置信度。
              </p>
            </div>
          </header>
          <div className="evidence-grid">
            <article>
              <span>证据完整性</span>
              <strong>4 / 4 场可回放</strong>
              <small>全部使用赛前冻结快照</small>
            </article>
            <article>
              <span>教训状态</span>
              <strong>7 条有效</strong>
              <small>0 条已归档</small>
            </article>
            <article>
              <span>样本前置</span>
              <strong>24 场可回测</strong>
              <small>满足 ≥20 场门槛</small>
            </article>
          </div>
          <section className="method-flow">
            <div className="complete">
              <span>01</span>
              <strong>证据聚合</strong>
              <small>已完成</small>
            </div>
            <div className={state === "待审" ? "active" : "complete"}>
              <span>02</span>
              <strong>OLD / NEW 回测</strong>
              <small>{state === "待审" ? "待启动" : "进行中"}</small>
            </div>
            <div>
              <span>03</span>
              <strong>AI 方法评审</strong>
              <small>1 轮匿名辩论</small>
            </div>
            <div>
              <span>04</span>
              <strong>管理员确认</strong>
              <small>生成新版本</small>
            </div>
          </section>
          <div className="method-copy">
            <p className="eyebrow">变更草案</p>
            <p>
              <strong>OLD：</strong>降雨仅作为一般天气因子参与模型判断。
            </p>
            <p>
              <strong>NEW：</strong>满足中雨与排水条件时，总进球期望下调
              0.25，相关比分置信度上限为 66%。
            </p>
          </div>
          <footer>
            <button className="button secondary" type="button">
              查看证据
            </button>
            <button
              className="button primary inline"
              type="button"
              onClick={() => setState("回测中")}
            >
              {state === "待审" ? "运行对照回测" : "查看回测进度"}
            </button>
          </footer>
        </section>
      </div>
      <section className="version-history">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">版本历史</p>
            <h2>核心方法论发布记录</h2>
          </div>
          <button className="button secondary" type="button">
            回滚上一版
          </button>
        </div>
        <div>
          <strong>methodology-v1.3</strong>
          <span>置信度校准与缺失资料折扣 · 2026-07-01</span>
          <span className="status-chip">当前版本</span>
        </div>
        <div>
          <strong>methodology-v1.2</strong>
          <span>定位球证据权重调整 · 2026-06-10</span>
          <button className="text-button" type="button">
            查看差异
          </button>
        </div>
      </section>
    </main>
  );
}
