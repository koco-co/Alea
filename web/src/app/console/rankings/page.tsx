"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { normalizeRankingRows, type RankingRow } from "@/lib/rankings-model";

const dimensions = [
  ["composite", "综合分"],
  ["exact_score", "比分命中率"],
  ["direction", "胜平负"],
  ["total_goals", "总进球"],
  ["half_full", "半全场"],
] as const;

export default function RankingsPage() {
  const [dimension, setDimension] = useState("composite");
  const [rows, setRows] = useState<RankingRow[]>([]);
  const [status, setStatus] = useState<"loading" | "ready" | "error">(
    "loading",
  );

  useEffect(() => {
    let cancelled = false;
    fetch(`/api/rankings?dimension=${dimension}&range=all`, {
      cache: "no-store",
    })
      .then(async (response) => {
        if (!response.ok) throw new Error("ranking_request_failed");
        return normalizeRankingRows(await response.json());
      })
      .then((value) => {
        if (!cancelled) {
          setRows(Array.isArray(value) ? value : []);
          setStatus("ready");
        }
      })
      .catch(() => {
        if (!cancelled) setStatus("error");
      });
    return () => {
      cancelled = true;
    };
  }, [dimension]);

  return (
    <main className="console-main research-page rankings-page">
      <div className="page-heading research-heading">
        <div>
          <p className="eyebrow">模型表现 · 版本化排行榜</p>
          <h1>只让结算事实决定名次。</h1>
          <p>排行榜只读取已公证、已结算并经过版本化评分的真实预测。</p>
        </div>
        <span
          className={`status-chip ${status === "error" ? "danger" : "warning"}`}
        >
          {status === "error" ? "数据暂不可用" : "等待真实结算"}
        </span>
      </div>
      <nav className="page-tabs" aria-label="排行榜维度">
        {dimensions.map(([value, label]) => (
          <button
            className={dimension === value ? "active" : ""}
            key={value}
            onClick={() => {
              setRows([]);
              setStatus("loading");
              setDimension(value);
            }}
            type="button"
          >
            {label}
          </button>
        ))}
      </nav>
      <div className="list-meta">
        <strong>{rows.length ? `${rows.length} 个模型` : "暂无排名"}</strong>
        <span>正式排名要求：已结算至少 10 场，覆盖率至少 80%</span>
      </div>
      {status === "error" ? (
        <div className="wide-empty-state">
          <strong>排行榜暂时无法加载</strong>
          <p>请稍后重试；页面不会用固定模型、比分或命中率替代真实数据。</p>
        </div>
      ) : rows.length === 0 ? (
        <div className="wide-empty-state">
          <strong>暂无已结算的公证预测</strong>
          <p>当前没有可排名数据。完成真实赛后结算后，模型才会进入此处。</p>
        </div>
      ) : (
        <section className="data-table-card">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">真实结算投影</p>
              <h2>模型排行</h2>
            </div>
          </div>
          <div className="data-table" role="table" aria-label="模型排行">
            <div className="data-table-row data-table-head" role="row">
              <span>名次 / 模型</span>
              <span>平滑得分</span>
              <span>结算场次</span>
              <span>覆盖率</span>
              <span>资格</span>
            </div>
            {rows.map((row) => (
              <Link
                className="data-table-row"
                href={`/console/rankings/${row.ai_instance_id}`}
                key={row.ai_instance_id}
              >
                <span>
                  {row.rank ?? "—"} · {row.display_name}
                </span>
                <span>{row.smoothed_score.toFixed(2)}</span>
                <span>{row.settled_count}</span>
                <span>{Math.round(row.participation_coverage * 100)}%</span>
                <span>{row.eligible_for_rank ? "正式排名" : "样本不足"}</span>
              </Link>
            ))}
          </div>
        </section>
      )}
    </main>
  );
}
