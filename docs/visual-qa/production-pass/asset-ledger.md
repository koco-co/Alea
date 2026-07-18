# Alea OpenDesign 资产台账

基线日期：2026-07-19
状态：修改前盘点，来源/许可未核验的资产均不得视为已通过。

| 资产 | 类型 | 真实/虚构 | 来源与许可 | 原始路径 | 原始尺寸 | 展示/裁切 | 降级 | 页面 | 基线结果 |
|---|---|---|---|---|---|---|---|---|---|
| Alea 标识组合 | PNG | 原创品牌 | 仓库现有品牌资产；来源记录待补 | `docs/assets/branding/alea-lockup.png` | 1774×887 | 保持透明边缘，不拉伸 | `alea-mark.png` | 全站 | 待核验 |
| Alea 图形标 | PNG | 原创品牌 | 仓库现有品牌资产；来源记录待补 | `docs/assets/branding/alea-mark.png` | 1254×1254 | 1:1，透明底 | 文字品牌名仅用于无图模式，不作为视觉完成态 | 全站 | 待核验 |
| OpenAI 标识 | SVG | 真实厂商 | OpenDesign 项目现有；官方来源/许可待核验 | OpenDesign `assets/openai.svg` | 矢量 | 统一 24/32/40px 光学尺寸 | 中性厂商占位图，不能用“GPT”字母球 | AI 身份、阵容 | 待核验 |
| Anthropic 标识 | SVG | 真实厂商 | OpenDesign 项目现有；官方来源/许可待核验 | OpenDesign `assets/anthropic.svg` | 矢量 | 核验字标/符号、留白、深浅背景 | 中性厂商占位图，不能用“C”字母球 | AI 身份、阵容 | P0 待核验 |
| Gemini 标识 | SVG | 真实厂商 | OpenDesign 项目现有；官方来源/许可待核验 | OpenDesign `assets/gemini.svg` | 矢量 | 与其他厂商统一光学尺寸 | 中性厂商占位图 | AI 身份、阵容 | 待核验 |
| DeepSeek 标识 | SVG | 真实厂商 | OpenDesign 项目现有；官方来源/许可待核验 | OpenDesign `assets/deepseek.svg` | 矢量 | 与其他厂商统一光学尺寸 | 中性厂商占位图 | AI 身份、阵容 | 待核验 |
| Kimi 标识 | SVG | 真实厂商 | OpenDesign 项目现有；官方来源/许可待核验 | OpenDesign `assets/kimi.svg` | 矢量 | 与其他厂商统一光学尺寸 | 中性厂商占位图 | AI 身份、阵容 | 待核验 |
| Qwen / 阿里云标识 | SVG | 真实厂商 | OpenDesign 项目只有 `alibaba-cloud.svg`，没有独立 Qwen 资产；官方来源/许可待核验 | OpenDesign `assets/alibaba-cloud.svg` | 矢量 | 未核验品牌映射前不得把阿里云图标直接称为 Qwen | 中性厂商缺失态 | AI 身份、阵容 | P0 失败：身份映射未确认 |
| 旧世界杯决赛英雄图 | JPEG | 赛事氛围图 | OpenDesign 项目现有；来源、许可和内容真实性未核验 | OpenDesign `assets/hero-wc-final.jpg` | 2400×1350 | 不再使用 | 无 | 营销页 | 失败：provenance 缺失，待移除引用 |
| 西班牙 vs 阿根廷决赛氛围主视觉 v2 | PNG | 原创生成图 | 2026-07-19 使用内置 ImageGen 生成；无 FIFA/足协/赞助商标识、无真实人物肖像；最终提示词见本轮 Goal 记录 | `docs/assets/branding/hero-spain-argentina-final-v2.png` | 1672×941 | 16:9；左侧文案负空间，移动端优先保留球场右中区域 | 暖纸纯色 + 对阵旗帜 | 营销页 | 原图已检查；待实际页面视觉验收 |
| 澜城/赤湾/北境/海岬队徽 | PNG/SVG | 虚构 | OpenDesign 既有生成/手绘来源不明 | OpenDesign `assets/crest-*` | PNG 512×512 | 统一 64×72 容器 | 无 | 多页面 | 失败：用户明确要求移除玩具式虚构数据 |
| 西班牙国家旗帜 | SVG + PNG | 真实国家 | Wikimedia Commons `Flag of Spain.svg`；public domain/CC0，详情页：https://commons.wikimedia.org/wiki/File:Flag_of_Spain.svg；2026-07-19 下载 | `docs/assets/teams/flag-spain.svg`、`flag-spain.png` | SVG；PNG 960×640 | 作为旗帜横向展示，保持 3:2，不冒充 RFEF 队徽 | 中性“国家队标识待授权”缺失态 | 全站赛事语境 | 已检查原图；待实际页面视觉验收 |
| 阿根廷国家旗帜 | SVG + PNG | 真实国家 | Wikimedia Commons `Flag of Argentina.svg`；public domain，详情页：https://commons.wikimedia.org/wiki/File:Flag_of_Argentina.svg；2026-07-19 下载 | `docs/assets/teams/flag-argentina.svg`、`flag-argentina.png` | SVG；PNG 960×600 | 作为旗帜横向展示，保持 8:5，不冒充 AFA 队徽 | 中性“国家队标识待授权”缺失态 | 全站赛事语境 | 已检查原图；待实际页面视觉验收 |
| 西班牙/阿根廷球员头像 | 栅格照片 | 真实人物 | 待研究可靠来源、许可、拍摄日期 | 待添加 | 待定 | 1:1 或 4:5 统一裁切、光线和背景 | 统一中性人物剪影 PNG | 情报、百科、阵容 | P0 缺失 |
| 教练/裁判头像 | 栅格照片 | 真实人物 | 待研究可靠来源；未确认裁判则必须显示“暂缺” | 待添加 | 待定 | 统一 1:1 裁切 | 中性人物剪影 PNG | 比赛详情、百科 | P0 缺失 |
| 账户头像 | 栅格 | 演示账户 | 待创建一致风格、非真实个人身份 | 待添加 | 建议 ≥256×256 | 1:1 圆形裁切 | 默认/无头像/加载失败三套 PNG | 顶栏、账户设置 | 缺失 |

## 资产规则

- 真实身份资产必须记录可追溯来源、许可/使用边界、抓取日期和用途。
- 原型演示不等于可以把官方赛事、阵容、赛果、赔率或伤停伪装成已核验业务数据。
- 国家队徽与国旗分别表达球队身份和国家身份；不能混为同一组件。
- 不以 emoji、文字首字母、CSS 图形、手绘 SVG 或随机头像作为交付完成态。
- 如果真实人物/裁判来源未确认，使用明确“暂缺”的中性栅格降级，不编造姓名与照片。
