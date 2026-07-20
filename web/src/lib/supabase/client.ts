"use client";

import { createBrowserClient } from "@supabase/ssr";

import { requireSupabasePublicConfig } from "./env";

let browserClient: ReturnType<typeof createBrowserClient> | undefined;

export function createClient() {
  const config = requireSupabasePublicConfig();
  browserClient ??= createBrowserClient(config.url, config.publishableKey);
  return browserClient;
}
