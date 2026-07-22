import "server-only";

import { getAccessContext } from "@/lib/supabase/access";
import { createClient } from "@/lib/supabase/server";

import { isSameOriginRequest } from "./admin-origin";

const ALLOWED_ADMIN_PATH =
  /^(?:\/v1\/admin\/providers(?:\/catalog|\/runtime\/(?:probe|api-test)|\/[0-9a-f-]+(?:\/secret)?|\/[0-9a-f-]+\/instances(?:\/[0-9a-f-]+)?)?|\/v1\/admin\/sync(?:\/import|\/runs(?:\/[0-9a-f-]+\/retry)?)?|\/v1\/admin\/results\/conflicts(?:\/[0-9a-f-]+\/adjudicate)?|\/v1\/admin\/roundtables(?:\/[0-9a-f-]+(?:\/(?:skip-debate|terminate))?)?|\/v1\/admin\/settings\/(?:scoring_rules|ledger_risk|data_automation|user_management|prompts_methodology)|\/v1\/admin\/users(?:\/[0-9a-f-]+\/(?:disable|restore))?|\/v1\/roundtables\/[0-9a-f-]+\/events|\/v1\/matches)$/i;

export async function proxyAdminApiRequest(
  request: Request,
  upstreamPath: string,
): Promise<Response> {
  const upstreamUrl = new URL(upstreamPath, "http://alea.internal");
  if (!ALLOWED_ADMIN_PATH.test(upstreamUrl.pathname)) {
    return Response.json({ error: "unsupported_admin_path" }, { status: 404 });
  }
  const access = await getAccessContext();
  if (!access) {
    return Response.json({ error: "authentication_required" }, { status: 401 });
  }
  if (access.role !== "admin") {
    return Response.json({ error: "administrator_required" }, { status: 403 });
  }
  if (request.method !== "GET") {
    if (!isSameOriginRequest(request)) {
      return Response.json(
        { error: "invalid_request_origin" },
        { status: 403 },
      );
    }
  }
  const internalApiUrl = process.env.INTERNAL_API_URL;
  if (!internalApiUrl) {
    return Response.json(
      { error: "admin_api_not_configured" },
      { status: 503 },
    );
  }
  const supabase = await createClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();
  if (!session?.access_token) {
    return Response.json({ error: "authentication_required" }, { status: 401 });
  }
  const body =
    request.method === "GET" || request.method === "HEAD"
      ? undefined
      : await request.text();
  try {
    const upstream = await fetch(
      `${internalApiUrl.replace(/\/$/, "")}${upstreamUrl.pathname}${upstreamUrl.search}`,
      {
        method: request.method,
        headers: {
          Authorization: `Bearer ${session.access_token}`,
          "Content-Type":
            request.headers.get("content-type") ?? "application/json",
          "X-Request-ID":
            request.headers.get("x-request-id") ?? crypto.randomUUID(),
        },
        body,
        cache: "no-store",
      },
    );
    return new Response(await upstream.arrayBuffer(), {
      status: upstream.status,
      headers: {
        "Content-Type":
          upstream.headers.get("content-type") ?? "application/json",
      },
    });
  } catch {
    return Response.json({ error: "admin_api_unavailable" }, { status: 503 });
  }
}

export const proxyAdminProviderRequest = proxyAdminApiRequest;
