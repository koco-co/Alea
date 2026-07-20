export type ExecutionMode = "api" | "cli";

export interface ConnectionHealth {
  status: "untested" | "probing" | "passed" | "failed";
  detected_version?: string | null;
  auth_status:
    "unknown" | "authenticated" | "unauthenticated" | "not_required" | "error";
  available_models?: string[];
  checked_at?: string | null;
  error_code?: string | null;
}

export interface ProviderInstanceRecord {
  id: string;
  nickname: string;
  instance_number: number;
  model_id: string;
  reasoning_level?: string | null;
  timeout_seconds: number;
  max_concurrency: number;
  prompt_version: string;
  enabled: boolean;
}

export interface ProviderConnectionRecord {
  id: string;
  version: number;
  execution_mode: ExecutionMode | "codex_cli";
  runtime_key?: string | null;
  protocol: string;
  api_url?: string | null;
  executable_path?: string | null;
  model_id: string;
  model_catalog?: string[];
  custom_model_ids?: string[];
  enabled: boolean;
  test_status: string;
  tested_at?: string | null;
  secret_tail?: string | null;
  health?: ConnectionHealth | null;
  instances: ProviderInstanceRecord[];
}

export interface ProviderRecord {
  id: string;
  key: string;
  display_name: string;
  family: string;
  allowed_api_domains: string[];
  enabled: boolean;
  connections: ProviderConnectionRecord[];
}

export interface InstanceDraft {
  id?: string;
  nickname: string;
  instanceNumber: number;
  modelId: string;
  reasoningLevel: string;
  timeoutSeconds: number;
  maxConcurrency: number;
  promptVersion: string;
  enabled: boolean;
}

export function latestConnection(
  provider: ProviderRecord | undefined,
): ProviderConnectionRecord | undefined {
  return provider?.connections.reduce<ProviderConnectionRecord | undefined>(
    (latest, connection) =>
      !latest || connection.version > latest.version ? connection : latest,
    undefined,
  );
}

export function nextConnectionVersion(
  provider: ProviderRecord | undefined,
): number {
  return (latestConnection(provider)?.version ?? 0) + 1;
}

export function canEnableConnection(
  mode: ExecutionMode,
  status: string,
  authStatus: string,
): boolean {
  if (status !== "passed") return false;
  return mode === "api" || authStatus === "authenticated";
}

export function initialInstances(
  provider: ProviderRecord | undefined,
  displayName: string,
  modelId: string,
): InstanceDraft[] {
  const persisted = latestConnection(provider)?.instances ?? [];
  if (persisted.length > 0) {
    return persisted.map((instance) => ({
      id: instance.id,
      nickname: instance.nickname,
      instanceNumber: instance.instance_number,
      modelId: instance.model_id,
      reasoningLevel: instance.reasoning_level ?? "medium",
      timeoutSeconds: instance.timeout_seconds,
      maxConcurrency: instance.max_concurrency,
      promptVersion: instance.prompt_version,
      enabled: instance.enabled,
    }));
  }
  return [
    {
      nickname: `${displayName}-1`,
      instanceNumber: 1,
      modelId,
      reasoningLevel: "medium",
      timeoutSeconds: 120,
      maxConcurrency: 1,
      promptVersion: "prediction-v1",
      enabled: false,
    },
  ];
}

export function addInstanceDraft(
  instances: InstanceDraft[],
  displayName: string,
  modelId: string,
): InstanceDraft[] {
  if (instances.length >= 3) return instances;
  const used = new Set(instances.map((instance) => instance.instanceNumber));
  const instanceNumber = [1, 2, 3].find((value) => !used.has(value)) ?? 3;
  return [
    ...instances,
    {
      nickname: `${displayName}-${instanceNumber}`,
      instanceNumber,
      modelId,
      reasoningLevel: "medium",
      timeoutSeconds: 120,
      maxConcurrency: 1,
      promptVersion: "prediction-v1",
      enabled: false,
    },
  ];
}
