import { proxyAuthenticatedApiRequest } from "@/lib/alea-api";

export const dynamic = "force-dynamic";

export async function GET(request: Request): Promise<Response> {
  return proxyAuthenticatedApiRequest(
    request,
    `/v1/matches${new URL(request.url).search}`,
  );
}
