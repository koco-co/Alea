import Link from "next/link";
import { redirect } from "next/navigation";

import { getAccessContext } from "@/lib/supabase/access";

const adminLinks = [
  ["模型阵容", "厂商与实例", "/console/admin/lineup"],
  ["数据管理", "同步与冲突", "/console/admin/sync"],
  ["系统设置", "版本化参数", "/console/admin/settings"],
  ["推演方法", "提议与评审", "/console/admin/settings/methodology"],
  ["用户管理", "权限与状态", "/console/admin/users"],
] as const;

export default async function AdminLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  const access = await getAccessContext();
  if (access?.role !== "admin") redirect("/console");
  return (
    <div className="admin-shell">
      <aside className="admin-sidebar">
        <div>
          <p className="eyebrow">Alea 管理台</p>
          <h2>系统管理</h2>
          <p>配置、事实来源与每次变更都要可追溯。</p>
        </div>
        <nav aria-label="系统管理导航">
          {adminLinks.map(([label, subtitle, href], index) => (
            <Link href={href} key={href}>
              <span>{String(index + 1).padStart(2, "0")}</span>
              <strong>
                {label}
                <small>{subtitle}</small>
              </strong>
            </Link>
          ))}
        </nav>
        <Link className="admin-back" href="/console">
          ← 返回用户控制台
        </Link>
      </aside>
      <div className="admin-content">{children}</div>
    </div>
  );
}
