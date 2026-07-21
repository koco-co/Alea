import { createServerClient } from "@supabase/ssr";
import { type NextRequest, NextResponse } from "next/server";

import { contentSecurityPolicy } from "@/lib/security";

import { getSupabasePublicConfig } from "./env";

const AUTH_ROUTES = new Set(["/login", "/signup", "/forgot"]);

function safeNext(value: string | null, fallback: string): string {
  return value?.startsWith("/") && !value.startsWith("//") ? value : fallback;
}

export async function updateSession(
  request: NextRequest,
): Promise<NextResponse> {
  const nonce = crypto.randomUUID().replaceAll("-", "");
  const requestHeaders = new Headers(request.headers);
  requestHeaders.set("x-nonce", nonce);
  let response = NextResponse.next({ request: { headers: requestHeaders } });
  const config = getSupabasePublicConfig();
  const demoRole =
    process.env.NODE_ENV !== "production"
      ? process.env.ALEA_DEMO_ROLE
      : undefined;
  let user: { id: string } | null =
    demoRole === "user" || demoRole === "admin" ? { id: "local-demo" } : null;
  let role: "user" | "admin" = demoRole === "admin" ? "admin" : "user";
  let status: "active" | "pending_consent" | "disabled" = user
    ? "active"
    : "pending_consent";

  if (config && !user) {
    const supabase = createServerClient(config.url, config.publishableKey, {
      cookies: {
        getAll: () => request.cookies.getAll(),
        setAll: (cookiesToSet) => {
          for (const { name, value } of cookiesToSet)
            request.cookies.set(name, value);
          response = NextResponse.next({
            request: { headers: requestHeaders },
          });
          for (const { name, value, options } of cookiesToSet) {
            response.cookies.set(name, value, options);
          }
        },
      },
    });
    const result = await supabase.auth.getUser();
    user = result.data.user;
    if (user) {
      const { data: profile } = await supabase
        .from("profiles")
        .select("role,status")
        .eq("id", user.id)
        .maybeSingle();
      status =
        profile?.status === "active" || profile?.status === "disabled"
          ? profile.status
          : "pending_consent";
      role = profile?.role === "admin" ? "admin" : "user";
    }
  }

  const path = request.nextUrl.pathname;
  if (!user && path.startsWith("/console")) {
    const loginUrl = new URL("/login", request.url);
    loginUrl.searchParams.set("next", `${path}${request.nextUrl.search}`);
    return secureRedirect(loginUrl, nonce, response);
  }
  if (!user && path === "/consent") {
    return secureRedirect(
      new URL("/login?next=/consent", request.url),
      nonce,
      response,
    );
  }
  if (
    user &&
    status === "pending_consent" &&
    path !== "/consent" &&
    !path.startsWith("/api/auth/")
  ) {
    return secureRedirect(new URL("/consent", request.url), nonce, response);
  }
  if (user && status === "disabled" && path.startsWith("/console")) {
    return secureRedirect(
      new URL("/login?error=account_disabled", request.url),
      nonce,
      response,
    );
  }
  if (
    user &&
    status === "active" &&
    role !== "admin" &&
    path.startsWith("/console/admin")
  ) {
    return secureRedirect(
      new URL("/console?error=forbidden", request.url),
      nonce,
      response,
    );
  }
  if (user && status === "active" && AUTH_ROUTES.has(path)) {
    return secureRedirect(
      new URL(
        safeNext(
          request.nextUrl.searchParams.get("next"),
          "/console/predictions",
        ),
        request.url,
      ),
      nonce,
      response,
    );
  }
  applySecurityHeaders(response, nonce);
  return response;
}

function secureRedirect(
  url: URL,
  nonce: string,
  source?: NextResponse,
): NextResponse {
  const response = NextResponse.redirect(url);
  for (const cookie of source?.cookies.getAll() ?? [])
    response.cookies.set(cookie);
  applySecurityHeaders(response, nonce);
  return response;
}

function applySecurityHeaders(response: NextResponse, nonce: string): void {
  response.headers.set(
    "Content-Security-Policy",
    contentSecurityPolicy(nonce, getSupabasePublicConfig()?.url),
  );
  response.headers.set("Referrer-Policy", "strict-origin-when-cross-origin");
  response.headers.set("X-Content-Type-Options", "nosniff");
  response.headers.set("X-Frame-Options", "DENY");
  response.headers.set(
    "Permissions-Policy",
    "camera=(), microphone=(), geolocation=()",
  );
}
