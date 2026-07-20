import { redirect } from "next/navigation";

import { TopNav } from "@/components/ui/top-nav";
import { getAccessContext } from "@/lib/supabase/access";

export default async function ConsoleLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  const access = await getAccessContext();
  if (!access) redirect("/login?next=/console");
  if (access.status === "pending_consent") redirect("/consent");
  if (access.status === "disabled") redirect("/login?error=account_disabled");
  return (
    <div className="console-shell">
      <TopNav role={access.role} email={access.email} />
      {children}
    </div>
  );
}
