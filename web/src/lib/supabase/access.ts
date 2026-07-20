import { getSupabasePublicConfig } from "./env";
import { createClient } from "./server";

export type AppRole = "user" | "admin";
export type ProfileStatus = "active" | "pending_consent" | "disabled";

export interface AccessContext {
  userId: string;
  email: string | null;
  role: AppRole;
  status: ProfileStatus;
}

export async function getAccessContext(): Promise<AccessContext | null> {
  const demoRole = process.env.ALEA_DEMO_ROLE;
  if (
    process.env.NODE_ENV !== "production" &&
    (demoRole === "user" || demoRole === "admin")
  ) {
    return {
      userId: "local-demo",
      email: `${demoRole}@alea.local`,
      role: demoRole,
      status: "active",
    };
  }
  if (!getSupabasePublicConfig()) return null;
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) return null;
  const { data: profile } = await supabase
    .from("profiles")
    .select("role,status")
    .eq("id", user.id)
    .maybeSingle();
  return {
    userId: user.id,
    email: user.email ?? null,
    role: profile?.role === "admin" ? "admin" : "user",
    status:
      profile?.status === "active" || profile?.status === "disabled"
        ? profile.status
        : "pending_consent",
  };
}
