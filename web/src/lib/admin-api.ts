import "server-only";

import { getAccessContext } from "@/lib/supabase/access";
import { createClient } from "@/lib/supabase/server";

const ALLOWED_ADMIN_PATH =
  /^(?:\/v1\/admin\/providers(?:\/catalog|\/runtime\/(?:probe|api-test)|\/[0-9a-f-]+(?:\/secret)?|\/[0-9a-f-]+\/instances(?:\/[0-9a-f-]+)?)?|\/v1\/admin\/sync(?:\/import|\/runs(?:\/[0-9a-f-]+\/retry)?)?|\/v1\/admin\/results\/conflicts(?:\/[0-9a-f-]+\/adjudicate)?)$/i;

export async function proxyAdminApiRequest(
  request: Request,
  upstreamPath: string,
): Promise<Response> {
  if (!ALLOWED_ADMIN_PATH.test(upstreamPath)) {
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
    const requestUrl = new URL(request.url);
    if (request.headers.get("origin") !== requestUrl.origin) {
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
      `${internalApiUrl.replace(/\/$/, "")}${upstreamPath}`,
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
