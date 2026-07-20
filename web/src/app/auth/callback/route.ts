import { type NextRequest, NextResponse } from "next/server";

import { getSupabasePublicConfig } from "@/lib/supabase/env";
import { createClient } from "@/lib/supabase/server";

function safeNext(value: string | null): string {
  return value?.startsWith("/") && !value.startsWith("//") ? value : "/console/predictions";
}

export async function GET(request: NextRequest) {
  const code = request.nextUrl.searchParams.get("code");
  if (!code || !getSupabasePublicConfig()) {
    return NextResponse.redirect(new URL("/login?error=invalid_callback", request.url));
  }
  const supabase = await createClient();
  const { data, error } = await supabase.auth.exchangeCodeForSession(code);
  if (error || !data.user) {
    return NextResponse.redirect(new URL("/login?error=callback_failed", request.url));
  }
  const { data: profile } = await supabase
    .from("profiles")
    .select("status")
    .eq("id", data.user.id)
    .maybeSingle();
  const destination = profile?.status === "active" ? safeNext(request.nextUrl.searchParams.get("next")) : "/consent";
  return NextResponse.redirect(new URL(destination, request.url));
}
