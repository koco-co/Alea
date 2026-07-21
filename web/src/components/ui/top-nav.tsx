"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { NotificationCenter } from "@/components/ui/notification-center";
import type { AppRole } from "@/lib/supabase/access";

const modules = [
  ["每日总览", "今日简报", "/console"],
  ["竞猜赛程", "今日竞彩", "/console/fixtures"],
  ["太玄问机", "模型推演", "/console/predictions"],
  ["预测排行", "谁最准", "/console/rankings"],
  ["盈亏账本", "模拟操盘", "/console/pnl"],
  ["赛后复盘", "败因沉淀", "/console/reviews"],
  ["竞彩方案", "配票出图", "/console/calculator"],
  ["赛事资料", "资料档案", "/console/wiki"],
] as const;

export function TopNav({
  role,
  email,
}: {
  role: AppRole;
  email: string | null;
}) {
  const path = usePathname();
  return <TopNavView role={role} email={email} path={path} />;
}

export function TopNavView({
  role,
  email,
  path,
}: {
  role: AppRole;
  email: string | null;
  path: string;
}) {
  const isAdminRoute = path.startsWith("/console/admin");
  return (
    <>
      <header className={isAdminRoute ? "topbar admin-topbar" : "topbar"}>
        <div className="topbar-main">
          <Link
            className="brand compact"
            href="/console"
            aria-label="Alea 每日总览"
          >
            <img src="/assets/brand/alea-lockup.png" alt="Alea" />
          </Link>
          <nav className="module-nav" aria-label="控制台主导航">
            {modules.map(([label, subtitle, href]) => {
              const active =
                href === "/console" ? path === href : path.startsWith(href);
              return (
                <Link
                  key={href}
                  href={href}
                  className={active ? "nav-link active" : "nav-link"}
                >
                  <span>{label}</span>
                  <small>{subtitle}</small>
                </Link>
              );
            })}
          </nav>
          <div className="account-nav">
            {role === "admin" ? (
              <Link className="admin-link" href="/console/admin/lineup">
                系统管理
              </Link>
            ) : null}
            <NotificationCenter role={role} />
            <Link
              className="avatar-button"
              href="/console/settings"
              aria-label={`账户设置 ${email ?? "用户"}`}
            >
              <img src="/assets/icons/user-round.svg" alt="" />
            </Link>
          </div>
        </div>
      </header>
      {!isAdminRoute ? (
        <nav className="mobile-module-nav" aria-label="移动端用户导航">
          {[modules[0], modules[2], modules[1], modules[6]].map(
            ([label, , href]) => {
              const active =
                href === "/console" ? path === href : path.startsWith(href);
              return (
                <Link
                  key={href}
                  href={href}
                  className={active ? "active" : undefined}
                  aria-current={active ? "page" : undefined}
                >
                  {label === "太玄问机"
                    ? "预测"
                    : label === "竞猜赛程"
                      ? "赛程"
                      : label === "竞彩方案"
                        ? "算票"
                        : "总览"}
                </Link>
              );
            },
          )}
        </nav>
      ) : null}
    </>
  );
}
