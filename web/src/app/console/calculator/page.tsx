"use client";

import { useState } from "react";

import {
  MatchSelector,
  type CalculatorMode,
} from "@/components/calculator/match-selector";
import { PlayConfig } from "@/components/calculator/play-config";
import { TicketPreview } from "@/components/calculator/ticket-preview";

export default function CalculatorPage() {
  const [mode, setMode] = useState<CalculatorMode>("fact");
  const [selected, setSelected] = useState(true);
  const [play, setPlay] = useState("胜平负");
  const [multiplier, setMultiplier] = useState(1);
  const [step, setStep] = useState(1);
  return (
    <main className="console-main research-page calculator-page">
      <div className="page-heading research-heading">
        <div>
          <p className="eyebrow">竞彩方案 · 选择比赛</p>
          <h1>先确认销售数据，再生成方案。</h1>
          <p>
            当前只保留 FIFA 已确认事实和固定 AI
            推演结果；竞彩场次编号、玩法、固定奖金、停售时间与销售状态尚无可信快照。
          </p>
        </div>
        <div className="source-badges">
          <span>AI 推演数据</span>
          <span>来源：FIFA · 采集 2026-07-19</span>
        </div>
      </div>
      <div className="calculator-mode" role="tablist">
        <button
          className={mode === "fact" ? "active" : ""}
          onClick={() => {
            setMode("fact");
            setStep(1);
          }}
          role="tab"
          type="button"
          aria-selected={mode === "fact"}
        >
          当前事实态
        </button>
        <button
          className={mode === "sample" ? "active" : ""}
          onClick={() => setMode("sample")}
          role="tab"
          type="button"
          aria-selected={mode === "sample"}
        >
          P0 交互样例
        </button>
      </div>
      <aside
        className={`calculator-warning ${mode === "sample" ? "sample" : ""}`}
      >
        <strong>
          {mode === "fact"
            ? "销售数据缺失，采纳、出图与下载保持禁用"
            : "独立交互样例：参数为非官方值，不是体彩 SP"}
        </strong>
        <p>
          {mode === "fact"
            ? "不生成场次编号、赔率、固定奖金、理论回报或结算结果。"
            : "仅用于验证选择、配置与出图流程，不与当前事实记录或公证记录混合。"}
        </p>
      </aside>
      <div className="mobile-stepper" aria-label="移动端步骤">
        {[1, 2, 3].map((value) => (
          <button
            className={step === value ? "active" : ""}
            key={value}
            onClick={() => setStep(value)}
            type="button"
          >
            <span>{value}</span>
            {value === 1 ? "选比赛" : value === 2 ? "配玩法" : "预览出图"}
          </button>
        ))}
      </div>
      <div className="calculator-grid">
        <div
          className={`calculator-column mobile-step-${step === 1 ? "active" : "hidden"}`}
        >
          <MatchSelector
            mode={mode}
            selected={selected}
            onToggle={() => setSelected((value) => !value)}
          />
          <button
            className="button primary mobile-next"
            onClick={() => setStep(2)}
            type="button"
          >
            下一步 · 配玩法
          </button>
        </div>
        <div
          className={`calculator-column mobile-step-${step === 2 ? "active" : "hidden"}`}
        >
          <PlayConfig
            mode={mode}
            selected={selected}
            play={play}
            onPlayChange={setPlay}
            multiplier={multiplier}
            onMultiplierChange={setMultiplier}
          />
          <button
            className="button primary mobile-next"
            onClick={() => setStep(3)}
            type="button"
          >
            下一步 · 预览出图
          </button>
        </div>
        <div
          className={`calculator-column mobile-step-${step === 3 ? "active" : "hidden"}`}
        >
          <TicketPreview mode={mode} multiplier={multiplier} />
        </div>
      </div>
    </main>
  );
}
