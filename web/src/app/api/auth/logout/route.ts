import { NextResponse } from "next/server";

import { createClient } from "@/lib/supabase/server";

export async function GET(request: Request): Promise<Response> {
  try {
    await (await createClient()).auth.signOut();
  } catch {
    // The redirect is still safe; middleware will refresh or clear the session.
  }
  const target = new URL("/login", request.url);
  target.searchParams.set("next", "/console/admin/roundtable");
  return NextResponse.redirect(target);
}
