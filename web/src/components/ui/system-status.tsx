import Link from "next/link";

import { getFreshnessLevel } from "@/lib/freshness";

export type GlobalDegradation =
  | "backend_unavailable"
  | "ai_unavailable"
  | "data_expired"
  | "data_source_partial";

const STATUS_COPY: Record<GlobalDegradation, { title: string; detail: string; href: string }> = {
  backend_unavailable: {
    title: "服务暂时不可用",
    detail: "已加载内容仍可查看，刷新操作暂时停用。",
    href: "/console",
  },
  ai_unavailable: {
    title: "新预测暂停产出",
    detail: "AI 服务当前不可用；既有推演卡片保持可见。",
    href: "/console/predictions",
  },
  data_expired: {
    title: "数据更新时间超过 24 小时",
    detail: "预测结果可能已过时，涉及赔率的生成与导出操作已停用。",
    href: "/console/fixtures",
  },
  data_source_partial: {
    title: "部分数据源同步延迟",
    detail: "Sporttery 销售数据暂缺，已加载内容保留；涉及赔率的操作暂停。",
    href: "/console/fixtures",
  },
};

export function GlobalStatusBanner({ status }: { status: GlobalDegradation }) {
  const copy = STATUS_COPY[status];
  return (
    <div className={`global-banner ${status}`} role="status">
      <p><strong>{copy.title}</strong> {copy.detail}</p>
      <Link href={copy.href}>查看状态</Link>
    </div>
  );
}

export function FreshnessIndicator({
  syncedAt,
  now,
  isAdmin,
}: {
  syncedAt: Date;
  now: Date;
  isAdmin: boolean;
}) {
  const level = getFreshnessLevel(syncedAt, now);
  const time = new Intl.DateTimeFormat("zh-CN", {
    timeZone: "Asia/Shanghai",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(syncedAt);
  const label =
    level === "fresh"
      ? `已同步 · ${time}`
      : level === "stale"
        ? `数据可能滞后 · ${time}`
        : "数据过期 >24h";
  return (
    <div className={`freshness ${level}`}>
      <span className="pulse" aria-hidden="true" />
      <div><strong>{label}</strong><small>北京时间</small></div>
      {isAdmin ? <Link href="/console/admin/sync">同步设置</Link> : null}
    </div>
  );
}
