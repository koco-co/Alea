"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import {
  addInstanceDraft,
  canEnableConnection,
  initialInstances,
  latestConnection,
  nextConnectionVersion,
  type ExecutionMode,
  type InstanceDraft,
  type ProviderRecord,
} from "./model";

interface ApiProviderDefinition {
  key: string;
  display_name: string;
  adapter: string;
  default_base_url: string;
  allowed_domains: string[];
  requires_api_key: boolean;
  fallback_models: string[];
  supports_reasoning: boolean;
  allow_local_http: boolean;
}

interface CliRuntimeDefinition {
  key: string;
  display_name: string;
  binary_names: string[];
  fallback_models: string[];
  stream_format: string;
  supports_custom_model: boolean;
  supports_reasoning: boolean;
  roundtable_capable: boolean;
}

interface ProviderCatalogResponse {
  api_providers?: ApiProviderDefinition[];
  cli_runtimes?: CliRuntimeDefinition[];
  error?: string;
}

interface ProviderListResponse {
  providers?: ProviderRecord[];
  error?: string;
}

interface TestResult {
  status: "idle" | "running" | "passed" | "failed";
  version?: string | null;
  authStatus?: string;
  models?: string[];
  errorCode?: string | null;
  latencyMs?: number;
}

const vendorAssets: Record<string, string> = {
  openai: "/assets/vendors/openai.svg",
  codex: "/assets/vendors/openai.svg",
  anthropic: "/assets/vendors/anthropic.svg",
  claude: "/assets/vendors/anthropic.svg",
  google: "/assets/vendors/gemini.svg",
  gemini: "/assets/vendors/gemini.svg",
  deepseek: "/assets/vendors/deepseek.svg",
  kimi: "/assets/vendors/kimi.png",
  qwen: "/assets/vendors/qwen.svg",
};

function responseError(body: unknown, fallback: string): string {
  if (body && typeof body === "object") {
    const value = (body as { detail?: unknown; error?: unknown }).detail;
    if (typeof value === "string") return value;
    const error = (body as { error?: unknown }).error;
    if (typeof error === "string") return error;
  }
  return fallback;
}

