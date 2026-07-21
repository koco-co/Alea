import { proxyAdminApiRequest } from "@/lib/admin-api";

export const dynamic = "force-dynamic";

export async function GET(request: Request): Promise<Response> {
  const query = new URL(request.url).search;
  return proxyAdminApiRequest(request, `/v1/matches${query}`);
}
