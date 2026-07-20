"use client";

import { useEffect, useRef, useState } from "react";

const agents = [
  { name: "Claude-1", logo: "/assets/vendors/anthropic.svg", score: "1 : 1" },
  { name: "GPT-1", logo: "/assets/vendors/openai.svg", score: "2 : 1" },
  { name: "DeepSeek-1", logo: "/assets/vendors/deepseek.svg", score: "2 : 0" },
  { name: "Gemini-1", logo: "/assets/vendors/gemini.svg", score: "2 : 1" },
  { name: "Qwen-1", logo: "/assets/vendors/qwen.svg", score: "1 : 0" },
] as const;

export function HeroAnimation() {
  const stageRef = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(true);

  useEffect(() => {
    const stage = stageRef.current;
    if (!stage) return;
    const observer = new IntersectionObserver(([entry]) => setVisible(entry.isIntersecting), { threshold: 0.2 });
    observer.observe(stage);
    return () => observer.disconnect();
  }, []);

  return (
    <div className={`hero-animation ${visible ? "is-playing" : "is-paused"}`} ref={stageRef} aria-label="七个 AI 独立预测后通过圆桌投票收敛为 2 比 1 的动画演示">
      <div className="animation-topline">
        <div>
          <span>2026 FIFA 世界杯 · 决赛</span>
          <strong>西班牙 vs 阿根廷</strong>
        </div>
        <span className="phase-pill">匿名圆桌</span>
      </div>

      <div className="agent-orbit" aria-hidden="true">
        {agents.map((agent, index) => (
          <div className={`agent-node agent-node-${index + 1}`} key={agent.name}>
            <span className="agent-score">{agent.score}</span>
            <span className="agent-logo"><img src={agent.logo} alt="" /></span>
          </div>
        ))}
        <div className="final-card">
          <span>AI 终投比分</span>
          <div className="final-score">
            <img src="/assets/teams/flag-spain.png" alt="" />
            <strong>2 : 1</strong>
            <img src="/assets/teams/flag-argentina.png" alt="" />
          </div>
          <small>半场 1 : 0</small>
          <b>加权共识 71%</b>
        </div>
      </div>

      <div className="animation-dialogues" aria-hidden="true">
        <span>“事实边界已核验”</span>
        <span>“我把 2:0 改为 2:1”</span>
      </div>
      <div className="consensus-track"><span /><strong>71%</strong></div>
      <p>5 / 7 原始票 · 3 位改票 · 待赛果确认</p>
    </div>
  );
}
