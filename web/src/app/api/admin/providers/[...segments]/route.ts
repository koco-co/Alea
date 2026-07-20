import { proxyAdminProviderRequest } from "@/lib/admin-api";

export const dynamic = "force-dynamic";

interface RouteContext {
  params: Promise<{ segments: string[] }>;
}

async function proxy(
  request: Request,
  context: RouteContext,
): Promise<Response> {
  const { segments } = await context.params;
  const safeSegments = segments.filter((segment) =>
    /^[A-Za-z0-9_-]+$/.test(segment),
  );
  if (safeSegments.length !== segments.length) {
    return Response.json({ error: "invalid_admin_path" }, { status: 400 });
  }
  return proxyAdminProviderRequest(
    request,
    `/v1/admin/providers/${safeSegments.join("/")}`,
  );
}

export const GET = proxy;
export const POST = proxy;
export const PUT = proxy;
export const DELETE = proxy;
