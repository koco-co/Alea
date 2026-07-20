import { describe, expect, test } from "bun:test";

import {
  addInstanceDraft,
  canEnableConnection,
  initialInstances,
  latestConnection,
  nextConnectionVersion,
  type ProviderRecord,
} from "./model";

const provider: ProviderRecord = {
  id: "provider-1",
  key: "deepseek",
  display_name: "DeepSeek",
  family: "openai_compat",
  allowed_api_domains: ["api.deepseek.com"],
  enabled: false,
  connections: [
    {
      id: "connection-1",
      version: 1,
      execution_mode: "api",
      protocol: "openai_compat",
      model_id: "deepseek-chat",
      enabled: false,
      test_status: "failed",
      instances: [],
    },
    {
      id: "connection-2",
      version: 3,
      execution_mode: "api",
      protocol: "openai_compat",
      model_id: "deepseek-reasoner",
      enabled: true,
      test_status: "passed",
      instances: [],
    },
  ],
};

describe("lineup state", () => {
  test("selects the newest immutable connection version", () => {
    expect(latestConnection(provider)?.id).toBe("connection-2");
    expect(nextConnectionVersion(provider)).toBe(4);
    expect(nextConnectionVersion(undefined)).toBe(1);
  });

  test("requires a passed connection and CLI authentication", () => {
    expect(canEnableConnection("api", "passed", "not_required")).toBe(true);
    expect(canEnableConnection("cli", "passed", "authenticated")).toBe(true);
    expect(canEnableConnection("cli", "passed", "unknown")).toBe(false);
    expect(canEnableConnection("api", "failed", "authenticated")).toBe(false);
  });

  test("creates one instance and enforces the three-instance ceiling", () => {
    const first = initialInstances(undefined, "Codex CLI", "default");
    const second = addInstanceDraft(first, "Codex CLI", "default");
    const third = addInstanceDraft(second, "Codex CLI", "default");
    expect(third.map((item) => item.instanceNumber)).toEqual([1, 2, 3]);
    expect(addInstanceDraft(third, "Codex CLI", "default")).toEqual(third);
  });
});
