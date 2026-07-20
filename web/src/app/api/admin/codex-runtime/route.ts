import { getAccessContext } from "@/lib/supabase/access";

export const dynamic = "force-dynamic";

export async function GET(): Promise<Response> {
  const access = await getAccessContext();
  if (!access)
    return Response.json({ error: "authentication_required" }, { status: 401 });
  if (access.role !== "admin") {
    return Response.json({ error: "administrator_required" }, { status: 403 });
  }
  const runnerUrl = process.env.CODEX_RUNNER_URL;
  const token = process.env.ALEA_RUNNER_TOKEN;
  if (!runnerUrl || !token) {
    return Response.json(
      { error: "codex_runner_not_configured" },
      { status: 503 },
    );
  }
  try {
    const [health, models] = await Promise.all([
      fetch(`${runnerUrl.replace(/\/$/, "")}/health`, { cache: "no-store" }),
      fetch(`${runnerUrl.replace(/\/$/, "")}/models`, {
        headers: { "X-Alea-Runner-Token": token },
        cache: "no-store",
      }),
    ]);
    if (!health.ok || !models.ok) throw new Error("runner response rejected");
    return Response.json({
      health: (await health.json()) as unknown,
      catalog: (await models.json()) as unknown,
    });
  } catch {
    return Response.json(
      { error: "codex_runner_unavailable" },
      { status: 503 },
    );
  }
}