export default function LineupPage() {
  const [mode, setMode] = useState<ExecutionMode>("api");
  const [catalog, setCatalog] = useState<ProviderCatalogResponse>({});
  const [records, setRecords] = useState<ProviderRecord[]>([]);
  const [selectedKey, setSelectedKey] = useState("deepseek");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [status, setStatus] = useState("正在加载真实配置…");
  const [baseUrl, setBaseUrl] = useState("");
  const [allowedDomains, setAllowedDomains] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [clearSecret, setClearSecret] = useState(false);
  const [executablePath, setExecutablePath] = useState("");
  const [modelId, setModelId] = useState("");
  const [customModelId, setCustomModelId] = useState("");
  const [instances, setInstances] = useState<InstanceDraft[]>([]);
  const [retiredInstanceIds, setRetiredInstanceIds] = useState<string[]>([]);
  const [testResult, setTestResult] = useState<TestResult>({ status: "idle" });

  const apiDefinitions = catalog.api_providers ?? [];
  const cliDefinitions = catalog.cli_runtimes ?? [];
  const definitions = mode === "api" ? apiDefinitions : cliDefinitions;
  const selectedDefinition = definitions.find(
    (definition) => definition.key === selectedKey,
  );
  const persistedProvider = records.find(
    (provider) => provider.key === selectedKey,
  );
  const persistedConnection = latestConnection(persistedProvider);

  const modelOptions = useMemo(() => {
    const fallback = selectedDefinition?.fallback_models ?? [];
    const discovered = testResult.models ?? [];
    return [...new Set([...discovered, ...fallback, modelId].filter(Boolean))];
  }, [modelId, selectedDefinition, testResult.models]);

  const invalidateTest = useCallback(() => {
    setTestResult({ status: "idle" });
    setStatus("存在未保存修改 · 需要重新测试");
  }, []);

  const hydrateSelection = useCallback(
    (
      nextMode: ExecutionMode,
      key: string,
      nextCatalog: ProviderCatalogResponse,
      nextRecords: ProviderRecord[],
    ) => {
      const entries =
        nextMode === "api"
          ? (nextCatalog.api_providers ?? [])
          : (nextCatalog.cli_runtimes ?? []);
      const definition = entries.find((item) => item.key === key) ?? entries[0];
      if (!definition) return;
      const provider = nextRecords.find((item) => item.key === definition.key);
      const connection = latestConnection(provider);
      const fallbackModel = definition.fallback_models[0] ?? "";
      const nextModel = connection?.model_id ?? fallbackModel;
      setMode(nextMode);
      setSelectedKey(definition.key);
      setBaseUrl(
        nextMode === "api"
          ? (connection?.api_url ??
              (definition as ApiProviderDefinition).default_base_url)
          : "",
      );
      setAllowedDomains(
        nextMode === "api"
          ? (
              provider?.allowed_api_domains ??
              (definition as ApiProviderDefinition).allowed_domains
            ).join(", ")
          : "",
      );
      setExecutablePath(
        nextMode === "cli" ? (connection?.executable_path ?? "") : "",
      );
      setApiKey("");
      setClearSecret(false);
      setModelId(nextModel);
      setCustomModelId("");
      setInstances(
        initialInstances(provider, definition.display_name, nextModel),
      );
      setRetiredInstanceIds([]);
      setTestResult(
        connection?.health
          ? {
              status:
                connection.health.status === "passed" ? "passed" : "failed",
              version: connection.health.detected_version,
              authStatus: connection.health.auth_status,
              models: connection.health.available_models,
              errorCode: connection.health.error_code,
            }
          : { status: "idle" },
      );
      setStatus(
        connection ? `已加载连接版本 v${connection.version}` : "新连接",
      );
    },
    [],
  );

  function applySelection(nextMode: ExecutionMode, key: string) {
    hydrateSelection(nextMode, key, catalog, records);
  }

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [catalogResponse, providersResponse] = await Promise.all([
        fetch("/api/admin/providers/catalog", { cache: "no-store" }),
        fetch("/api/admin/providers", { cache: "no-store" }),
      ]);
      const nextCatalog =
        (await catalogResponse.json()) as ProviderCatalogResponse;
      const nextProviderBody =
        (await providersResponse.json()) as ProviderListResponse;
      if (!catalogResponse.ok) {
        throw new Error(responseError(nextCatalog, "provider_catalog_failed"));
      }
      const nextRecords = providersResponse.ok
        ? (nextProviderBody.providers ?? [])
        : [];
      setCatalog(nextCatalog);
      setRecords(nextRecords);
      const preferredApi =
        nextCatalog.api_providers?.find((item) => item.key === "deepseek") ??
        nextCatalog.api_providers?.[0];
      if (preferredApi) {
        hydrateSelection("api", preferredApi.key, nextCatalog, nextRecords);
      }
      if (!providersResponse.ok) {
        setStatus(
          `目录已加载；持久化配置不可用：${responseError(nextProviderBody, "provider_list_failed")}`,
        );
      }
    } catch (error) {
      setStatus(
        `加载失败：${error instanceof Error ? error.message : "unknown_error"}`,
      );
    } finally {
      setLoading(false);
    }
  }, [hydrateSelection]);

  useEffect(() => {
    // Initial catalogue and persistence hydration is an external synchronization.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load();
  }, [load]);

  async function testConnection() {
    if (!selectedDefinition || !modelId) {
      setStatus("请先选择厂商/工具与模型");
      return;
    }
    setTestResult({ status: "running" });
    setStatus("正在执行真实连接测试…");
    const endpoint =
      mode === "cli"
        ? "/api/admin/providers/runtime/probe"
        : "/api/admin/providers/runtime/api-test";
    const payload =
      mode === "cli"
        ? {
            runtime_key: selectedKey,
            executable_path: executablePath,
            model_id: modelId,
            schema_test: true,
            timeout_seconds: 60,
          }
        : {
            provider_key: selectedKey,
            api_url: baseUrl,
            api_key: apiKey || undefined,
            model_id: modelId,
            allowed_api_domains: allowedDomains
              .split(",")
              .map((item) => item.trim())
              .filter(Boolean),
            timeout_seconds: 30,
            connection_id: persistedConnection?.id,
            connection_version: persistedConnection?.version,
          };
    try {
      const response = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const body = (await response.json()) as {
        status?: string;
        version?: string | null;
        auth_status?: string;
        models?: string[];
        error_code?: string | null;
        latency_ms?: number;
      };
      const passed = response.ok && body.status === "passed";
      setTestResult({
        status: passed ? "passed" : "failed",
        version: body.version,
        authStatus: body.auth_status,
        models: body.models,
        errorCode:
          body.error_code ??
          (passed ? null : responseError(body, "connection_test_failed")),
        latencyMs: body.latency_ms,
      });
      setStatus(
        passed
          ? `连接测试通过${body.latency_ms ? ` · ${body.latency_ms} ms` : ""}`
          : `测试失败 · ${body.error_code ?? responseError(body, "connection_test_failed")}`,
      );
    } catch {
      setTestResult({
        status: "failed",
        errorCode: "connection_test_unavailable",
      });
      setStatus("测试失败 · 后台暂不可用");
    }
  }

  async function saveConfiguration() {
    if (!selectedDefinition || !modelId) return;
    const authStatus = testResult.authStatus ?? "unknown";
    const qualified = canEnableConnection(mode, testResult.status, authStatus);
    if (!qualified && instances.some((instance) => instance.enabled)) {
      setStatus("保存失败 · 未通过连接与认证测试的实例不能启用");
      return;
    }
    setSaving(true);
    setStatus("正在保存版本化配置…");
    const connectionId = crypto.randomUUID();
    const domains = allowedDomains
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean);
    const connectionVersion = nextConnectionVersion(persistedProvider);
    const requestBody = {
      provider_id: persistedProvider?.id,
      provider_key: selectedKey,
      connection_id: connectionId,
      connection_version: connectionVersion,
      display_name: selectedDefinition.display_name,
      execution_mode: mode,
      protocol:
        mode === "api"
          ? (selectedDefinition as ApiProviderDefinition).adapter
          : "local_cli",
      api_url: mode === "api" ? baseUrl : undefined,
      runtime_key: mode === "cli" ? selectedKey : undefined,
      executable_path: mode === "cli" ? executablePath : undefined,
      model_id: modelId,
      custom_model_ids: customModelId ? [customModelId] : [],
      allowed_api_domains: mode === "api" ? domains : [],
      api_key: mode === "api" && apiKey ? apiKey : undefined,
      clear_secret: mode === "api" ? clearSecret : false,
      previous_connection_id:
        mode === "api" ? persistedConnection?.id : undefined,
      previous_connection_version:
        mode === "api" ? persistedConnection?.version : undefined,
      enabled: qualified && instances.some((instance) => instance.enabled),
    };
    try {
      const response = await fetch(`/api/admin/providers/${connectionId}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(requestBody),
      });
      const body = (await response.json()) as {
        provider_id?: string;
        error?: string;
        detail?: string;
      };
      if (!response.ok || !body.provider_id) {
        throw new Error(responseError(body, "provider_save_failed"));
      }
      for (const instanceId of retiredInstanceIds) {
        const retireResponse = await fetch(
          `/api/admin/providers/${body.provider_id}/instances/${instanceId}`,
          { method: "DELETE" },
        );
        if (!retireResponse.ok) {
          const retireError = (await retireResponse.json()) as unknown;
          throw new Error(
            responseError(retireError, "provider_instance_retire_failed"),
          );
        }
      }
      for (const instance of instances) {
        const instanceBody = {
          connection_id: connectionId,
          nickname: instance.nickname,
          instance_number: instance.instanceNumber,
          model_id: instance.modelId,
          reasoning_level: instance.reasoningLevel || null,
          timeout_seconds: instance.timeoutSeconds,
          max_concurrency: instance.maxConcurrency,
          prompt_version: instance.promptVersion,
          enabled: qualified && instance.enabled,
        };
        const instanceResponse = await fetch(
          instance.id
            ? `/api/admin/providers/${body.provider_id}/instances/${instance.id}`
            : `/api/admin/providers/${body.provider_id}/instances`,
          {
            method: instance.id ? "PUT" : "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(instanceBody),
          },
        );
        if (!instanceResponse.ok) {
          const instanceError = (await instanceResponse.json()) as unknown;
          throw new Error(
            responseError(instanceError, "provider_instance_save_failed"),
          );
        }
      }
      setApiKey("");
      setClearSecret(false);
      setRetiredInstanceIds([]);
      setStatus(`已保存连接版本 v${connectionVersion}`);
      await load();
    } catch (error) {
      setStatus(
        `保存失败 · ${error instanceof Error ? error.message : "unknown_error"}`,
      );
    } finally {
      setSaving(false);
    }
  }

  function updateInstance(index: number, patch: Partial<InstanceDraft>) {
    setInstances((current) =>
      current.map((instance, itemIndex) =>
        itemIndex === index ? { ...instance, ...patch } : instance,
      ),
    );
  }

  async function deleteConfiguration() {
    if (!persistedProvider) return;
    setSaving(true);
    setStatus("正在删除配置并停用关联实例…");
    try {
      const response = await fetch(
        `/api/admin/providers/${persistedProvider.id}`,
        { method: "DELETE" },
      );
      if (!response.ok) {
        const body = (await response.json()) as unknown;
        throw new Error(responseError(body, "provider_retire_failed"));
      }
      setStatus("配置已删除");
      await load();
    } catch (error) {
      setStatus(
        `删除失败 · ${error instanceof Error ? error.message : "unknown_error"}`,
      );
    } finally {
      setSaving(false);
    }
  }

  const qualified = canEnableConnection(
    mode,
    testResult.status,
    testResult.authStatus ?? "unknown",
  );
  const iconPath = selectedDefinition
    ? vendorAssets[selectedDefinition.key]
    : undefined;

  return (
    <main className="admin-main lineup-page">
      <header className="admin-page-heading">
        <div>
          <p className="eyebrow">系统管理 · 模型阵容</p>
          <h1>API 厂商与 CLI 工具</h1>
          <p>
            两类连接共享模型、实例和 Prompt
            版本管理；只有通过真实连接与结构化输出测试的实例才能进入新圆桌。
          </p>
        </div>
        <span
          className={
            testResult.status === "passed"
              ? "status-chip"
              : "status-chip warning"
          }
        >
          {loading
            ? "加载中…"
            : testResult.status === "running"
              ? "测试中…"
              : testResult.status === "passed"
                ? "连接已验证"
                : "等待验证"}
        </span>
      </header>

      <section className="admin-context lineup-mode-header">
        <div>
          <p className="eyebrow">执行模式</p>
          <h2>在同一个阵容中管理两类连接</h2>
          <p>
            CLI 路径由管理员填写；平台不会扫描 PATH，也不会部署 runner daemon。
          </p>
        </div>
        <div className="segmented-control" role="tablist" aria-label="执行模式">
          <button
            className={mode === "api" ? "active" : ""}
            type="button"
            role="tab"
            aria-selected={mode === "api"}
            onClick={() => {
              const first =
                apiDefinitions.find((item) => item.key === "deepseek") ??
                apiDefinitions[0];
              if (first) applySelection("api", first.key);
            }}
          >
            API 厂商
          </button>
          <button
            className={mode === "cli" ? "active" : ""}
            type="button"
            role="tab"
            aria-selected={mode === "cli"}
            onClick={() => {
              const first =
                cliDefinitions.find((item) => item.key === "codex") ??
                cliDefinitions[0];
              if (first) applySelection("cli", first.key);
            }}
          >
            CLI 工具
          </button>
        </div>
      </section>

      <div className="lineup-layout">
        <aside className="provider-list" aria-label={`${mode} 连接目录`}>
          <div className="provider-list-heading">
            <div>
              <p className="eyebrow">
                {mode === "api" ? "API Provider" : "Local CLI"}
              </p>
              <h2>{mode === "api" ? "厂商目录" : "工具目录"}</h2>
            </div>
            <span>{definitions.length}</span>
          </div>
          <label className="provider-search">
            <span className="sr-only">搜索目录</span>
            <input
              type="search"
              placeholder="搜索厂商或 CLI"
              onChange={(event) => {
                const value = event.target.value.toLocaleLowerCase();
                const match = definitions.find((item) =>
                  item.display_name.toLocaleLowerCase().includes(value),
                );
                if (match) applySelection(mode, match.key);
              }}
            />
          </label>
          <div className="provider-directory">
            {definitions.map((definition) => {
              const provider = records.find(
                (item) => item.key === definition.key,
              );
              const connection = latestConnection(provider);
              const asset = vendorAssets[definition.key];
              return (
                <button
                  className={`provider-item ${selectedKey === definition.key ? "active" : ""}`}
                  key={definition.key}
                  type="button"
                  onClick={() => applySelection(mode, definition.key)}
                >
                  {asset ? (
                    <img
                      src={asset}
                      alt={`${definition.display_name} 官方标识`}
                    />
                  ) : null}
                  <span>
                    <strong>{definition.display_name}</strong>
                    <small>
                      {connection
                        ? `v${connection.version} · ${connection.test_status}`
                        : "尚未配置"}
                    </small>
                  </span>
                  <i className={connection?.enabled ? "ready" : ""} />
                </button>
              );
            })}
          </div>
        </aside>

        <section className="provider-editor">
          {selectedDefinition ? (
            <>
              <header>
                <div className="provider-title">
                  {iconPath ? (
                    <img
                      src={iconPath}
                      alt={`${selectedDefinition.display_name} 官方标识`}
                    />
                  ) : null}
                  <div>
                    <p className="eyebrow">
                      {mode === "api" ? "API 厂商" : "CLI 工具"}
                    </p>
                    <h2>{selectedDefinition.display_name}</h2>
                    <p>
                      {mode === "api"
                        ? (selectedDefinition as ApiProviderDefinition).adapter
                        : `runtime_key=${selectedDefinition.key}`}
                    </p>
                  </div>
                </div>
                <span
                  className={qualified ? "status-chip" : "status-chip warning"}
                >
                  {qualified ? "可进入圆桌" : "不可进入圆桌"}
                </span>
              </header>

              <div className="admin-form-section">
                <div className="section-heading">
                  <div>
                    <p className="eyebrow">
                      {mode === "api" ? "端点与凭据" : "本地可执行文件"}
                    </p>
                    <h2>{mode === "api" ? "连接配置" : "运行时路径"}</h2>
                  </div>
                </div>
                {mode === "api" ? (
                  <div className="admin-form-grid">
                    <label>
                      <span>Base URL</span>
                      <input
                        value={baseUrl}
                        onChange={(event) => {
                          setBaseUrl(event.target.value);
                          invalidateTest();
                        }}
                        placeholder="https://api.example.com/v1"
                      />
                    </label>
                    <label>
                      <span>允许域名</span>
                      <input
                        value={allowedDomains}
                        onChange={(event) => {
                          setAllowedDomains(event.target.value);
                          invalidateTest();
                        }}
                        placeholder="api.example.com"
                      />
                    </label>
                    <div className="secret-field">
                      <span>API Key</span>
                      <strong>
                        {persistedConnection?.secret_tail
                          ? `•••• •••• ${persistedConnection.secret_tail}`
                          : "未保存密钥"}
                      </strong>
                      <small>
                        明文只发送到 FastAPI 并加密保存；页面只读取密钥尾号。
                      </small>
                      <div>
                        <input
                          type="password"
                          value={apiKey}
                          autoComplete="new-password"
                          aria-label="新 API Key"
                          placeholder="输入或替换密钥"
                          onChange={(event) => {
                            setApiKey(event.target.value);
                            setClearSecret(false);
                            invalidateTest();
                          }}
                        />
                        <button
                          className="button ghost-inline"
                          type="button"
                          onClick={() => {
                            setApiKey("");
                            setClearSecret(true);
                            invalidateTest();
                          }}
                        >
                          清除
                        </button>
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="admin-form-grid">
                    <label className="wide">
                      <span>绝对可执行路径</span>
                      <input
                        value={executablePath}
                        onChange={(event) => {
                          setExecutablePath(event.target.value);
                          invalidateTest();
                        }}
                        placeholder="/absolute/path/to/cli"
                        spellCheck={false}
                      />
                    </label>
                    <label>
                      <span>版本</span>
                      <input
                        value={testResult.version ?? "尚未探测"}
                        readOnly
                      />
                    </label>
                    <label>
                      <span>认证状态</span>
                      <input
                        value={testResult.authStatus ?? "unknown"}
                        readOnly
                      />
                    </label>
                  </div>
                )}
              </div>

              <div className="admin-form-section">
                <div className="section-heading">
                  <div>
                    <p className="eyebrow">模型目录</p>
                    <h2>模型与自定义 ID</h2>
                  </div>
                  <span className="status-chip">
                    {modelOptions.length} 个可选项
                  </span>
                </div>
                <div className="model-tools">
                  <label>
                    <span>当前模型</span>
                    <select
                      value={modelId}
                      onChange={(event) => {
                        const value = event.target.value;
                        setModelId(value);
                        setInstances((current) =>
                          current.map((item) => ({ ...item, modelId: value })),
                        );
                        invalidateTest();
                      }}
                    >
                      {modelOptions.map((item) => (
                        <option key={item} value={item}>
                          {item}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label>
                    <span>自定义模型 ID</span>
                    <input
                      value={customModelId}
                      onChange={(event) => setCustomModelId(event.target.value)}
                      placeholder="provider/model-id"
                      disabled={
                        mode === "cli" &&
                        !(selectedDefinition as CliRuntimeDefinition)
                          .supports_custom_model
                      }
                    />
                  </label>
                </div>
                {customModelId ? (
                  <button
                    className="button secondary lineup-use-model"
                    type="button"
                    onClick={() => {
                      if (
                        !/^[A-Za-z0-9][A-Za-z0-9._:/-]{1,127}$/.test(
                          customModelId,
                        )
                      ) {
                        setStatus("自定义模型 ID 格式无效");
                        return;
                      }
                      setModelId(customModelId);
                      setInstances((current) =>
                        current.map((item) => ({
                          ...item,
                          modelId: customModelId,
                        })),
                      );
                      invalidateTest();
                    }}
                  >
                    使用自定义模型
                  </button>
                ) : null}
              </div>

              <div className="admin-form-section">
                <div className="section-heading">
                  <div>
                    <p className="eyebrow">连接验证</p>
                    <h2>真实后台测试</h2>
                  </div>
                  <button
                    className="button secondary"
                    disabled={
                      testResult.status === "running" ||
                      !modelId ||
                      (mode === "cli" ? !executablePath : !baseUrl)
                    }
                    type="button"
                    onClick={() => void testConnection()}
                  >
                    {testResult.status === "running"
                      ? "测试中…"
                      : testResult.status === "failed"
                        ? "重试"
                        : "测试连接"}
                  </button>
                </div>
                <p
                  className={`inline-callout ${testResult.status === "failed" ? "danger" : ""}`}
                  role="status"
                >
                  {testResult.status === "passed"
                    ? `测试通过${testResult.latencyMs ? ` · ${testResult.latencyMs} ms` : ""}。`
                    : testResult.status === "failed"
                      ? `测试失败：${testResult.errorCode ?? "unknown_error"}。`
                      : mode === "cli"
                        ? "测试文件权限、版本、CLI 自身认证和模型目录；不会执行任意命令。"
                        : "测试端点、认证、所选模型和最小 JSON Schema 输出。"}
                </p>
              </div>

              <div className="admin-form-section">
                <div className="section-heading">
                  <div>
                    <p className="eyebrow">实例管理</p>
                    <h2>{instances.length} / 3 个实例</h2>
                  </div>
                  <button
                    className="button secondary"
                    disabled={instances.length >= 3}
                    type="button"
                    onClick={() => {
                      setInstances((current) =>
                        addInstanceDraft(
                          current,
                          selectedDefinition.display_name,
                          modelId,
                        ),
                      );
                    }}
                  >
                    {instances.length >= 3 ? "已达上限" : "新增实例"}
                  </button>
                </div>
                <div className="lineup-instance-list">
                  {instances.map((instance, index) => (
                    <article
                      className="instance-card"
                      key={instance.id ?? instance.instanceNumber}
                    >
                      <header>
                        <div>
                          <strong>{instance.nickname}</strong>
                          <small>
                            实例{" "}
                            {String(instance.instanceNumber).padStart(2, "0")}
                          </small>
                        </div>
                        <div className="lineup-instance-actions">
                          <label className="switch-row">
                            <input
                              type="checkbox"
                              checked={instance.enabled}
                              disabled={!qualified}
                              onChange={(event) =>
                                updateInstance(index, {
                                  enabled: event.target.checked,
                                })
                              }
                            />
                            <span>启用</span>
                          </label>
                          <button
                            className="text-danger"
                            type="button"
                            onClick={() => {
                              if (instance.id) {
                                setRetiredInstanceIds((current) => [
                                  ...new Set([
                                    ...current,
                                    instance.id as string,
                                  ]),
                                ]);
                              }
                              setInstances((current) =>
                                current.filter(
                                  (_, itemIndex) => itemIndex !== index,
                                ),
                              );
                            }}
                          >
                            退役
                          </button>
                        </div>
                      </header>
                      <div className="admin-form-grid three">
                        <label>
                          <span>实例昵称</span>
                          <input
                            value={instance.nickname}
                            onChange={(event) =>
                              updateInstance(index, {
                                nickname: event.target.value,
                              })
                            }
                          />
                        </label>
                        <label>
                          <span>模型</span>
                          <select
                            value={instance.modelId}
                            onChange={(event) => {
                              updateInstance(index, {
                                modelId: event.target.value,
                              });
                              invalidateTest();
                            }}
                          >
                            {modelOptions.map((item) => (
                              <option key={item} value={item}>
                                {item}
                              </option>
                            ))}
                          </select>
                        </label>
                        <label>
                          <span>推理强度</span>
                          <select
                            value={instance.reasoningLevel}
                            onChange={(event) =>
                              updateInstance(index, {
                                reasoningLevel: event.target.value,
                              })
                            }
                          >
                            <option value="low">低</option>
                            <option value="medium">中</option>
                            <option value="high">高</option>
                          </select>
                        </label>
                        <label>
                          <span>超时（秒）</span>
                          <input
                            type="number"
                            min="1"
                            max="900"
                            value={instance.timeoutSeconds}
                            onChange={(event) =>
                              updateInstance(index, {
                                timeoutSeconds: Number(event.target.value),
                              })
                            }
                          />
                        </label>
                        <label>
                          <span>并发</span>
                          <input
                            type="number"
                            min="1"
                            max="16"
                            value={instance.maxConcurrency}
                            onChange={(event) =>
                              updateInstance(index, {
                                maxConcurrency: Number(event.target.value),
                              })
                            }
                          />
                        </label>
                        <label>
                          <span>Prompt 版本</span>
                          <input
                            value={instance.promptVersion}
                            onChange={(event) =>
                              updateInstance(index, {
                                promptVersion: event.target.value,
                              })
                            }
                          />
                        </label>
                      </div>
                    </article>
                  ))}
                </div>
              </div>
            </>
          ) : (
            <div className="lineup-empty">
              <h2>目录尚未加载</h2>
              <p>检查后台连接后重试。</p>
            </div>
          )}
        </section>
      </div>

      <footer className="admin-savebar">
        <div>
          <span
            className={
              status.startsWith("已保存") || status.startsWith("已加载")
                ? "status-chip"
                : "status-chip warning"
            }
          >
            {status}
          </span>
          <p>配置按版本保存；Worker 只读取圆桌启动时冻结的已启用连接与实例。</p>
        </div>
        <div>
          {persistedProvider ? (
            <button
              className="button danger"
              disabled={loading || saving}
              type="button"
              onClick={() => void deleteConfiguration()}
            >
              删除配置
            </button>
          ) : null}
          <button
            className="button secondary"
            disabled={loading || saving}
            type="button"
            onClick={() =>
              selectedDefinition && applySelection(mode, selectedDefinition.key)
            }
          >
            撤销修改
          </button>
          <button
            className="button primary inline"
            disabled={loading || saving || !selectedDefinition}
            type="button"
            onClick={() => void saveConfiguration()}
          >
            {saving ? "保存中…" : "保存配置"}
          </button>
        </div>
      </footer>
    </main>
  );
}
