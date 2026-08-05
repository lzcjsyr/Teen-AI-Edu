---
name: original-art-story-video
description: 将用户的一段故事想法、自创角色或手绘原画，制作成可微信分享的 3:4 故事视频：先生成可编辑的 Word 文稿，再生成供确认的角色原型，确认后才加入配图、可选授权声音或预置旁白、字幕、背景音乐和 MP4 合成。只要用户想把一个故事文本、涂鸦或自创角色发展成竖版故事视频，尤其希望先审 Word 文稿、确认角色形象、重做单幕或不使用传统剪辑软件时，都应使用本 Skill；普通横屏解说、商业数据动画和非叙事视频不使用本 Skill。
compatibility: 需要 Python 3.10+、FFmpeg、MIMO_API_KEY，以及 Python 的 docx/Pillow 依赖。生图使用 WorkBuddy 内置 ImageGen 工具，无需额外 API 密钥。
---

# 原画故事视频

## 交付目标

交付 1080×1440、H.264/AAC 编码的 MP4，以及可继续编辑的 `故事.docx`。默认加入背景音乐，创作者可在 Word 中选曲或关闭；不要求使用传统剪辑软件。

## 生图方式（重要变更）

本 Skill 的生图能力使用 **WorkBuddy 内置 ImageGen 工具**（腾讯混元模型）。助手在对话中直接调用 ImageGen 生成图片，无需用户配置外部 API 密钥。

**工作原理：**
1. 运行 `run.py prototype` 或 `run.py images` 时，脚本会先完成本地准备工作（归一化原画等），然后为每张缺失的图片打印 `IMAGE_PLAN`（包含 prompt、参考图路径、保存路径、尺寸）。
2. 助手解析计划，逐个调用 ImageGen 工具，将生成的图片保存到指定路径。
3. 再次运行同一命令，脚本检测到图片已存在，自动执行本地后处理：
   - **JFIF 归一化**：ImageGen 输出 PNG 格式，脚本自动用 PIL 将其转换为标准 JFIF JPEG 并缩放到 config 尺寸（1024×1536），确保 python-docx 能正确识别。
   - 角色原型加印名字。
   - 生成结尾页。
   - 更新清单并回写 docx。

**多角色一致性策略（方案 A）：** ImageGen 的 `image` 参数仅接受单张参考图。因此场景生成时只传入原画作为风格参考，角色外貌通过文字描述在 prompt 中传达。角色原型阶段仍然只传入原画，一致性较好。

**ImageGen 注意事项：**
- ImageGen 输出 PNG 文件，文件名基于 prompt 内容生成（通常很长）。助手生成后需用 `ls -t` 找到最新文件，重命名/移动到 `IMAGE_PLAN` 中指定的 `output` 路径。
- ImageGen 可能遇到速率限制（`RequestLimitExceeded`），等待 15 秒后重试即可。
- ImageGen 实际输出尺寸可能与请求的 `size` 参数不完全一致，脚本后处理会自动缩放到配置尺寸。

## 开始前

1. 运行 `python3 脚本/run.py preflight`。仅生成文稿时，缺少配音密钥不阻止先完成故事共创。生图不再需要任何外部密钥。
2. 使用昵称或编号作为项目名，不在项目名、故事或提示词中写真实姓名、住址、学校、联系方式等不必要信息。
3. 若要上传原画或克隆声音，先确认创作者拥有素材使用权，并同意将对应素材发送给外部服务。未获声音授权时，继续用官方预置音色，不上传声音参考。
4. 仅在当前任务需要时阅读：故事与画面规则读 `参考/02_故事创作规则.md`；接口、尺寸、隐私或声音问题读 `参考/03_技术与隐私.md`。

## 故事共创

优先提取用户已提供的信息；不足时一次只问一组简短问题：角色是什么、最特别的特点、想去哪里、遇到什么小困难、希望呈现的气氛。给出三个一句话方向供选择。

选定后，按 `参考/02_故事创作规则.md` 写为故事，保存为 JSON。必须提供 `title`、`creator_display`、角色的 `name` / `subject_type` / 外貌，以及各幕的 `narration` 和 `visual_prompt`；结构参照 `参考/story.example.json`。幕数不限（至少 1 幕）。非人物主角就是其自身，不要凭空增加人类身体或操作者。

## 四阶段、三次人工确认

不要使用 `run.py all`。角色原型是控制角色一致性的关键中间产物；在它确认前生成场景，会放大返工成本。每个需要创作者判断的阶段结束后都必须等待确认。

### 1. 文稿与选择

```bash
python3 脚本/run.py init \
  --project "项目名" \
  --story "故事JSON路径"
```

命令生成 `项目名/故事.docx`；原画与声音在此阶段都可暂不提供。Word 是唯一的编辑入口。提醒用户核对角色、旁白、画面提示词、配音音色和"背景音乐"选项。配音音色可填写官方预置音色 `冰糖`、`苏打`、`茉莉`、`白桦`，或填写 `克隆音` 启用声音克隆（详见 `参考/03_技术与隐私.md`）。背景音乐可填写 `自动匹配`、`无`、`菊次郎的夏天`、`卡农`、`空灵之声` 或 `勇气之誓`。

