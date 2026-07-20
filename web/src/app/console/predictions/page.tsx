import { PredictionCard } from "@/components/prediction/prediction-card";

export default function PredictionsPage() {
  return (
    <main className="console-main research-page">
      <div className="page-heading research-heading">
        <div><p className="eyebrow">太玄问机 · 今日推演</p><h1>决赛推演，先把事实与模型判断分开。</h1><p>比赛身份与开球时间来自 FIFA；比分、投票和辩论均为固定 AI 原型输出，不是赛果。</p></div>
        <div className="source-badges"><span>AI 推演数据</span><span>来源：FIFA · 采集 2026-07-19</span></div>
      </div>
      <nav className="page-tabs" aria-label="推演视图"><a className="active" href="#today">今日推演</a><a href="#history">历史推演</a><a href="#states">生命周期状态</a></nav>
      <div className="list-meta"><strong>今日 1 张</strong><span>北京时间 7 月 20 日 03:00</span></div>
      <aside className="source-boundary"><strong>数据边界</strong><div><b>竞彩销售、首发、伤停、裁判与技术统计尚未取得可信快照</b><span>相关字段统一显示待确认；不生成场次编号、赔率或命中结果。</span></div></aside>
      <div id="today"><PredictionCard /></div>
      <section className="wide-empty-state" id="history"><strong>暂无可核验的历史推演</strong><p>官方赛果确认并完成真实结算后，记录才会进入历史筛选与模型统计。</p></section>
    </main>
  );
}
