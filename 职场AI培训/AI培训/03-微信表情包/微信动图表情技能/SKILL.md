---
name: 微信动图表情
description: 为微信聊天制作可传播的 GIF 表情。用户提到微信表情包、动图表情、聊天反应图、斗图、打工人自嘲图或想把故事做成 GIF 时使用。技能按“迷你故事脚本 → 原始分镜素材 → GIF 成品”三步工作；除非用户明确要求一口气完成，否则每步结束都停下来请用户确认。所有项目过程文件和成品均使用中文目录与文件名。
compatibility: 仅依赖 WorkBuddy 内置图片生成能力（ImageGen）、安装 Pillow 的 Python 3，以及系统自带中文字体（macOS 的 PingFang / STHeiti，用于脚本叠加文字）。不需要任何外部图片/视频 API 或密钥。
---

# 微信动图表情

目标是做一张在聊天窗口里一眼看懂、愿意转发的表情。动作有铺垫和包袱，文字只做加分，不替代动作。

## 图片生成：只用 WorkBuddy 内置 ImageGen（硬性约束）

本技能的所有画面**只能**用 WorkBuddy **内置图片生成工具 ImageGen**（文生图 / 图生图）产出。

- ✅ 允许：内置 `ImageGen`（若为延迟工具，先用 `ToolSearch` 加载其 schema，再用 `DeferExecuteTool` 调用）。
- ❌ 禁止：任何外部或付费图片/视频 API，包括但不限于 **豆包 / Seedream、MiniMax、火山引擎 Ark、Stability、OpenAI Images、Midjourney** 等；禁止 `requests`/`urllib`/`curl` 调用任何图像生成接口；禁止读取 `MINIMAX_API_KEY`、`ARK_API_KEY`、`API_KEY` 之类环境变量。
- 若内置 ImageGen 不可用，**停下来告知用户**，不要退回外部 API。

技能内的 Python 脚本 `脚本/拼接动图.py` **只做本地图像拼接**（Pillow），不联网、不调用任何 API。

## 项目结构

每个项目在用户指定根目录下新建一个中文名称文件夹，不覆盖旧项目：

```text
<根目录>/<项目名称>/
  迷你故事脚本.md
  生成提示词.txt
  原始素材/连环分镜.png
  分帧图片/第01帧.png …
  最终成品/<项目名称>.gif
  最终成品/首帧预览.png
  质检报告/质量检查.json
  质检报告/动作预览图.png
```

## 三步确认工作流

默认采用“做完一步、让用户看一步”的协作方式。用户没有明确说“直接做完”“一口气完成”“不用确认”时，严格停在每一步末尾，展示结果路径和一句简短说明，并等待确认或修改意见。

若用户明确要求生成完整案例、直接完成或作为自动验收测试，可连续执行三步；在 `迷你故事脚本.md` 首行记录“本次按用户明确授权连续执行”。

### 第一步：迷你故事脚本

创建 `迷你故事脚本.md`，用 4 行写出四格动作：

1. **铺垫**：角色正处于哪种日常情境。
2. **触发**：发生什么让人有反应。
3. **包袱**：动作或表情如何反转，形成笑点。
4. **循环**：最后一格如何自然接回第一格。

再补充“聊天场景、角色、文字设计、画面重点”。角色使用原创形象，不使用真人、知名 IP、品牌或攻击特定人群。自嘲题材用荒诞和反差来表达无奈。

停下来请用户确认故事是否够好笑、文字是否合适。只有确认后才进入第二步。

### 第二步：生成原始素材（内置 ImageGen）

将确认过的完整提示词保存到 `生成提示词.txt`，再用 **WorkBuddy 内置 ImageGen** 生成正方形、规则 2×2 连环分镜，把结果保存为 `原始素材/连环分镜.png`。

