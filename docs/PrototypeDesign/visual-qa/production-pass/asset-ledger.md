# Alea OpenDesign 资产台账

核对日期：2026-07-19

运行目录：`docs/PrototypeDesign/open-design/assets/`

状态定义：

- `通过`：来源 / 生成方式、用途、路径、尺寸、视觉回退和本轮渲染均已记录。
- `内部原型可用`：文件与视觉渲染正常，但商标许可或原始下载记录不足，不可外推为商业发布许可。
- `缺失态`：PRD 需要该类资料，但可信来源未接入；页面必须显示文字缺失态，不放占位头像或假队徽。

| 资产 | 来源 / 许可与用途 | 路径 | 尺寸 / Hash | 展示与回退 | 本轮结果 |
|---|---|---|---|---|---|
| Alea 组合标 | 仓库既有原创品牌资产；用于全站页头 | `assets/brand/alea-lockup.png` | 1242×456；SHA-256 `12708f04…3d740` | 桌面 36px、移动 30px 高；保持透明边距，不以文字首字母替代 | 通过；34 路由双端均完整 |
| Alea 图形标 | 仓库既有原创品牌资产；票面、头像与小尺寸身份 | `assets/brand/alea-mark.png` | 1254×1254；`fe46532b…bf0e` | 1:1 透明底；图像失败判视觉失败 | 通过 |
| 决赛主视觉 v2 | 2026-07-19 使用内置生成工具创建；无真实人物肖像、足协徽章或赞助标识；仅用于原型氛围 | `assets/hero-spain-argentina-final-v2.png` | 1672×941；`e82aad7b…57d1` | 16:9；桌面保留左侧文案负空间，移动优先保留球场主体 | 通过；营销页双端已检查 |
| 西班牙国旗 | Wikimedia Commons `Flag of Spain.svg`；public domain / CC0；用于国家身份，不冒充 RFEF 队徽 | `assets/flag-spain.png` | 960×640；`6ff37f9d…4100` | 保持 3:2；详情页明确写“国旗” | 通过 |
| 阿根廷国旗 | Wikimedia Commons `Flag of Argentina.svg`；public domain；用于国家身份，不冒充 AFA 队徽 | `assets/flag-argentina.png` | 960×600；`575d9fa0…0510` | 保持 8:5；详情页明确写“国旗” | 通过 |
| OpenAI 标识 | 既有 SVG，已按 [OpenAI Brand](https://openai.com/brand/) 当前黑色标识指导校正；用于厂商身份；精确下载文件的原始记录仍不完整 | `assets/vendors/openai.svg` | SVG；`6fe96414…a0f1a7` | 统一 vendor 容器；无文字字母球回退 | 内部原型可用；商标授权待确认 |
| Anthropic 标识 | 2026-07-19 从 [Anthropic Press Kit](https://www.anthropic.com/press-kit) 取得官方 Symbol；用于厂商身份 | `assets/vendors/anthropic.svg` | SVG；`d5591888…0a03bb` | 保持原始比例与光学留白；不得用普通 “AI/Claude” 文字冒充字标 | 来源通过；商标授权待确认 |
| DeepSeek 标识 | OpenDesign 项目既有 SVG；原始下载记录与商标边界未保存 | `assets/vendors/deepseek.svg` | SVG；`5d2c1b23…c1d0` | 统一 vendor 容器 | 内部原型可用；外部许可待确认 |
| Gemini 标识 | OpenDesign 项目既有 SVG；原始下载记录与商标边界未保存 | `assets/vendors/gemini.svg` | SVG；`5f9dac87…2f41` | 统一 vendor 容器 | 内部原型可用；外部许可待确认 |
| Kimi 标识 | 2026-07-19 从 [Kimi Branding Guide](https://moonshotai.github.io/Branding-Guide/) 取得官方圆角图标；用于厂商身份 | `assets/vendors/kimi.png` | 1024×1024；`61bc910b…9160d` | 1:1；统一 vendor 容器，不作为人物头像 | 来源与分辨率通过；商标授权待确认 |
| Qwen 标识 | OpenDesign 项目既有 SVG；身份与 Qwen 官方组织一致，但文件无原始下载元数据 | `assets/vendors/qwen.svg` | SVG；`189f77fb…57d2` | 统一 vendor 容器；不以阿里云通用标识冒充 | 内部原型可用；外部许可待确认 |
| Lucide Copy | Lucide `copy`，ISC License；用于方案卡复制 | `assets/icons/lucide-copy.svg` | 24×24 viewBox；`ea80e566…5718` | 20px 图形 / 44px 热区；必须保留 `aria-label` | 通过；可用与禁用态已检查 |
| Lucide Download | Lucide `download`，ISC License；用于 PNG 下载 | `assets/icons/lucide-download.svg` | 24×24 viewBox；`3daeee13…39d` | 20px 图形 / 44px 热区；必须保留禁用原因 | 通过；可用与禁用态已检查 |
| Lucide User Round | Lucide v0.468.0 `user-round`，ISC License；用于头像加载失败 / 无头像回退 | `assets/icons/lucide-user-round.svg` | 24×24 viewBox；`d7390d37…474c3` | 只作为语义回退图标，不冒充人物或账户首字母 | 通过；默认、失败与无头像状态已检查 |
| Lucide Bell / Star | Lucide v0.468.0 `bell`、`star`，ISC License；用于消息与关注空态 | `assets/icons/lucide-bell.svg`、`lucide-star.svg` | 24×24 viewBox；`129a018b…ea13`、`8169933b…ce8b` | 空态语义图标，不使用 emoji / 文字符号 | 通过；桌面与移动空态已检查 |
| 球员 / 教练 / 裁判头像 | 可信人物源尚未接入；不得随机借用照片、姓名或剪影冒充资料 | 无运行资产 | 不适用 | 页面使用文字缺失卡，不显示占位人物图 | 缺失态通过 |
| 足协 / 国家队徽 | 未取得 RFEF / AFA 可追溯资产与许可；国旗不可冒充队徽 | 无运行资产 | 不适用 | 身份页明确“只读身份、不以国旗冒充足协队徽” | 缺失态通过 |
| 用户账户头像 · 林舟 | 2026-07-19 使用内置生成工具创建的虚构账户头像；只用于 Alea 原型，不对应真实人物 | `assets/accounts/lin-zhou.png` | 512×512；`0dc01ad2…fccc3a` | 1:1；页头 44px、摘要 48–56px、账户页 88–96px；失败回退到 User Round，不显示文字首字 | 通过；默认、上传成功、加载失败、无头像四态已检查 |
| 管理员账户头像 | 2026-07-19 使用内置生成工具创建的虚构管理员头像；只用于 Alea 原型，不对应真实人物 | `assets/accounts/admin.png` | 512×512；`1a880afb…2f616` | 1:1；用户壳不得出现管理员身份；失败回退规则与用户头像一致 | 通过；管理壳桌面与移动已检查 |

## 资产验收结论

- 运行资源引用检查：通过；未发现 broken image。
- 最终 34 个正式路由在 1440×900 与 390×844 共 68 张新截图中均已重新渲染；5 张桌面和 5 张移动联系表已人工打开检查。
- 真实赛事身份：只使用可追溯国旗，未伪造足协队徽、球员、教练或裁判资产。
- 账户身份：两个虚构账户均使用 512×512 本地生成栅格头像，四种头像状态有明确名称、回退与真实上传交互证据；文字首字头像已清零。
- AI 厂商标识：Anthropic 与 Kimi 已补齐官方来源，OpenAI 已按官方品牌指导校正；DeepSeek、Gemini、Qwen 与 OpenAI 精确文件下载记录仍不完整，且所有厂商标识的商业商标授权仍需产品方确认。当前仅声明内部原型可用。

## Next.js 前端复用（2026-07-20）

| 前端资产集合 | 来源 / 用途 | 前端路径 | 回退 | 本轮结果 |
|---|---|---|---|---|
| Alea 组合标、两队国旗、6 个 AI 厂商标识、Copy / Download / Bell / User Round 图标 | 机械复制自上表已登记的 OpenDesign 资产；用于营销、推演、赛程、方案计算器与全局导航 | `web/public/assets/brand/`、`teams/`、`vendors/`、`icons/` | 品牌与身份资产加载失败时不以文字、emoji 或手绘图形冒充；账户使用 User Round 语义图标 | 静态资源引用检查通过；受执行环境禁止监听端口影响，Next.js 新页面的浏览器渲染仍待双视口复核 |
