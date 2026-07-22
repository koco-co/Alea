"use client";

import { useState } from "react";

import { MatchSelector } from "@/components/calculator/match-selector";
import { PlayConfig } from "@/components/calculator/play-config";
import { TicketPreview } from "@/components/calculator/ticket-preview";

export default function CalculatorPage() {
  const mode = "fact" as const;
  const [selected] = useState(false);
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
            当前没有从授权竞彩来源取得可信快照；竞彩场次编号、玩法、固定奖金、
            停售时间与销售状态尚未确认。
          </p>
        </div>
        <div className="source-badges">
          <span>AI 推演数据</span>
          <span>来源：等待授权竞彩 Offer</span>
        </div>
      </div>
      <aside className="calculator-warning">
        <strong>销售数据缺失，采纳、出图与下载保持禁用</strong>
        <p>不生成场次编号、赔率、固定奖金、理论回报或结算结果。</p>
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
          <MatchSelector />
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
