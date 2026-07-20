"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";

import type { AppRole } from "@/lib/supabase/access";

const userNotices = [
  { id: "prediction", title: "世界杯决赛推演已发布", meta: "西班牙 vs 阿根廷 · 12 分钟前", href: "/console/predictions/n8c4-02" },
  { id: "review", title: "你关注的复盘已发布", meta: "法国 vs 巴西 · 昨天 22:18", href: "/console/reviews/review-20260718" },
];

const adminNotices = [
  { id: "sync", title: "赛果来源存在冲突", meta: "FIFA Match 104 · 等待人工确认", href: "/console/admin/sync" },
  { id: "method", title: "新方法论提议待审", meta: "雨战总进球修正 · 3 场证据", href: "/console/admin/settings/methodology" },
];

export function NotificationCenter({ role }: { role: AppRole }) {
  const [open, setOpen] = useState(false);
  const [read, setRead] = useState<string[]>([]);
  const root = useRef<HTMLDivElement>(null);
  const notices = role === "admin" ? [...adminNotices, ...userNotices] : userNotices;
  const unread = notices.filter((notice) => !read.includes(notice.id)).length;

  useEffect(() => {
    const close = (event: MouseEvent) => {
      if (!root.current?.contains(event.target as Node)) setOpen(false);
    };
    const escape = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", close);
    document.addEventListener("keydown", escape);
    return () => {
      document.removeEventListener("mousedown", close);
      document.removeEventListener("keydown", escape);
    };
  }, []);

  return (
    <div className="notification-root" ref={root}>
      <button className="icon-button notification-trigger" type="button" aria-label={`消息中心，${unread} 条未读`} aria-expanded={open} onClick={() => setOpen((value) => !value)}>
        <img src="/assets/icons/bell.svg" alt="" />
        {unread ? <span className="notification-badge">{unread}</span> : null}
      </button>
      {open ? (
        <section className="notification-popover" role="dialog" aria-label="消息中心">
          <header><div><p className="eyebrow">消息中心</p><h2>站内通知</h2></div><button type="button" onClick={() => setRead(notices.map((notice) => notice.id))}>全部已读</button></header>
          <div className="notification-list">
            {notices.map((notice) => (
              <Link className={read.includes(notice.id) ? "notification-item read" : "notification-item"} href={notice.href} key={notice.id} onClick={() => { setRead((items) => [...new Set([...items, notice.id])]); setOpen(false); }}>
                <span className="notification-dot" />
                <span><strong>{notice.title}</strong><small>{notice.meta}</small></span>
              </Link>
            ))}
          </div>
          <Link className="notification-footer" href="/console/settings" onClick={() => setOpen(false)}>通知偏好与我的关注 →</Link>
        </section>
      ) : null}
    </div>
  );
}
