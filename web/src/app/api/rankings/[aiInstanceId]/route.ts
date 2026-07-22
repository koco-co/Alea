import { proxyAuthenticatedApiRequest } from "@/lib/alea-api";

export const dynamic = "force-dynamic";

export async function GET(
  request: Request,
  context: { params: Promise<{ aiInstanceId: string }> },
): Promise<Response> {
  const { aiInstanceId } = await context.params;
  return proxyAuthenticatedApiRequest(
    request,
    `/v1/rankings/${encodeURIComponent(aiInstanceId)}`,
  );
}
