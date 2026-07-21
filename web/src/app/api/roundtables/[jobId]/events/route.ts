import { proxyAdminApiRequest } from "@/lib/admin-api";

export const dynamic = "force-dynamic";

interface RouteContext {
  params: Promise<{ jobId: string }>;
}

export async function GET(
  request: Request,
  context: RouteContext,
): Promise<Response> {
  const { jobId } = await context.params;
  if (!/^[0-9a-f-]{36}$/i.test(jobId)) {
    return Response.json({ error: "invalid_roundtable_id" }, { status: 400 });
  }
  const query = new URL(request.url).search;
  return proxyAdminApiRequest(
    request,
    `/v1/roundtables/${jobId}/events${query}`,
  );
}
