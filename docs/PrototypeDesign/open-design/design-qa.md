# Alea 品牌替换 QA

检查日期：2026-07-18

## 变更范围

- Alea 主标识：营销首页、认证页、用户控制台、预测页、管理后台、算票器、设计系统、页脚、票据预览、导出票据与 favicon。
- AI 厂商标识：DeepSeek、Anthropic / Claude、OpenAI / GPT、Google Gemini、Kimi、Qwen。
- 实例阵容：7 个实例、6 个厂商；DeepSeek 使用 2 个独立实例编号。

## 自动检查

- 7 个 HTML 页面全部使用新的 Alea 品牌资源。
- 6 个厂商 SVG 均可被 XML 解析。
- 4 个 PNG 资源均可读取尺寸与透明通道信息。
- HTML 引用的本地图片资源缺失数：0。
- 旧厂商路径、文本占位、缺失资源降级、黑白反色滤镜、旧字母 A 标识残留：0。

## 视觉检查

- `qa/home.png`：营销首页，7 个模型卡片均显示彩色厂商图标；顶部 Alea 锁定组合在深色背景上清晰可见。
- `qa/admin.png`：管理后台，7 个实例图标完整显示，无 OpenAI 文本占位或 Kimi 缺失占位。
- `qa/console.png`：用户控制台，厂商图标保留品牌色，未被反色滤镜覆盖。
- `qa/calculator.png`：算票器顶部和票据预览均显示新 Alea 标识。
- `qa/logo-application-comparison.png`：选中方案与后台、控制台实际应用的并排对照。

## 导出检查

- 导出票据 SVG 已使用 `assets/brand/alea-mark-export.png`，不再绘制旧字母 A。
- 点击“下载 PNG”后页面返回“PNG 已生成：Alea-方案-N8C4-02”成功提示，控制台无错误。
- in-app Browser 的下载事件监听未返回文件句柄，因此本次未对最终下载文件做像素级复核。
