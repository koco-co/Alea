import "server-only";

import { createClient } from "@/lib/supabase/server";

import { isSameOriginRequest } from "./admin-origin";
import { getAccessContext } from "./supabase/access";

const ALLOWED_PATH = /^\/v1\/rankings(?:\/[0-9a-f-]+)?$/i;

export async function proxyAuthenticatedApiRequest(
  request: Request,
  upstreamPath: string,
): Promise<Response> {
  const upstreamUrl = new URL(upstreamPath, "http://alea.internal");
  if (!ALLOWED_PATH.test(upstreamUrl.pathname)) {
    return Response.json({ error: "unsupported_api_path" }, { status: 404 });
  }
  if (request.method !== "GET") {
    return Response.json({ error: "method_not_allowed" }, { status: 405 });
  }
  // Same-origin checks protect state-changing requests. Browser GET requests
  // commonly omit the Origin header, so requiring it here would make a
  // read-only authenticated projection fail in the production shell.
  if (request.method !== "GET" && !isSameOriginRequest(request)) {
    return Response.json({ error: "invalid_request_origin" }, { status: 403 });
  }
  if (!(await getAccessContext())) {
    return Response.json({ error: "authentication_required" }, { status: 401 });
  }
  const internalApiUrl = process.env.INTERNAL_API_URL;
  if (!internalApiUrl) {
    return Response.json({ error: "api_not_configured" }, { status: 503 });
  }
  const supabase = await createClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();
  if (!session?.access_token) {
    return Response.json({ error: "authentication_required" }, { status: 401 });
  }
  try {
    const upstream = await fetch(
      `${internalApiUrl.replace(/\/$/, "")}${upstreamUrl.pathname}${upstreamUrl.search}`,
      {
        method: "GET",
        headers: {
          Authorization: `Bearer ${session.access_token}`,
          "X-Request-ID": crypto.randomUUID(),
        },
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
    return Response.json({ error: "api_unavailable" }, { status: 503 });
  }
}