**确认点 1：** 提供 `故事.docx` 的绝对路径。请用户直接编辑并保存；保留 `【旁白-开始/结束】` 与 `【画面提示词-开始/结束】` 标记，确认后再继续。

### 2. 角色原型

文稿确认后，让用户提供原画；若没有原画，说明当前版本无法继续生成一致配图。只生成角色原型：

```bash
python3 脚本/run.py prototype --project "项目名"
```

**两步流程：**
1. 脚本归一化原画，为每个角色打印 `IMAGE_PLAN`（prompt、参考图路径、输出路径、尺寸）。
2. **助手调用 ImageGen 工具**：对每个 `IMAGE_PLAN`，使用 `ToolSearch` 加载 ImageGen 工具，再用 `DeferExecuteTool` 调用，参数：
   - `prompt`: 计划中的 prompt
   - `image`: 计划中的 reference 路径（原画归一化后的路径）
   - `size`: 计划中的 size（如 `1024x1536`）
   - `quality`: `"high"`
   - `input_fidelity`: `"high"`（角色原型需高保真保留原画风格）
   - `output_dir`: 图片输出目录（让 ImageGen 保存到项目 `图片/` 目录）
   - 生成后，将文件重命名/移动到 `IMAGE_PLAN` 中指定的 `output` 路径。
3. 再次运行 `python3 脚本/run.py prototype --project "项目名"`，脚本检测到图片已存在，自动加印角色名并更新清单、回写 docx。

若原型不满意，可在 Word 修改角色设定后重做：

```bash
python3 脚本/run.py prototype --project "项目名" --force
```

`--force` 会删除已有原型图和名字标记，重新打印生成计划。

**确认点 2：** 提供更新后的 `故事.docx`。请用户只检查角色的外形、颜色、结构和手绘气质；确认原型无误后再继续。

### 3. 配图与旁白

```bash
python3 脚本/run.py images --project "项目名"
python3 脚本/run.py voice --project "项目名"
```

**配图两步流程（同阶段 2）：**
1. `run.py images` 为每幕缺失的场景图打印 `IMAGE_PLAN`，同时自动生成结尾页（本地 PIL，无需外部调用）。
2. **助手调用 ImageGen 工具**：对每个 `IMAGE_PLAN`，参数：
   - `prompt`: 计划中的 prompt
   - `image`: 计划中的 reference 路径（原画归一化路径）
   - `size`: `1024x1536`
   - `quality`: `"high"`
   - `input_fidelity`: `"medium"`（场景图允许更多创意发挥）
   - `output_dir`: 项目 `图片/` 目录
   - 生成后，将文件重命名/移动到 `IMAGE_PLAN` 中指定的 `output` 路径。
3. 再次运行 `python3 脚本/run.py images --project "项目名"`，脚本检测到所有图片已存在，更新清单并回写 docx。

`voice` 会读取 `故事.docx` 的「配音音色」：填 `克隆音` 则启用声音克隆（优先用 `输入/声音参考.*`，缺失时回退 Skill 自带样例 `资源/用户声音/声音参考.wav`）；填官方音色名则用预置音色。**指定 `克隆音` 时不要加 `--preset`**，否则会强制走预置音色、覆盖文档意图。

`images` 只会使用已存在的角色原型；若原型缺失，脚本会停止并提示先完成阶段 2。图片生成会先读取 Word 的最新内容，并在完成后自动重建 `故事.docx`：无论是首次生成还是用 `--scene N --force` 重做某一幕，Word 内对应配图都会更新。若改动某一幕：

```bash
python3 脚本/run.py images --project "项目名" --scene 2 --force
# 然后助手用 ImageGen 重新生成该幕图片
# 再运行一次 images 完成后处理
python3 脚本/run.py voice --project "项目名" --scene 2 --force
```

仅重做实际改动的图片或旁白；不要重复生成未改动素材。结尾作品页会同时刷新，突出显示故事标题与创作者名称。

**确认点 3：** 让用户重新打开 `故事.docx` 检查配图，并试听 `声音/`。如有修改，按上面的单幕命令刷新；确认后再合成。

### 4. 合成与交付

```bash
python3 脚本/run.py render --project "项目名" --force
python3 脚本/run.py verify --project "项目名"
```

使用 `--force` 确保采用刚更新的图片、旁白、背景音乐和结尾页。交付 `故事视频.mp4` 的绝对路径，并提醒用户分享前检查不希望公开的信息。

## 失败分流

- 生图效果不满意：用 `images --scene N --force` 重做该幕，助手重新调用 ImageGen 生成。
- ImageGen 速率限制（`RequestLimitExceeded`）：等待 15 秒后重试同一调用。
- ImageGen 输出 PNG：脚本后处理自动转换为 JFIF JPEG，助手无需手动转换。
- 限流或网络失败（ImageGen）：重试同一 ImageGen 调用。
- 角色原型不满意：在 Word 修改角色设定后，使用 `prototype --force`；未确认前不要运行 `images`。
- 角色走样：只用 `images --scene N --force` 重做该幕。
- Word 解析失败：恢复结构标记、检查各幕和必填项，再重试。
- 字幕烧录不可用：保留 SRT 与无烧录字幕版视频，不阻塞交付。
