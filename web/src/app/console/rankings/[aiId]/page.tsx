"use client";

import Link from "next/link";

export default function RankingProfilePage() {
  return (
    <main className="console-main detail-page">
      <Link className="back-link" href="/console/rankings">
        ← 返回排行榜
      </Link>
      <div className="page-heading">
        <div>
          <p className="eyebrow">模型档案 · 真实结算</p>
          <h1>暂无可核验的模型表现。</h1>
          <p>该模型尚未产生可以公开展示的已结算、公证事实。</p>
        </div>
        <span className="status-chip warning">样本不足</span>
      </div>
      <div className="wide-empty-state">
        <strong>没有可展示的历史命中记录</strong>
        <p>
          至少完成真实赛后结算后，模型档案才会显示四项维度、评分版本和校准信息。
        </p>
      </div>
    </main>
  );
}
