"use client";

import Link from "next/link";
import { useMemo, useState } from "react";

const reviews = [
  {
    id: "review-20260718",
    competition: "国际邀请赛",
    date: "2026-07-18",
    matchup: "法国 vs 巴西",
    predicted: "2 : 0",
    actual: "1 : 2",
    result: "miss",
    ai: ["OpenAI", "Anthropic", "DeepSeek"],
    summary: "低估了巴西右路反击速度，并在伤停资料暂缺时给出了过高置信度。",
  },
  {
    id: "review-20260714",
    competition: "欧洲国家联赛",
    date: "2026-07-14",
    matchup: "葡萄牙 vs 荷兰",
    predicted: "1 : 1",
    actual: "1 : 1",
    result: "hit",
    ai: ["OpenAI", "Gemini", "Qwen"],
    summary: "对中场控制与低节奏的判断成立；定位球风险权重也保持在合理区间。",
  },
  {
    id: "review-20260710",
    competition: "南美锦标赛",
    date: "2026-07-10",
    matchup: "阿根廷 vs 哥伦比亚",
    predicted: "2 : 1",
    actual: "2 : 0",
    result: "miss",
    ai: ["Anthropic", "DeepSeek", "Kimi"],
    summary: "方向命中但高估客队进球，未充分吸收临场锋线变更。",
  },
] as const;

export default function ReviewsPage() {
  const [result, setResult] = useState("all");
  const [competition, setCompetition] = useState("all");
  const [ai, setAi] = useState("all");
  const filtered = useMemo(
    () =>
      reviews.filter(
        (review) =>
          (result === "all" || review.result === result) &&
          (competition === "all" || review.competition === competition) &&
          (ai === "all" || review.ai.includes(ai as never)),
      ),
    [result, competition, ai],
  );
  return (
    <main className="console-main research-page reviews-page">
      <div className="page-heading research-heading">
        <div>
          <p className="eyebrow">赛后复盘 · 败因沉淀</p>
          <h1>把“为什么错”变成下一次的规则。</h1>
          <p>
            仅展示已审核发布的复盘；命中场次同样复盘，以确认哪些判断真正可复用。
          </p>
        </div>
        <span className="status-chip">3 份已发布</span>
      </div>
      <div className="review-filters">
        <label>
          <span>日期</span>
          <input type="date" defaultValue="2026-07-20" />
        </label>
        <label>
          <span>赛事</span>
          <select
            value={competition}
            onChange={(event) => setCompetition(event.target.value)}
          >
            <option value="all">全部赛事</option>
            {[...new Set(reviews.map((review) => review.competition))].map(
              (item) => (
                <option key={item}>{item}</option>
              ),
            )}
          </select>
        </label>
        <label>
          <span>参与 AI</span>
          <select value={ai} onChange={(event) => setAi(event.target.value)}>
            <option value="all">全部 AI</option>
            {["OpenAI", "Anthropic", "DeepSeek", "Gemini", "Qwen", "Kimi"].map(
              (item) => (
                <option key={item}>{item}</option>
              ),
            )}
          </select>
        </label>
        <div className="segmented-control" aria-label="命中筛选">
          {[
            ["all", "全部"],
            ["hit", "命中"],
            ["miss", "未中"],
          ].map(([value, label]) => (
            <button
              className={result === value ? "active" : ""}
              type="button"
              key={value}
              onClick={() => setResult(value)}
            >
              {label}
            </button>
          ))}
        </div>
      </div>
      <div className="review-grid">
        {filtered.map((review) => (
          <article className="review-card" key={review.id}>
            <header>
              <div>
                <span>{review.competition}</span>
                <strong>{review.matchup}</strong>
              </div>
              <span className={`result-stamp ${review.result}`}>
                {review.result === "hit" ? "命中" : "未中"}
              </span>
            </header>
            <div className="score-compare">
              <div>
                <span>推演比分</span>
                <strong>{review.predicted}</strong>
              </div>
              <i />
              <div>
                <span>实际比分</span>
                <strong>{review.actual}</strong>
              </div>
            </div>
            <p>{review.summary}</p>
            <footer>
              <div className="ai-labels">
                {review.ai.map((item) => (
                  <span key={item}>{item}</span>
                ))}
              </div>
              <time>{review.date}</time>
            </footer>
            <Link href={`/console/reviews/${review.id}`}>阅读结构化复盘 →</Link>
          </article>
        ))}
      </div>
      {!filtered.length ? (
        <div className="wide-empty-state">
          <strong>当前筛选下没有复盘</strong>
          <p>调整赛事、AI 或命中状态后再试。</p>
        </div>
      ) : null}
    </main>
  );
}
