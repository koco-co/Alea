export type FreshnessLevel = "fresh" | "stale" | "expired";

export function getFreshnessLevel(syncedAt: Date, now: Date): FreshnessLevel {
  const ageMinutes = Math.max(0, (now.getTime() - syncedAt.getTime()) / 60_000);
  if (ageMinutes > 24 * 60) return "expired";
  if (ageMinutes > 60) return "stale";
  return "fresh";
}
