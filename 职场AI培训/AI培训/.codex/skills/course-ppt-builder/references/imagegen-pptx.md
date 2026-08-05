# 图片版 PPTX 生成参考

当用户选择“图片版 PPTX / 每页一张图 / image_gen / PPTX”时读取本文件。

目标产物是一套 16:9 图片和一个不可编辑的图片版 `.pptx`：每个课程页先生成一张图片，再用脚本把图片铺满 PPTX 页面。

## 流程

### 1. 提取每页内容

用户确认 Markdown 后，运行：

```bash
python course-ppt-builder/scripts/extract_slide_briefs.py \
  "第一课/课程稿.md" \
  --out "第一课/课件成品/页面摘要.json"
```

脚本会读取 `#### 【第 N 页：标题】`，并生成结构化的页面摘要 JSON。

### 2. 逐页生成图片

- 真正负责生成图片的是内置 `image_gen` 工具。
- 本 Skill 负责把 Markdown 页面内容改写成适合 `image_gen` 的提示词，并管理图片保存、质量检查和 PPTX 合成。
- 每个课程页应单独生成一张图片，不要试图一次生成整套课程图片。
- 如果用户没有特别要求，不要切换到 CLI 或 API fallback；默认使用内置 `image_gen` 工具。
- 不要用本地代码绘制图片来替代生图，除非用户明确要求不用 AI 生图。

每页生成前，读取页面摘要 JSON 中的一页内容并提炼：

1. 页面标题
2. 本页核心信息，一句话即可
3. 应该放进图里的短文本，控制在 3-5 条
4. 适合的视觉结构，优先参考 Markdown 里的 `**页面设计**`，例如分层图、流程图、提示词框、四宫格、封面

不要把 Markdown 原文整段塞进提示词让模型照抄。先把内容整理成清晰的视觉 brief。

## 统一图片风格

每张图片都要遵守：

- 16:9 横版
- 中文商务培训 PPT 页面
- 简洁、干净、有基本商务范
- 浅色背景，留白充足
- 蓝、绿、灰、橙作为少量强调色
- 不要复杂科技风、不要炫光、不要大面积渐变
- 不要水印、不要 logo、不要无关人物
- 不要密集文字，不要小字堆满页面

## 通用提示词模板

```text
Use case: infographic-diagram
Asset type: 16:9 Chinese business training PowerPoint slide image
Primary request: Generate one PPT slide image based on the provided slide brief.

Style: clean, minimal, professional business training style; light background; generous whitespace; restrained blue, green, gray, and amber accents; clear hierarchy; modern layout; no clutter.

Slide title: [页面标题]
Core message: [一句话核心信息]
Visible Chinese text: [3-5 条短句，必须准确可读]
Visual structure: [分层图 / 流程图 / 提示词框 / 四宫格 / 对比图 / 封面]

Requirements:
- All visible text must be Simplified Chinese.
- Text must be large, clear, and readable.
- Do not add unrelated people, fake logos, watermarks, decorative tech backgrounds, or dense paragraphs.
- The result should look like one page of a clean corporate training deck.
```

## 页面类型提示

### 封面页

使用大标题、简短副标题、课程名、主讲人和时长。画面要简洁，不要做成海报。

### 概念关系页

优先使用分层图、矩阵图、流程图。文字要短，图形关系要清楚。

### 表格或对比页

不要塞入完整大表。只保留最关键的几项，或改成卡片式对比。

### 提示词页

使用明显的深色或浅色提示词框，旁边放 2-3 条提醒。提示词不要太长。

### 案例流程页

使用“输入 -> 处理 -> 输出”或 3-5 步流程。每步只保留短句。

### 总结页

使用 3-4 个短语或关键词，不要写解释段落。

## 保存与命名

内置 `image_gen` 工具生成图片后，必须把选定图片复制到项目输出目录：

```text
第一课/课件成品/页面图片/第01页.png
第一课/课件成品/页面图片/第02页.png
...
```

课件产物目录和图片目录都必须使用中文命名。不要使用 `generated_ppt/`、`images/` 等英文目录名，也不要只把图片留在默认生成目录。

课程 Markdown 保留在课程文件夹根目录，例如 `第一课/课程稿.md`；页面摘要、页面图片和 PPTX 属于展示成品，必须放在 `第一课/课件成品/` 内。

### 3. 图片质量检查

每页生成后检查：

- 中文是否可读，有无错字或乱码
- 页面标题是否和 Markdown 含义一致
- 文字是否过密、过小或被截断
- 画面是否干净、商务、统一
- 是否有无关图案、人物、水印或假 logo

如果某页失败，只重做这一页。

如果 `image_gen` 无法稳定生成准确中文，改用更少文字的图示页，并把详细文字留在 Markdown 或讲稿中。不要改用本地代码渲染，除非用户明确同意。

### 4. 合成 PPTX

图片全部生成并检查后，运行：

```bash
python course-ppt-builder/scripts/images_to_ppt.py \
  "第一课/课件成品/页面图片" \
  --out "第一课/课件成品/图片版课件.pptx"
```

脚本会按文件名排序，把每张图片铺满一页 16:9 幻灯片。

## 交付前检查

- 页面摘要 JSON 的页数和 Markdown 页数一致
- 图片数量和页面摘要 JSON 页数一致
- PPTX 页数和图片数量一致
- 图片中文字没有明显乱码或错字
- 页面风格统一
- PPTX 文件能成功生成

最终回复写清楚：Markdown 文件路径、图片目录、PPTX 文件路径、总页数。
