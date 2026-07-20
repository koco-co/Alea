"use client";

import { useMemo, useState } from "react";

type Draft = {
  id: string;
  title: string;
  kind: "单场" | "串关";
  status: "待审核" | "已发布" | "禁止发布";
  notary: string | null;
  audit: string;
  cutoff: string;
};

const DRAFTS: Draft[] = [
  {
    id: "draft-104",
    title: "西班牙 vs 阿根廷",
    kind: "单场",
    status: "待审核",
    notary: "N8C4-02",
    audit: "AUDIT-104",
    cutoff: "20:00",
  },
  {
    id: "draft-105",
    title: "法国 / 巴西 · 德国 / 葡萄牙",
    kind: "串关",
    status: "待审核",
    notary: "N8C4-03",
    audit: "AUDIT-105",
    cutoff: "22:00",
  },
  {
    id: "draft-106",
    title: "荷兰 vs 意大利",
    kind: "单场",
    status: "禁止发布",
    notary: null,
    audit: "AUDIT-106",
    cutoff: "21:30",
  },
];

const CHECKS = [
  ["法定人数", "通过", "3 个实例、2 个厂商"],
  ["玩法与串关合法性", "通过", "SPORTTERY-2026.07"],
  ["距停售 ≥ 10 分钟", "通过", "剩余 84 分钟"],
  ["重复在售卡片", "通过", "未发现重复"],
  ["赔率快照新鲜度", "警告", "62 分钟前，发布前需确认"],
  ["事实性陈述来源", "通过", "0 条无来源陈述"],
  ["关键输入暂缺", "警告", "首发名单尚未公布"],
] as const;

