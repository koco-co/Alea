"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";

const groups = [
  ["scoring_rules", "评分与规则"],
  ["ledger_risk", "模拟盘与风控"],
  ["data_automation", "数据与自动化"],
  ["user_management", "用户管理"],
  ["prompts_methodology", "提示词与方法论"],
] as const;

export default function AdminSettingsPage() {
  const [dirty, setDirty] = useState(false);
  const [status, setStatus] = useState("未修改");
  const [query, setQuery] = useState("");
  const [showRuleHistory, setShowRuleHistory] = useState(false);
  const [versions, setVersions] = useState<Record<string, number>>({});
  const [backendNotice, setBackendNotice] = useState<string | null>(null);
  const formRef = useRef<HTMLFormElement>(null);
  const [sourceCheck, setSourceCheck] = useState<"pending" | "error">(
    "pending",
  );
  const change = () => {
    setDirty(true);
    setStatus("存在未保存修改");
  };
  const shown = (keywords: string) => !query || keywords.includes(query.trim());
  useEffect(() => {
    let cancelled = false;
    void Promise.all(
      groups.map(async ([group]) => {
        const response = await fetch(`/api/admin/settings/${group}`, {
          cache: "no-store",
        });
        if (!response.ok) throw new Error("settings_unavailable");
        const payload = (await response.json()) as {
          items?: Array<{ setting_key: string; version: number }>;
        };
        return [
          group,
          payload.items?.find((item) => item.setting_key === group)?.version ??
            0,
        ] as const;
      }),
    )
      .then((loaded) => {
        if (cancelled) return;
        setVersions(Object.fromEntries(loaded));
        setBackendNotice("已读取数据库中的设置版本；保存会创建不可变新版本。");
      })
      .catch(() => {
        if (!cancelled) {
          setBackendNotice(
            "设置数据库暂不可用；页面不会把本地默认值冒充为已保存版本。",
          );
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);
  const save = async () => {
    const form = formRef.current;
    if (!form) return;
    setStatus("正在保存新版本");
    const formData = new FormData(form);
    const values = Object.fromEntries(
      Array.from(formData.entries()).map(([key, value]) => [key, value]),
    );
    try {
      await Promise.all(
        groups
          .filter(([group]) => group !== "user_management")
          .map(async ([group]) => {
            const response = await fetch(`/api/admin/settings/${group}`, {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({
                expected_version: versions[group] || undefined,
                value: values,
                change_note: "管理员从系统设置页面发布新版本",
              }),
            });
            if (!response.ok) throw new Error("settings_save_failed");
          }),
      );
      setDirty(false);
      setStatus("已保存新版本");
      setBackendNotice("设置已写入数据库，并生成管理员审计记录。");
    } catch {
      setStatus("保存失败");
      setBackendNotice("保存失败；数据库未接受不完整或版本冲突的设置。");
    }
  };
  return (
    <main className="admin-main">
      <header className="admin-page-heading">
        <div>
          <p className="eyebrow">系统管理 · 系统设置 · PRD 15.6</p>
          <h1>运行参数必须可定位、可验证、可追溯。</h1>
          <p>每次保存都发布新版本，只影响之后新建的圆桌、方案或结算。</p>
        </div>
        <span className="status-chip">system-settings-v2.0</span>
      </header>
      {backendNotice ? (
        <div className="inline-callout">{backendNotice}</div>
      ) : null}
      <div className="settings-search">
        <label>
          <span>快速定位</span>
          <input
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="例如：评分、风控、同步、提示词"
          />
        </label>
        <span>{groups.filter((group) => shown(group[1])).length} 个分组</span>
      </div>
      <form
        className="settings-layout"
        ref={formRef}
        onSubmit={(event) => {
          event.preventDefault();
          void save();
        }}
      >
        <nav>
          {groups.map(([id, label]) => (
            <a href={`#settings-${id}`} key={id}>
              {label}
            </a>
          ))}
        </nav>
        <div className="settings-panels">
          {shown("评分 规则 权重 体彩 版本") ? (
            <section id="settings-scoring_rules" className="settings-panel">
              <header>
                <div>
                  <p className="eyebrow">评分与规则</p>
                  <h2>综合分与竞彩规则版本</h2>
                </div>
                <span className="status-chip">score-v1.4</span>
              </header>
              <div className="admin-form-grid three">
                <label>
                  <span>准确率权重（%）</span>
                  <input
                    name="scoring_accuracy_weight"
                    type="number"
                    defaultValue="50"
                    onChange={change}
                  />
                </label>
                <label>
                  <span>校准度权重（%）</span>
                  <input
                    name="scoring_calibration_weight"
                    type="number"
                    defaultValue="25"
                    onChange={change}
                  />
                </label>
                <label>
                  <span>模拟收益权重（%）</span>
                  <input
                    name="scoring_profit_weight"
                    type="number"
                    defaultValue="25"
                    onChange={change}
                  />
                </label>
              </div>
              <div className="version-row">
                <div>
                  <strong>SPORTTERY-2026.07</strong>
                  <span>生效于 2026-07-01 · 当前规则</span>
                </div>
                <button
                  className="button secondary"
                  type="button"
                  aria-expanded={showRuleHistory}
                  aria-controls="sporttery-rule-history"
                  onClick={() => setShowRuleHistory((shown) => !shown)}
                >
                  {showRuleHistory ? "收起版本历史" : "查看版本历史"}
                </button>
              </div>
              {showRuleHistory ? (
                <section
                  id="sporttery-rule-history"
                  className="switch-stack"
                  aria-label="竞彩规则版本历史"
                >
                  <div className="version-row">
                    <div>
                      <strong>SPORTTERY-2026.07 · v1</strong>
                      <span>
                        当前已发布 · 五玩法、动态过关、1–50
                        倍、奖金上限、无效场次重算、half-even
                      </span>
                    </div>
                    <span className="status-chip">已验证</span>
                  </div>
                  <div className="inline-callout">
                    <strong>官方来源台账 · 4 项</strong>
                    <p>
                      游戏方法、取消场次、混合过关与奖金舍入均已保存
                      URL、观察时间和规范化
                      SHA-256；实时赔率与销售状态继续待官方确认。
                    </p>
                  </div>
                  <div
                    className={
                      sourceCheck === "error"
                        ? "inline-callout danger"
                        : "inline-callout"
                    }
                    role="status"
                  >
                    <strong>
                      {sourceCheck === "error"
                        ? "在线核验服务未接入"
                        : "在线复核待接入"}
                    </strong>
                    <p>
                      {sourceCheck === "error"
                        ? "已安全回退至已发布规则；计算继续使用冻结版本，不改写来源状态。"
                        : "历史人工转录已验证；本页不会把未执行的实时在线复核显示为成功。"}
                    </p>
                    <button
                      className="button secondary"
                      type="button"
                      onClick={() =>
                        setSourceCheck((state) =>
                          state === "error" ? "pending" : "error",
                        )
                      }
                    >
                      {sourceCheck === "error"
                        ? "返回已发布版本"
                        : "重新核验来源"}
                    </button>
                  </div>
                </section>
              ) : null}
            </section>
          ) : null}
          {shown("模拟盘 风控 资金 仓位 风险 文案") ? (
            <section id="settings-ledger_risk" className="settings-panel">
              <header>
                <div>
                  <p className="eyebrow">模拟盘与风控</p>
                  <h2>资金与风险敞口</h2>
                </div>
              </header>
              <div className="admin-form-grid">
                <label>
                  <span>初始资金（模拟币）</span>
                  <input
                    name="risk_initial_balance"
                    type="number"
                    defaultValue="10000"
                    onChange={change}
                  />
                </label>
                <label>
                  <span>单日风险敞口（%）</span>
                  <input
                    name="risk_daily_percent"
                    type="number"
                    defaultValue="15"
                    onChange={change}
                  />
                </label>
                <label>
                  <span>单方案仓位下限（%）</span>
                  <input
                    name="risk_position_min_percent"
                    type="number"
                    defaultValue="1"
                    onChange={change}
                  />
                </label>
                <label>
                  <span>单方案仓位上限（%）</span>
                  <input
                    name="risk_position_max_percent"
                    type="number"
                    defaultValue="5"
                    onChange={change}
                  />
                </label>
                <label className="wide">
                  <span>风险提示文案</span>
                  <textarea
                    name="risk_copy"
                    defaultValue="本产品仅用于 AI 推演研究与娱乐展示，不构成投注建议；请理性购彩。"
                    onChange={change}
                  />
                </label>
              </div>
            </section>
          ) : null}
          {shown("数据 自动化 同步 定时 圆桌 复盘 历史 上下文") ? (
            <section id="settings-data_automation" className="settings-panel">
              <header>
                <div>
                  <p className="eyebrow">数据与自动化</p>
                  <h2>同步、定时圆桌与历史上下文</h2>
                </div>
                <span className="status-chip">版本化设置</span>
              </header>
              <div className="admin-form-grid three">
                <label>
                  <span>同步周期（分钟）</span>
                  <input
                    name="automation_sync_interval"
                    type="number"
                    defaultValue="30"
                    onChange={change}
                  />
                </label>
                <label>
                  <span>每日发起时间</span>
                  <input
                    name="automation_schedule_time"
                    type="time"
                    defaultValue="08:00"
                    onChange={change}
                  />
                </label>
                <label>
                  <span>默认辩论轮数</span>
                  <input
                    name="automation_debate_rounds"
                    type="number"
                    defaultValue="2"
                    onChange={change}
                  />
                </label>
                <label>
                  <span>默认入围上限</span>
                  <input
                    name="automation_nomination_limit"
                    type="number"
                    defaultValue="8"
                    onChange={change}
                  />
                </label>
                <label>
                  <span>近期结算记录（1–50）</span>
                  <input
                    type="number"
                    min="1"
                    max="50"
                    name="automation_recent_match_limit"
                    defaultValue="10"
                    onChange={change}
                  />
                </label>
                <label>
                  <span>有效教训上限（1–20）</span>
                  <input
                    type="number"
                    min="1"
                    max="20"
                    name="automation_lesson_limit"
                    defaultValue="5"
                    onChange={change}
                  />
                </label>
              </div>
              <div className="switch-stack">
                <label className="switch-row">
                  <input
                    name="automation_scheduled_roundtable"
                    type="checkbox"
                    defaultChecked
                    onChange={change}
                  />
                  <span>
                    <strong>开启每日定时圆桌</strong>
                    <small>按默认阵容与轮数创建新任务</small>
                  </span>
                </label>
                <label className="switch-row">
                  <input
                    name="automation_auto_review"
                    type="checkbox"
                    defaultChecked
                    onChange={change}
                  />
                  <span>
                    <strong>赛果确认后自动创建复盘</strong>
                    <small>冲突未裁定时不会触发</small>
                  </span>
                </label>
              </div>
            </section>
          ) : null}
          {shown("用户 管理 权限") ? (
            <section id="settings-user_management" className="settings-panel">
              <header>
                <div>
                  <p className="eyebrow">用户管理</p>
                  <h2>访问控制与审计</h2>
                </div>
                <Link className="button secondary" href="/console/admin/users">
                  打开用户管理
                </Link>
              </header>
              <p>禁用、恢复与角色调整都需要二次确认，并记录操作者与时间。</p>
            </section>
          ) : null}
          {shown("提示词 方法论 版本 发布 回滚") ? (
            <section
              id="settings-prompts_methodology"
              className="settings-panel"
            >
              <header>
                <div>
                  <p className="eyebrow">提示词与方法论</p>
                  <h2>受控版本发布</h2>
                </div>
                <Link
                  className="button secondary"
                  href="/console/admin/settings/methodology"
                >
                  打开方法评审
                </Link>
              </header>
              <div className="version-row">
                <div>
                  <strong>prompt-v1.9 · methodology-v1.3</strong>
                  <span>历史圆桌继续引用冻结时版本</span>
                </div>
                <button className="button secondary" type="button">
                  查看发布记录
                </button>
              </div>
            </section>
          ) : null}
        </div>
      </form>
      <footer className="admin-savebar settings-sticky">
        <div>
          <span className={dirty ? "status-chip warning" : "status-chip"}>
            {status}
          </span>
          <p>
            {dirty
              ? "离开前请保存或撤销本次设置草稿。"
              : "所有配置与已发布版本一致。"}
          </p>
        </div>
        <div>
          <button
            className="button secondary"
            disabled={!dirty}
            type="button"
            onClick={() => {
              setDirty(false);
              setStatus("未修改");
            }}
          >
            撤销修改
          </button>
          <button
            className="button primary inline"
            disabled={!dirty}
            type="button"
            onClick={() => void save()}
          >
            保存新版本
          </button>
        </div>
      </footer>
    </main>
  );
}
