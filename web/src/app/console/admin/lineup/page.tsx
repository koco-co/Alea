"use client";

import { useCallback, useEffect, useState } from "react";

type RuntimeResult = {
  health?: { status?: string; codex_available?: boolean };
  catalog?: { models?: string[]; source?: string };
  error?: string;
};

export default function LineupPage() {
  const [mode, setMode] = useState<"codex_cli" | "api">("codex_cli");
  const [runtime, setRuntime] = useState<RuntimeResult>({});
  const [scanning, setScanning] = useState(true);
  const [testing, setTesting] = useState(false);
  const [status, setStatus] = useState("未修改");
  const [model, setModel] = useState("gpt-5.6-sol");
  const [secretAction, setSecretAction] = useState<
    "saved" | "replace" | "cleared"
  >("cleared");
  const [instanceEnabled, setInstanceEnabled] = useState(true);

  const scan = useCallback(async (): Promise<RuntimeResult> => {
    setScanning(true);
    try {
      const response = await fetch("/api/admin/codex-runtime", {
        cache: "no-store",
      });
      const body = (await response.json()) as RuntimeResult;
      setRuntime(body);
      const firstModel = body.catalog?.models?.[0];
      if (firstModel) setModel(firstModel);
      return body;
    } catch {
      const unavailable = { error: "codex_runner_unavailable" };
      setRuntime(unavailable);
      return unavailable;
    } finally {
      setScanning(false);
    }
  }, []);

  useEffect(() => {
    // Runtime discovery is an external synchronization; the state transitions
    // intentionally happen after the fetch resolves.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void scan();
  }, [scan]);

  const testConnection = async () => {
    setTesting(true);
    const result = await scan();
    setTesting(false);
    setStatus(
      result.health?.codex_available
        ? "运行时可用 · 尚未保存"
        : "测试失败 · 可重新扫描",
    );
  };

  const runtimeReady = runtime.health?.codex_available === true;
  const models = runtime.catalog?.models ?? [model];

  return (
    <main className="admin-main">
      <header className="admin-page-heading">
        <div>
          <p className="eyebrow">系统管理 · 模型阵容</p>
          <h1>配置可验证的 CLI 与 API Provider。</h1>
          <p>
            CLI 不保存伪 URL 或伪密钥；API 凭据只以密文保存，浏览器仅显示尾号。
          </p>
        </div>
        <span className={runtimeReady ? "status-chip" : "status-chip warning"}>
          {scanning
            ? "探测中…"
            : runtimeReady
              ? "Codex CLI 可用"
              : "Codex CLI 不可用"}
        </span>
      </header>

      <section className="admin-context">
        <div>
          <p className="eyebrow">执行模式</p>
          <h2>CLI 运行时 / API 密钥</h2>
          <p>
            本地与专用 Linux runner 使用相同隔离协议；生产登录由运维 device-auth
            完成。
          </p>
        </div>
        <div
          className="segmented-control"
          role="tablist"
          aria-label="Provider 执行模式"
        >
          <button
            className={mode === "codex_cli" ? "active" : ""}
            type="button"
            role="tab"
            aria-selected={mode === "codex_cli"}
            onClick={() => setMode("codex_cli")}
          >
            CLI 运行时
          </button>
          <button
            className={mode === "api" ? "active" : ""}
            type="button"
            role="tab"
            aria-selected={mode === "api"}
            onClick={() => setMode("api")}
          >
            API 密钥
          </button>
        </div>
      </section>

      <section className="provider-editor">
        <header>
          <div className="provider-title">
            <img src="/assets/vendors/openai.svg" alt="OpenAI 官方标识" />
            <div>
              <h2>{mode === "codex_cli" ? "Codex CLI" : "OpenAI 兼容 API"}</h2>
              <p>
                {mode === "codex_cli"
                  ? "runtime_key=codex · 不读取仓库、规则或插件"
                  : "HTTPS 端点 · 域名白名单 · envelope encryption"}
              </p>
            </div>
          </div>
          {mode === "codex_cli" ? (
            <button
              className="button secondary"
              type="button"
              onClick={() => void scan()}
            >
              {scanning ? "扫描中…" : "重新扫描"}
            </button>
          ) : null}
        </header>

        {mode === "codex_cli" ? (
          <>
            <div className="admin-form-section">
              <div className="section-heading">
                <div>
                  <p className="eyebrow">运行时探测</p>
                  <h2>本机 Codex 状态</h2>
                </div>
                <span
                  className={
                    runtimeReady ? "status-chip" : "status-chip warning"
                  }
                >
                  {runtimeReady ? "已登录且可执行" : "未连接"}
                </span>
              </div>
              <div className="admin-form-grid">
                <label>
                  <span>Runtime Key</span>
                  <input value="codex" readOnly />
                </label>
                <label>
                  <span>模型目录来源</span>
                  <input
                    value={runtime.catalog?.source ?? "尚未探测"}
                    readOnly
                  />
                </label>
              </div>
              {runtime.error ? (
                <p className="inline-callout">
                  Runner 不可用。检查本地服务或重新扫描。
                </p>
              ) : null}
            </div>
            <div className="admin-form-section">
              <div className="section-heading">
                <div>
                  <p className="eyebrow">模型目录</p>
                  <h2>选择结构化输出模型</h2>
                </div>
              </div>
              <div className="model-tools">
                <label>
                  <span>当前模型</span>
                  <select
                    value={model}
                    onChange={(event) => setModel(event.target.value)}
                  >
                    {models.map((item) => (
                      <option key={item}>{item}</option>
                    ))}
                  </select>
                </label>
                <label>
                  <span>推理强度</span>
                  <select
                    defaultValue="high"
                    onChange={() => setStatus("存在未保存修改")}
                  >
                    <option value="low">低</option>
                    <option value="medium">中</option>
                    <option value="high">高</option>
                  </select>
                </label>
              </div>
            </div>
          </>
        ) : (
          <div className="admin-form-section">
            <div className="section-heading">
              <div>
                <p className="eyebrow">端点与凭据</p>
                <h2>API 连接</h2>
              </div>
              <span className="status-chip warning">尚未配置</span>
            </div>
            <div className="admin-form-grid">
              <label>
                <span>HTTPS Endpoint</span>
                <input
                  placeholder="https://api.example.com/v1"
                  onChange={() => setStatus("存在未保存修改")}
                />
              </label>
              <label>
                <span>允许域名</span>
                <input
                  placeholder="api.example.com"
                  onChange={() => setStatus("存在未保存修改")}
                />
              </label>
              <div className="secret-field">
                <span>API 密钥</span>
                <strong>
                  {secretAction === "saved" ? "•••• •••• A7K9" : "未保存密钥"}
                </strong>
                <small>替换后旧测试结果立即失效；清除后实例自动禁用。</small>
                <div>
                  <button
                    className="button secondary"
                    type="button"
                    onClick={() => {
                      setSecretAction("replace");
                      setStatus("存在未保存修改");
                    }}
                  >
                    替换密钥
                  </button>
                  <button
                    className="button ghost-inline"
                    type="button"
                    onClick={() => {
                      setSecretAction("cleared");
                      setStatus("密钥已清除 · 尚未保存");
                    }}
                  >
                    清除密钥
                  </button>
                </div>
                {secretAction === "replace" ? (
                  <input
                    type="password"
                    autoComplete="new-password"
                    aria-label="新 API 密钥"
                    placeholder="输入新密钥"
                  />
                ) : null}
              </div>
            </div>
          </div>
        )}

        <div className="admin-form-section">
          <div className="section-heading">
            <div>
              <p className="eyebrow">连接验证</p>
              <h2>保存前测试</h2>
            </div>
            <button
              className="button secondary"
              disabled={testing}
              type="button"
              onClick={() => void testConnection()}
            >
              {testing ? "测试中…" : "测试连接"}
            </button>
          </div>
          <p className="inline-callout">
            {mode === "codex_cli"
              ? "测试 runner 健康、登录状态与模型目录；不会执行任意命令。"
              : "API 模式将在服务端验证端点、认证和最小模型能力。"}
          </p>
        </div>

        <div className="admin-form-section">
          <div className="section-heading">
            <div>
              <p className="eyebrow">实例管理</p>
              <h2>1 / 3 个实例</h2>
            </div>
            <button className="button secondary" type="button">
              新增实例
            </button>
          </div>
          <article className="instance-card">
            <header>
              <div>
                <strong>Codex · 主力</strong>
                <small>实例 01 · {instanceEnabled ? "已启用" : "已停用"}</small>
              </div>
              <label className="switch-row">
                <input
                  type="checkbox"
                  checked={instanceEnabled}
                  onChange={(event) => {
                    setInstanceEnabled(event.target.checked);
                    setStatus("存在未保存修改");
                  }}
                />
                <span>启用</span>
              </label>
            </header>
            <div className="admin-form-grid three">
              <label>
                <span>实例昵称</span>
                <input defaultValue="Codex · 主力" />
              </label>
              <label>
                <span>模型</span>
                <input value={model} readOnly />
              </label>
              <label>
                <span>Prompt 版本</span>
                <input defaultValue="prompt-v1.9" />
              </label>
              <label>
                <span>超时（秒）</span>
                <input type="number" defaultValue="120" min="1" max="900" />
              </label>
              <label>
                <span>并发上限</span>
                <input type="number" defaultValue="1" min="1" max="16" />
              </label>
            </div>
          </article>
        </div>
      </section>

      <footer className="admin-savebar">
        <div>
          <span
            className={
              status === "未修改" ? "status-chip" : "status-chip warning"
            }
          >
            {status}
          </span>
          <p>
            没有第二个真实 Provider 时，圆桌必须进入 no-quorum，不伪造成功。
          </p>
        </div>
        <div>
          <button
            className="button secondary"
            type="button"
            onClick={() => setStatus("未修改")}
          >
            撤销修改
          </button>
          <button
            className="button primary inline"
            type="button"
            onClick={() => setStatus("保存失败 · 数据库管理网关暂不可用")}
          >
            保存配置
          </button>
        </div>
      </footer>
    </main>
  );
}