export default function PublishPage() {
  const [drafts, setDrafts] = useState<Draft[]>(DRAFTS);
  const [selectedId, setSelectedId] = useState(DRAFTS[0].id);
  const [tab, setTab] = useState<"predictions" | "rest">("predictions");
  const [note, setNote] = useState("");
  const [warningsConfirmed, setWarningsConfirmed] = useState(false);
  const [confirmPublish, setConfirmPublish] = useState(false);
  const [withdrawId, setWithdrawId] = useState<string | null>(null);
  const [withdrawReason, setWithdrawReason] = useState("");
  const [restPublished, setRestPublished] = useState(false);
  const [status, setStatus] = useState("");

  const selected = useMemo(
    () => drafts.find((draft) => draft.id === selectedId) ?? drafts[0],
    [drafts, selectedId],
  );
  const blocked = selected.status === "禁止发布" || !selected.notary;
  const hasWarnings = CHECKS.some(([, result]) => result === "警告");

  const publish = () => {
    if (blocked) return;
    if (hasWarnings && !warningsConfirmed) {
      setStatus("请先确认全部黄色警告，再进行发布二次确认。");
      return;
    }
    setConfirmPublish(true);
  };

  const confirmPublication = () => {
    setDrafts((items) =>
      items.map((draft) =>
        draft.id === selected.id ? { ...draft, status: "已发布" } : draft,
      ),
    );
    setConfirmPublish(false);
    setStatus("发布操作已提交；卡片内容锁定，仅可撤回下架。");
  };

  const withdraw = () => {
    if (!withdrawId || !withdrawReason.trim()) {
      setStatus("撤回必须填写原因。");
      return;
    }
    setDrafts((items) =>
      items.map((draft) =>
        draft.id === withdrawId ? { ...draft, status: "待审核" } : draft,
      ),
    );
    setWithdrawId(null);
    setWithdrawReason("");
    setStatus("卡片已撤回；历史占位、公证内容、排行与模拟盘统计保持不变。");
  };

  return (
    <main className="admin-main">
      <header className="admin-page-heading">
        <div>
          <p className="eyebrow">系统管理 · 发布审核 · PRD 15.3</p>
          <h1>管理员只能备注与决定是否发布，不能改写公证内容。</h1>
          <p>质检红项会阻断发布；黄项必须显式确认。发布与否不改变公证、排行或模拟盘统计。</p>
        </div>
        <span className="status-chip warning">{drafts.filter((draft) => draft.status === "待审核").length} 个待审核</span>
      </header>

      <div className="segmented-control" aria-label="发布审核类型">
        <button className={tab === "predictions" ? "active" : ""} type="button" onClick={() => setTab("predictions")}>预测卡草稿</button>
        <button className={tab === "rest" ? "active" : ""} type="button" onClick={() => setTab("rest")}>今日休战</button>
      </div>

      {tab === "rest" ? (
        <section className="data-table-card">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">零场入围 · 公告草稿</p>
              <h2>今日休战</h2>
            </div>
            <span className="status-chip">AUDIT-REST-20260720</span>
          </div>
          <div className="admin-context">
            <div>
              <p className="eyebrow">只读审计结论</p>
              <h2>当日全部在售场次均未超过 50% 加权 yes 票</h2>
              <p>选场范围、有效参与数、冻结版本与零场入围结论来自执行审计，不可编辑。</p>
            </div>
            <dl>
              <div><dt>选场范围</dt><dd>2026-07-20 · 全部在售</dd></div>
              <div><dt>有效参与</dt><dd>4 / 5 实例 · 3 厂商</dd></div>
              <div><dt>冻结版本</dt><dd>VOTE-7.1 · LINEUP-7.4</dd></div>
            </dl>
          </div>
          <label className="block">
            <span className="mb-2 block text-sm font-bold">管理员备注（可选）</span>
            <textarea className="min-h-28 w-full rounded-2xl border border-stone-200 bg-white p-4" placeholder="只能添加备注，不能改写 AI 提名与终投结论" />
          </label>
          <div className="mt-4 flex flex-wrap gap-3">
            <button className="button primary inline" type="button" disabled={restPublished} onClick={() => setRestPublished(true)}>
              {restPublished ? "今日休战已发布" : "发布今日休战"}
            </button>
            <button className="button secondary" type="button" onClick={() => setStatus("公告保持未发布；公开审计投影仍会进入历史推演。")}>不发布</button>
          </div>
        </section>
      ) : (
        <>
          <section className="data-table-card">
            <div className="panel-heading">
              <div>
                <p className="eyebrow">草稿列表</p>
                <h2>待审核单场卡与串关卡</h2>
              </div>
              <span className="status-chip">显示公证或执行审计编号</span>
            </div>
            <div className="data-table" role="table">
              <div className="data-table-row data-table-head" role="row">
                <span>草稿</span><span>类型</span><span>公证状态</span><span>停售</span><span>操作</span>
              </div>
              {drafts.map((draft) => (
                <div className="data-table-row" role="row" key={draft.id}>
                  <span><strong>{draft.title}</strong><small className="block">{draft.audit}</small></span>
                  <span>{draft.kind}</span>
                  <span className={draft.notary ? "positive-copy" : "negative-copy"}>{draft.notary ?? "未达法定人数"}</span>
                  <span className="mono-value">{draft.cutoff}</span>
                  <button className="button secondary" type="button" onClick={() => setSelectedId(draft.id)}>审核</button>
                </div>
              ))}
            </div>
          </section>

          <div className="review-detail-grid">
            <section className="review-section">
              <p className="eyebrow">用户端完整预览 · 只读</p>
              <h2>{selected.title}</h2>
              <div className="score-compare">
                <div><span>终投比分</span><strong>2 : 1</strong><i>半场 1 : 0</i></div>
                <div><span>共识度</span><strong>71%</strong><i>原始票数 5 / 7</i></div>
              </div>
              <div className="inline-callout">
                <strong>{selected.notary ? `公证账本 ${selected.notary}` : `执行审计 ${selected.audit}`}</strong>
                <p>{selected.notary ? "AI 结论、玩法、赔率快照、仓位与回放已经冻结。" : "未达法定人数，不写入公证账本且禁止发布。"}</p>
              </div>
              <label className="block">
                <span className="mb-2 block text-sm font-bold">管理员备注</span>
                <textarea className="min-h-28 w-full rounded-2xl border border-stone-200 bg-white p-4" value={note} onChange={(event) => setNote(event.target.value)} placeholder="备注会追加保存，不修改公证内容" />
              </label>
              <button className="button secondary" type="button" onClick={() => setStatus(note.trim() ? "管理员备注已追加。" : "请先填写管理员备注。")}>保存备注</button>
            </section>

            <section className="review-section">
              <p className="eyebrow">发布前质检清单</p>
              <h2>{blocked ? "存在红项，禁止发布" : "红项已通过，确认黄色警告"}</h2>
              <div className="switch-stack">
                {CHECKS.map(([label, result, detail]) => (
                  <div className="version-row" key={label}>
                    <div><strong>{label}</strong><span>{detail}</span></div>
                    <span className={result === "警告" ? "status-chip warning" : "status-chip"}>{result}</span>
                  </div>
                ))}
                {!selected.notary ? (
                  <div className="version-row">
                    <div><strong>法定人数</strong><span>仅执行审计，不可公证或发布</span></div>
                    <span className="status-chip warning">禁止</span>
                  </div>
                ) : null}
              </div>
              {hasWarnings && !blocked ? (
                <label className="switch-row">
                  <input type="checkbox" checked={warningsConfirmed} onChange={(event) => setWarningsConfirmed(event.target.checked)} />
                  <span><strong>我已检查并确认黄色警告</strong><small>确认动作会连同操作者与时间写入审计。</small></span>
                </label>
              ) : null}
              <div className="flex flex-wrap gap-3">
                {selected.status === "已发布" ? (
                  <button className="button secondary" type="button" onClick={() => setWithdrawId(selected.id)}>撤回下架</button>
                ) : (
                  <button className="button primary inline" type="button" disabled={blocked} onClick={publish}>发布</button>
                )}
              </div>
            </section>
          </div>
        </>
      )}

      {status ? <p className="form-message" role="status">{status}</p> : null}

      {confirmPublish ? (
        <div className="confirm-overlay" role="presentation">
          <section role="dialog" aria-modal="true" aria-labelledby="publish-confirm-title">
            <p className="eyebrow">二次确认</p>
            <h2 id="publish-confirm-title">确认发布 {selected.title}？</h2>
            <p>发布后卡片锁定，仅可撤回下架；公证内容、排行与模拟盘统计不受发布状态影响。</p>
            <div>
              <button className="button secondary" type="button" onClick={() => setConfirmPublish(false)}>取消</button>
              <button className="button primary inline" type="button" onClick={confirmPublication}>确认发布</button>
            </div>
          </section>
        </div>
      ) : null}

      {withdrawId ? (
        <div className="confirm-overlay" role="presentation">
          <section role="dialog" aria-modal="true" aria-labelledby="withdraw-title">
            <p className="eyebrow">撤回流程</p>
            <h2 id="withdraw-title">撤回已发布卡片？</h2>
            <p>用户端历史将保留撤回时间、原因和可展开的原内容。</p>
            <label>
              <span>撤回原因</span>
              <textarea value={withdrawReason} onChange={(event) => setWithdrawReason(event.target.value)} placeholder="必填，并写入审计记录" />
            </label>
            <div>
              <button className="button secondary" type="button" onClick={() => setWithdrawId(null)}>取消</button>
              <button className="button primary inline" type="button" onClick={withdraw}>确认撤回</button>
            </div>
          </section>
        </div>
      ) : null}
    </main>
  );
}
