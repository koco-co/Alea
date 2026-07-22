import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Alea",
  description: "竞彩足球 AI 预测平台",
};

// The middleware attaches a request-scoped CSP nonce. Keep the shell dynamic so
// Next can propagate that nonce to its bootstrap scripts instead of serving a
// cached static document whose scripts the production CSP blocks.
export const dynamic = "force-dynamic";

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}