调用要点：
- 用 ImageGen 的**文生图**模式，`prompt` 用下面的英文结构化模板，宽高比设为 **1:1（正方形，size 用 `1024x1024`）**；调用时务必加 **`quality: "high"`** 提升清晰度与细节，让线条更精致、画面更高清。
- 生成后把返回的图片保存/复制到 `原始素材/连环分镜.png`（脚本也会自动把 `--source` 复制过去）。
- 一次没达标（缺格、角色不一致、带水印、非纯白底）就重跑 ImageGen，不要将就。

使用**纯白背景**，避免绿幕抠图造成边缘残色；最终 GIF 也使用纯白背景。提示词结构如下：

> ⚠️ **文字不让 AI 画**：ImageGen 渲染中文极不可靠（缺笔画、变形、位置乱），因此提示词里 `Text (verbatim)` 一律写 **NONE**，中文由第三步脚本用系统黑体精准叠加。ImageGen 只负责画角色。

```text
Use case: illustration-story
Asset type: WeChat custom animated sticker storyboard, to be cut into GIF frames
Primary request: original [角色] reacting "[聊天场景]" in four beats: [第1格]; [第2格]; [第3格]; [第4格]. ONLY the character's body is visible — absolutely NO surrounding objects, furniture, bedding, pillows, clothes-as-background, floor, desk, or any scene props; character floats completely ALONE on pure white. CRITICAL: the character must wear COLOURED clothing (e.g. a teal/blue/ochre outfit) — NEVER white or near-white clothes, so the body clearly stands out against the white background.
Style/medium: authentic Studio Ghibli / Hayao Miyazaki hand-painted watercolour animation style — soft painterly textures, warm natural colour palette, gentle hand-drawn ink outlines, charming rounded characters with soulful expressive eyes, dreamy cinematic soft light, high-definition film-quality rendering. IMPORTANT for contrast: the character must use RICH, CLEARLY-COLOURED fills (saturated enough to read against white) with visible defined outlines; the character must be clearly NON-WHITE and NON-PALE so it separates cleanly from the pure white background; NO watercolor bleed, halo, or warm tint spreading into the white space — the background must stay perfectly clean pure white with zero colour contamination.
Composition/framing: four separate character-pose illustrations arranged in a clean, evenly-spaced, well-aligned 2×2 grid layout on ONE flat canvas; each of the four cells is the SAME size and the character sits at roughly the SAME position and SAME scale within its cell (so equal cropping cuts cleanly); ABSOLUTELY NO grid lines, NO panel borders, NO frames, NO dividers, NO gray lines, NO outlines around panels — ONLY solid pure white space between poses; generous white padding so the character never touches any edge or boundary.
Scene/backdrop: PERFECTLY FLAT SOLID PURE WHITE #FFFFFF BACKGROUND IN EVERY PANEL; character floats ALONE on pure white — nothing else visible, no bed, no blanket, no pillow, no furniture, no clothing items, no floor, no desk, NO shadows, NO gradients, NO reflections, NO texture, NO decorative borders, NO panel labels.
Text (verbatim): "NONE"
Constraints: NO text, NO letters, NO Chinese characters anywhere in the image (text is added later by script); each panel is a distinct sequential pose; preserve character identity; same character scale and placement across all four cells; NO WATERMARK; no "图片由AI生成" mark; no logos; no other characters unless the story needs them.
```

**三个必踩坑，务必在提示词里强调**（否则脚本第三步会失败）：
1. **真纯白底**：不要办公桌、地板、米黄色、阴影。角色“悬浮”在 `#FFFFFF` 上，否则脚本的“白色背景检查”会因四角非纯白而失败。
2. **去水印 + 不画字**：默认可能带「图片由AI生成」水印，提示词必须包含 `NO WATERMARK`；同时 `Text (verbatim): "NONE"` 且明确 `NO text/letters/Chinese characters`——中文由脚本叠加，让 AI 画字只会乱。
3. **⭐ 主体与白底必须有反差（最关键）**：宫崎骏水彩风本身偏柔和，务必额外强调角色用**较饱和、清晰可辨的彩色**填充 + **可见描边**，穿**彩色衣服（蓝/青/赭）而非白/浅色**。目的：让四角与格间留白保持纯白（`#FFFFFF`），角色与白底自然分离，切分时边缘干净。

