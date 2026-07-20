import { proxyAdminApiRequest } from "@/lib/admin-api";

export const dynamic = "force-dynamic";

export function GET(request: Request): Promise<Response> {
  return proxyAdminApiRequest(request, "/v1/admin/sync/runs");
}

export function POST(request: Request): Promise<Response> {
  return proxyAdminApiRequest(request, "/v1/admin/sync");
}
