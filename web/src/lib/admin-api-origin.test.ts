import { describe, expect, test } from "bun:test";

import { isSameOriginRequest } from "./admin-origin";

describe("isSameOriginRequest", () => {
  test("accepts the direct request origin", () => {
    const request = new Request("http://127.0.0.1:3002/api/admin/providers", {
      headers: { origin: "http://127.0.0.1:3002" },
    });
    expect(isSameOriginRequest(request)).toBe(true);
  });

  test("accepts a same-origin forwarded host used by the Next dev proxy", () => {
    const request = new Request("http://localhost:3002/api/admin/providers", {
      headers: {
        host: "127.0.0.1:3002",
        origin: "http://127.0.0.1:3002",
        "x-forwarded-proto": "http",
      },
    });
    expect(isSameOriginRequest(request)).toBe(true);
  });

  test("rejects a cross-site origin", () => {
    const request = new Request("https://alea.example/api/admin/providers", {
      headers: {
        host: "alea.example",
        origin: "https://attacker.example",
      },
    });
    expect(isSameOriginRequest(request)).toBe(false);
  });
});
