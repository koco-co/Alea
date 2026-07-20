"use client";

import { useState } from "react";

import type { CalculatorMode } from "./match-selector";
import { createTicketCardBlob, TicketCardImage } from "./ticket-card-image";

export function TicketPreview({
  mode,
  multiplier,
}: {
  mode: CalculatorMode;
  multiplier: number;
}) {
  const [message, setMessage] = useState("");
  const ready = mode === "sample";
  async function exportCard(action: "copy" | "download") {
    if (!ready) return;
    try {
      const blob = await createTicketCardBlob(multiplier);
      if (
        action === "copy" &&
        navigator.clipboard &&
        typeof ClipboardItem !== "undefined"
      ) {
        await navigator.clipboard.write([
          new ClipboardItem({ "image/png": blob }),
        ]);
        setMessage("已复制，可粘贴分享");
      } else {
        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = url;
        link.download = "alea-ticket-sample.png";
        link.click();
        URL.revokeObjectURL(url);
        setMessage("方案卡已下载");
      }
    } catch {
      setMessage("当前浏览器无法完成出图，请重试");
    }
  }
  return (
    <section
      className="ticket-preview-panel"
      aria-labelledby="ticket-preview-title"
    >
      <div className="ticket-preview-heading">
        <div>
          <span>步骤 3 · 方案预览</span>
          <h2 id="ticket-preview-title">所见即所得</h2>
        </div>
        <div className="ticket-actions">
          <button
            disabled={!ready}
            onClick={() => exportCard("copy")}
            type="button"
            aria-label="复制方案卡图片"
            title={ready ? "复制方案卡图片" : "待竞彩销售数据确认"}
          >
            <img src="/assets/icons/copy.svg" alt="" />
          </button>
          <button
            disabled={!ready}
            onClick={() => exportCard("download")}
            type="button"
            aria-label="下载方案卡图片"
            title={ready ? "下载方案卡图片" : "待竞彩销售数据确认"}
          >
            <img src="/assets/icons/download.svg" alt="" />
          </button>
        </div>
      </div>
      <TicketCardImage mode={mode} multiplier={multiplier} />
      {message ? (
        <p className="export-message" role="status">
          {message}
        </p>
      ) : null}
    </section>
  );
}
