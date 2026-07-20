import { proxyAdminApiRequest } from "@/lib/admin-api";

export const dynamic = "force-dynamic";

interface RouteContext {
  params: Promise<{ runId: string }>;
}

export async function POST(
  request: Request,
  context: RouteContext,
): Promise<Response> {
  const { runId } = await context.params;
  if (!/^[0-9a-f-]{36}$/i.test(runId)) {
    return Response.json({ error: "invalid_sync_run_id" }, { status: 400 });
  }
  return proxyAdminApiRequest(request, `/v1/admin/sync/runs/${runId}/retry`);
}
