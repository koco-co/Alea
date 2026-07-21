import { describe, expect, test } from "bun:test";

import {
  contentSecurityPolicy,
  redactSensitive,
  sanitizeMarkdown,
} from "./security";

describe("web security helpers", () => {
  test("markdown escapes HTML and drops unsafe protocols", () => {
    const result = sanitizeMarkdown(
      "<script>alert(1)</script> [x](javascript:alert(1))",
    );
    expect(result).toContain("&lt;script&gt;");
    expect(result).not.toContain("javascript:");
  });

  test("redaction covers nested headers and token-shaped values", () => {
    const result = redactSensitive({
      Authorization: "Bearer abc",
      nested: "sk-secret1234",
    });
    expect(result).toEqual({
      Authorization: "[REDACTED]",
      nested: "[REDACTED]",
    });
  });

  test("CSP is nonce bound and denies framing", () => {
    const csp = contentSecurityPolicy("nonce-value");
    expect(csp).toContain("'nonce-nonce-value'");
    expect(csp).toContain("frame-ancestors 'none'");
  });

  test("CSP permits the configured local Supabase HTTP and realtime origins", () => {
    const csp = contentSecurityPolicy(
      "nonce-value",
      "http://127.0.0.1:54321/auth/v1",
    );
    expect(csp).toContain("http://127.0.0.1:54321");
    expect(csp).toContain("ws://127.0.0.1:54321");
    expect(csp).not.toContain("upgrade-insecure-requests");
  });

  test("CSP ignores invalid Supabase protocols", () => {
    const csp = contentSecurityPolicy("nonce-value", "javascript:alert(1)");
    expect(csp).not.toContain("javascript:");
  });
});