**画面一致性要求**（切分准确的前提）：提示词要强调 **四格等大、角色在各格中位置/大小一致**（`evenly-spaced 2×2 grid, same size cells, same character scale and placement`）。脚本按行列等分裁切，原图排布越规整，切分越准。

检查四格是否齐全、角色是否一致、四格排布是否规整等大、背景是否纯白、是否无水印无文字。（文字留到第三步用脚本叠加。）

停下来让用户查看分镜，接受“改文字、改动作、改角色、重新生成”等意见。确认后才进入第三步。

### 第三步：拼接成 GIF

运行技能内的中文脚本，切出每格并导出白底 GIF。脚本只用 Pillow，需在装有 Pillow 的 Python 3 里运行（如托管 venv `/Users/<用户>/.workbuddy/binaries/python/envs/default/bin/python3`）：

```bash
python3 <技能目录>/脚本/拼接动图.py \
  --source <项目目录>/原始素材/连环分镜.png \
  --project <项目目录> \
  --rows 2 --cols 2 --gutter 6 \
  --durations 400,400,400,1500 \
  --texts "起不来|？|……|上班" \
  --text-pos bottom
```

参数说明：
- `--durations`：各帧停留时长（毫秒）。推荐 **`400,400,400,1500`**：前三格每格 0.4 秒读图轻松；**最后一格（包袱/高潮）停 1.5 秒**形成“结束感”，循环回到第一格时能看出新一轮开始。
- `--texts`：**每格文字，用竖线 `|` 分隔**（如 `"起不来|？|……|上班"`）。某格不要字就留空（如 `"|？||上班"`）。文字由脚本用系统黑体精准叠加，绝不会乱。极短常用中文最佳；即使去掉文字，动作本身也要能看懂笑点。
- `--text-pos`：文字位置 `top` 或 `bottom`（默认 `bottom`）。
- `--gutter`：每格四边裁掉的像素，用来切掉 AI 可能画出的分割线，保证切分干净（默认 6，分割线粗就调大）。

脚本流程（**已去掉抠图/重心对齐/归一化**，改为精准裁切 + 脚本叠字）：

1. **精准等分裁切**：按行列把原图等分成规整四格，`--gutter` 裁掉每格边缘（切掉分割线残留）。切分是否准，取决于原图四格排布是否规整等大——所以第二步提示词要强调“四格等大、角色位置一致”。
2. **整体居中缩放（不抠图）**：把每格画面**整体**等比缩放后居中贴到正方形白底画布（contain 模式），四周留一点白边。不再做主体检测/重心对齐/大小归一化——角色一致性完全靠提示词保证。
3. **边缘清杂**：只把紧贴画布四边 ~10px 的近白/中性灰杂色（分割线残片、背景轻微溢出）涂白，不碰画面中心，保护角色与文字。
4. **脚本叠加中文字**：用系统黑体（PingFang 或 STHeiti）在每格叠加 `--texts` 指定的文字，带白色描边、字号自适应、横向居中——字体规整不乱，位置固定可控。
5. **循环接缝标记**：最后一格之后插入一帧轻微闪白（约 78% 白、140ms），配合第 4 格长停顿，标出无限循环的起点。
6. **循环导出**：导出循环 GIF、最大边长 240 像素、文件 ≤ 500 KB、纯白背景、关闭抖动防灰斑。

脚本会写入中文命名的分帧、首帧预览、动作预览图和 `质量检查.json`（含每格文字与所用字体）。

交付前检查：

1. `质量检查.json` 的“是否通过”为真，且“背景检查”为“白色背景通过”。
2. GIF 是循环 GIF，大小不超过 240×240、文件不超过 500 KB。
3. 检查 `动作预览图.png`：四格切分干净（无相邻格内容/无分割线残留）、角色清晰、白底干净、无水印；`质量检查.json` 里的“每格文字”与预期一致（文字由脚本叠加，天然规整）。

最后报告成品路径、尺寸、帧数、时长、文件大小。用户可将 GIF 发到微信后长按选择“添加到表情”。
