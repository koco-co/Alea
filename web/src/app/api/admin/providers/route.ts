import { proxyAdminProviderRequest } from "@/lib/admin-api";

export const dynamic = "force-dynamic";

export async function GET(request: Request): Promise<Response> {
  return proxyAdminProviderRequest(request, "/v1/admin/providers");
}
