import { proxyAdminApiRequest } from "@/lib/admin-api";

export const dynamic = "force-dynamic";

export async function GET(request: Request): Promise<Response> {
  return proxyAdminApiRequest(request, "/v1/admin/roundtables");
}

export async function POST(request: Request): Promise<Response> {
  return proxyAdminApiRequest(request, "/v1/admin/roundtables");
}
