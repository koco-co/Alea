import { proxyAdminApiRequest } from "@/lib/admin-api";

export const dynamic = "force-dynamic";

interface RouteContext {
  params: Promise<{ group: string }>;
}

const allowedGroups = new Set([
  "scoring_rules",
  "ledger_risk",
  "data_automation",
  "user_management",
  "prompts_methodology",
]);

async function proxy(
  request: Request,
  context: RouteContext,
): Promise<Response> {
  const { group } = await context.params;
  if (!allowedGroups.has(group)) {
    return Response.json({ error: "invalid_settings_group" }, { status: 400 });
  }
  return proxyAdminApiRequest(request, `/v1/admin/settings/${group}`);
}

export const GET = proxy;
export const POST = proxy;
