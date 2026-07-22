import { proxyAdminApiRequest } from "@/lib/admin-api";

export const dynamic = "force-dynamic";

interface RouteContext {
  params: Promise<{ userId: string; action: string }>;
}

async function proxy(
  request: Request,
  context: RouteContext,
): Promise<Response> {
  const { userId, action } = await context.params;
  if (!/^[0-9a-f-]{36}$/i.test(userId) || !/^(disable|restore)$/.test(action)) {
    return Response.json({ error: "invalid_user_action" }, { status: 400 });
  }
  return proxyAdminApiRequest(request, `/v1/admin/users/${userId}/${action}`);
}

export const POST = proxy;
