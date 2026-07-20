"use client";

import Link from "next/link";
import { useMemo, useState } from "react";

const INSTANCES = [
  ["openai-1", "OpenAI · 主分析", "GPT-5.2", "可用"],
  ["anthropic-1", "Anthropic · 反方", "Claude Sonnet", "可用"],
  ["google-1", "Google · 校验", "Gemini Pro", "待连接"],
] as const;

const MATCHES = [
  ["match-104", "FIFA Match 104", "西班牙 vs 阿根廷", "20:00 停售"],
  ["match-105", "FIFA Match 105", "法国 vs 巴西", "22:00 停售"],
  ["match-106", "FIFA Match 106", "德国 vs 葡萄牙", "23:30 停售"],
] as const;

type Mode = "autonomous" | "selected";

export default function RoundtablePage() {
  const [mode, setMode] = useState<Mode>("autonomous");
  const [instances, setInstances] = useState(["openai-1", "anthropic-1"]);
  const [matches, setMatches] = useState<string[]>([]);
  const [rounds, setRounds] = useState("1");
  const [candidateLimit, setCandidateLimit] = useState("8");
  const [scheduled, setScheduled] = useState(true);
  const [scheduleTime, setScheduleTime] = useState("08:00");
  const [status, setStatus] = useState<"idle" | "starting" | "created">("idle");
  const [error, setError] = useState("");

  const quorum = useMemo(() => {
    const selected = INSTANCES.filter(([id]) => instances.includes(id));
    const providers = new Set(
      selected.map(([, label]) => label.split(" · ")[0]),
    );
    return { instances: selected.length, providers: providers.size };
  }, [instances]);

  const toggle = (
    id: string,
    selected: string[],
    update: (next: string[]) => void,
  ) => {
    update(
      selected.includes(id)
        ? selected.filter((item) => item !== id)
        : [...selected, id],
    );
  };

  const start = () => {
    if (mode === "selected" && matches.length === 0) {
      setError("指定选场模式至少选择一场在售比赛。");
      return;
    }
    if (instances.length === 0) {
      setError("至少选择一个可用 AI 实例。");
      return;
    }
    setError("");
    setStatus("starting");
    window.setTimeout(() => setStatus("created"), 500);
  };

  return (
    <main className="admin-main">
      <header className="admin-page-heading">
        <div>
          <p className="eyebrow">系统管理 · 发起推演 · PRD 15.1</p>
          <h1>先冻结范围、阵容与规则，再让圆桌开始。</h1>
          <p>
            自主推演用于日常全量扫描；指定选场用于聚焦已选比赛。两种模式共用同一审计与法定人数规则。
          </p>
        </div>
        <span
          className={
            quorum.instances >= 3 && quorum.providers >= 2
              ? "status-chip"
              : "status-chip warning"
          }
        >
          {quorum.instances} 个实例 · {quorum.providers} 个厂商
        </span>
      </header>

      <section className="data-table-card">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">01 · 推演模式</p>
            <h2>选择自主扫描或指定比赛</h2>
          </div>
          <span className="status-chip">配置在提交时冻结</span>
        </div>
        <div className="segmented-control" aria-label="推演模式">
          <button
            className={mode === "autonomous" ? "active" : ""}
            type="button"
            onClick={() => setMode("autonomous")}
          >
            自主推演
          </button>
          <button
            className={mode === "selected" ? "active" : ""}
            type="button"
            onClick={() => setMode("selected")}
          >
            指定选场
          </button>
        </div>
        <div className="admin-form-section">
          {mode === "autonomous" ? (
            <div className="admin-form-grid three">
              <label>
                <span>业务日期</span>
                <input type="date" defaultValue="2026-07-20" />
              </label>
              <label>
                <span>赛事范围</span>
                <select defaultValue="all">
                  <option value="all">当日全部在售场次</option>
                  <option value="fifa">仅 FIFA 赛事</option>
                </select>
              </label>
              <label>
                <span>排除比赛</span>
                <select defaultValue="none">
                  <option value="none">不排除</option>
                  <option value="missing">排除关键数据暂缺场次</option>
                </select>
              </label>
            </div>
          ) : (
            <div className="switch-stack" aria-label="在售比赛多选">
              {MATCHES.map(([id, competition, teams, cutoff]) => (
                <label className="switch-row" key={id}>
                  <input
                    type="checkbox"
                    checked={matches.includes(id)}
                    onChange={() => toggle(id, matches, setMatches)}
                  />
                  <span>
                    <strong>{teams}</strong>
                    <small>
                      {competition} · {cutoff}
                    </small>
                  </span>
                </label>
              ))}
            </div>
          )}
        </div>
      </section>

      <section className="data-table-card">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">02 · 选择阵容</p>
            <h2>仅启用且通过连接测试的实例可参赛</h2>
          </div>
          <Link className="button secondary" href="/console/admin/lineup">
            管理模型阵容
          </Link>
        </div>
        <div className="switch-stack">
          {INSTANCES.map(([id, label, model, availability]) => {
            const disabled = availability !== "可用";
            return (
              <label className="switch-row" key={id}>
                <input
                  type="checkbox"
                  disabled={disabled}
                  checked={instances.includes(id)}
                  onChange={() => toggle(id, instances, setInstances)}
                />
                <span>
                  <strong>{label}</strong>
                  <small>
                    {model} · {availability}
                  </small>
                </span>
              </label>
            );
          })}
        </div>
        {quorum.instances < 3 || quorum.providers < 2 ? (
          <div className="inline-callout danger" role="status">
            <strong>当前阵容未达到法定人数</strong>
            <p>
              任务仍可发起并生成执行审计，但不会写入公证账本，也不能发布预测卡。
            </p>
          </div>
        ) : null}
      </section>

      <section className="data-table-card">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">03 · 参数与定时</p>
            <h2>辩论轮数、入围上限与每日计划</h2>
          </div>
          <Link
            className="button secondary"
            href="/console/admin/settings#settings-automation"
          >
            打开版本化设置
          </Link>
        </div>
        <div className="admin-form-grid three">
          <label>
            <span>辩论轮数</span>
            <select
              value={rounds}
              onChange={(event) => setRounds(event.target.value)}
            >
              <option value="1">1 轮（默认）</option>
              <option value="2">2 轮</option>
            </select>
          </label>
          {mode === "autonomous" ? (
            <label>
              <span>入围上限</span>
              <input
                min="1"
                max="20"
                type="number"
                value={candidateLimit}
                onChange={(event) => setCandidateLimit(event.target.value)}
              />
            </label>
          ) : null}
          <label>
            <span>每日自动发起时间</span>
            <input
              type="time"
              value={scheduleTime}
              onChange={(event) => setScheduleTime(event.target.value)}
            />
          </label>
        </div>
        <label className="switch-row">
          <input
            type="checkbox"
            checked={scheduled}
            onChange={(event) => setScheduled(event.target.checked)}
          />
          <span>
            <strong>启用每日定时圆桌</strong>
            <small>
              保存后按当前默认范围、阵容、轮数
              {mode === "autonomous" ? `与 ${candidateLimit} 场上限` : ""}
              自动创建任务
            </small>
          </span>
        </label>
      </section>

      {error ? (
        <p className="form-message error" role="alert">
          {error}
        </p>
      ) : null}
      {status === "created" ? (
        <section className="audit-strip" role="status">
          <p className="eyebrow">任务已创建</p>
          <div>
            <strong>ROUND-20260720-001</strong>
            <span>配置已冻结，执行审计将在首份 AI 结果返回时建立。</span>
            <Link
              className="button primary inline"
              href="/console/admin/roundtable/round-20260720-001"
            >
              查看推演直播
            </Link>
          </div>
        </section>
      ) : (
        <button
          className="button primary inline"
          type="button"
          disabled={status === "starting"}
          onClick={start}
        >
          {status === "starting" ? "正在创建圆桌…" : "发起圆桌"}
        </button>
      )}
    </main>
  );
}
