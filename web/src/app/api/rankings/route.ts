import { proxyAuthenticatedApiRequest } from "@/lib/alea-api";

export const dynamic = "force-dynamic";

export async function GET(request: Request): Promise<Response> {
  const url = new URL(request.url);
  return proxyAuthenticatedApiRequest(request, `/v1/rankings${url.search}`);
}
