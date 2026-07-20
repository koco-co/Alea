import type { CalculatorMode } from "./match-selector";

export function TicketCardImage({
  mode,
  multiplier,
}: {
  mode: CalculatorMode;
  multiplier: number;
}) {
  const ready = mode === "sample";
  return (
    <div className="ticket-card-image" id="ticket-card-image">
      <header>
        <div>
          <img src="/assets/brand/alea-lockup.png" alt="Alea" />
          <strong>方案</strong>
        </div>
        <span>{ready ? "交互样例" : "不可生成"}</span>
      </header>
      <p>公证示例 N8C4-02 · AI 推演数据</p>
      <h3>西班牙 vs 阿根廷</h3>
      <small>
        固定 AI 推演：西班牙 2:1 阿根廷，半场 1:0。最终赛果待官方确认。
      </small>
      <dl>
        <div>
          <dt>竞彩场次</dt>
          <dd>{ready ? "非官方参数样例" : "待销售数据确认"}</dd>
        </div>
        <div>
          <dt>玩法 / 选项</dt>
          <dd>{ready ? "胜平负 · 西班牙胜" : "待销售数据确认"}</dd>
        </div>
        <div>
          <dt>过关 / 倍数</dt>
          <dd>{ready ? `单关 · ${multiplier} 倍` : "—"}</dd>
        </div>
        <div>
          <dt>注数 / 金额</dt>
          <dd>{ready ? `1 注 · ${2 * multiplier} 元` : "—"}</dd>
        </div>
        <div>
          <dt>理论回报</dt>
          <dd>{ready ? `${(3.64 * multiplier).toFixed(2)} 元` : "—"}</dd>
        </div>
      </dl>
      <footer>
        <strong>理性研究</strong>
        <p>赔率为生成时的非官方交互样例，不是体彩 SP。</p>
        <p>
          本图非彩票、非投注凭证，不构成投注建议；购彩须本人前往正规实体店，未满
          18 周岁禁止购彩。
        </p>
      </footer>
    </div>
  );
}

export async function createTicketCardBlob(multiplier: number): Promise<Blob> {
  const canvas = document.createElement("canvas");
  canvas.width = 760;
  canvas.height = 1080;
  const context = canvas.getContext("2d");
  if (!context) throw new Error("浏览器不支持方案卡出图");
  context.fillStyle = "#faf9f5";
  context.fillRect(0, 0, canvas.width, canvas.height);
  context.fillStyle = "#181715";
  context.fillRect(0, 0, canvas.width, 220);
  const logo = await loadCanvasImage("/assets/brand/alea-lockup.png");
  context.fillStyle = "#faf9f5";
  context.fillRect(48, 38, 154, 72);
  context.drawImage(logo, 58, 47, 134, 54);
  context.fillStyle = "#faf9f5";
  context.font = "48px Georgia, serif";
  context.fillText("方案", 236, 92);
  context.font = "24px sans-serif";
  context.fillText("交互样例 · 非体彩 SP", 58, 148);
  context.fillStyle = "#141413";
  context.font = "44px Georgia, serif";
  context.fillText("西班牙 vs 阿根廷", 58, 310);
  context.font = "24px sans-serif";
  context.fillStyle = "#6c6a64";
  context.fillText("固定 AI 推演：2 : 1 · 半场 1 : 0", 58, 360);
  const rows = [
    ["玩法 / 选项", "胜平负 · 西班牙胜"],
    ["过关 / 倍数", `单关 · ${multiplier} 倍`],
    ["注数 / 金额", `1 注 · ${2 * multiplier} 元`],
    ["理论回报", `${(3.64 * multiplier).toFixed(2)} 元`],
  ];
  rows.forEach(([label, value], index) => {
    const y = 450 + index * 94;
    context.strokeStyle = "#e6dfd8";
    context.beginPath();
    context.moveTo(58, y + 35);
    context.lineTo(702, y + 35);
    context.stroke();
    context.font = "22px sans-serif";
    context.fillStyle = "#6c6a64";
    context.fillText(label, 58, y);
    context.font = "bold 24px sans-serif";
    context.fillStyle = "#141413";
    context.textAlign = "right";
    context.fillText(value, 702, y);
    context.textAlign = "left";
  });
  context.fillStyle = "#efe9de";
  context.fillRect(40, 840, 680, 188);
  context.font = "bold 22px sans-serif";
  context.fillStyle = "#141413";
  context.fillText("理性研究", 66, 892);
  context.font = "19px sans-serif";
  context.fillStyle = "#3d3d3a";
  context.fillText("赔率为非官方交互样例，不是体彩 SP。", 66, 936);
  context.fillText("本图非彩票、非投注凭证，不构成投注建议。", 66, 972);
  return await new Promise((resolve, reject) =>
    canvas.toBlob(
      (blob) => (blob ? resolve(blob) : reject(new Error("出图失败"))),
      "image/png",
    ),
  );
}

function loadCanvasImage(source: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const image = new Image();
    image.onload = () => resolve(image);
    image.onerror = () => reject(new Error("品牌资产加载失败"));
    image.src = source;
  });
}
