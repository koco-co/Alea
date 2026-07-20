import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Alea",
  description: "竞彩足球 AI 预测平台",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}
