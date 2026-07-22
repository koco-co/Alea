import { proxyAdminApiRequest } from "@/lib/admin-api";

export const dynamic = "force-dynamic";

export async function GET(request: Request): Promise<Response> {
  const url = new URL(request.url);
  const query = url.search;
  return proxyAdminApiRequest(request, `/v1/admin/users${query}`);
}
