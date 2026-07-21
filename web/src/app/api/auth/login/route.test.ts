import { beforeEach, describe, expect, mock, test } from "bun:test";

const signInWithPassword = mock(async (): Promise<{ error: Error | null }> => ({
  error: null,
}));

mock.module("@/lib/supabase/server", () => ({
  createClient: async () => ({
    auth: { signInWithPassword },
  }),
}));

const { POST } = await import("./route");

function loginRequest(body: string) {
  return new Request("http://alea.local/api/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body,
  });
}

describe("POST /api/auth/login", () => {
  beforeEach(() => {
    signInWithPassword.mockReset();
    signInWithPassword.mockResolvedValue({ error: null });
  });

  test("rejects invalid JSON and missing credentials", async () => {
    expect((await POST(loginRequest("{"))).status).toBe(400);
    expect(
      (await POST(loginRequest(JSON.stringify({ email: "" })))).status,
    ).toBe(400);
  });

  test("returns a generic credential error without leaking provider detail", async () => {
    signInWithPassword.mockResolvedValue({
      error: new Error("upstream detail"),
    });
    const response = await POST(
      loginRequest(
        JSON.stringify({
          email: "admin@alea.local",
          password: "incorrect",
        }),
      ),
    );
    expect(response.status).toBe(401);
    expect(await response.json()).toEqual({ error: "邮箱或密码不正确" });
  });

  test("creates a session for valid credentials", async () => {
    const response = await POST(
      loginRequest(
        JSON.stringify({
          email: "admin@alea.local",
          password: "valid-password",
        }),
      ),
    );
    expect(response.status).toBe(200);
    expect(await response.json()).toEqual({ ok: true });
  });
});
