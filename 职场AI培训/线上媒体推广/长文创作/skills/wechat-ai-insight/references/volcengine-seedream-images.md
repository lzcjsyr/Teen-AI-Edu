# 火山方舟 Seedream 配图说明

这份说明只服务于公众号配图阶段。
正文写完之后，再读取它。

## 目标

- 默认调用火山方舟文生图 API，直接生成本地插图文件。
- 只有当用户明确要求本地 HTML 解释图时，才改走 [local-html-images.md](local-html-images.md)。
- 图片是阅读辅助，不是信息主载体。

## 默认策略

- 正文先写完。
- 再分析全文，挑出 5 到 7 个最适合配图的位置。
- 再为这 5 到 7 个位置统一写 prompt，统一调用 API 生图。
- 所有生成图片统一保存到项目文件夹下的 `images/` 子文件夹。
- 图片默认走 16:9 横图。
- 图中文字尽量少。不要在 prompt 里要求大段中文排版。
- 画面默认追求结构清楚、层级分明、重点突出、整体简洁。
- 默认风格偏宫崎骏动画气质的暖色手绘编辑插图：温馨、柔和、明亮，有空气感和生活感，不阴冷，不赛博霓虹，不做通用科技海报。
- 如果画面中需要可见文字，默认使用中文；只有模型名、产品名、缩写等专业名词才保留英文。
- 图片优先承担这几种作用：视觉锚点、概念隐喻、场景化补充、情绪氛围。
- 图片不要承担这几种作用：精确流程图、复杂关系图、密集信息图、长文案海报。
- 如果用户明确要求强结构、强可控、少量中文标签的解释图，再切换到本地 HTML 截图模式；默认不要主动切换。

## API 约定

- Endpoint：`https://ark.cn-beijing.volces.com/api/v3/images/generations`
- 默认模型：`doubao-seedream-5-0-260128`
- 默认返回：`response_format = "url"`
- 默认关闭水印：`watermark = false`
- 默认关闭串行生成：`sequential_image_generation = "disabled"`
- 默认关闭流式：`stream = false`
- API Key 从项目根目录 `.env` 或系统环境变量 `ARK_API_KEY` 读取，不写入 skill 代码或文档
- 调用方默认只需要提供两个口子：`prompt` 和 `size`

## 本地配置

项目根目录应提供 `.env`，并参考 `.env.example` 填写：

```env
ARK_API_KEY=
ARK_ENDPOINT=https://ark.cn-beijing.volces.com/api/v3/images/generations
ARK_MODEL=doubao-seedream-5-0-260128
```

`.env` 存放真实密钥，必须被 git 忽略；`.env.example` 只保留变量名和默认公共配置。
如果系统环境变量已经设置同名变量，脚本会优先使用系统环境变量。

## 尺寸说明

- 这个 skill 默认把 16:9 横图尺寸设为 `2560x1440`。
- 这是当前已经实际跑通的默认值。
- 如果任务需要其他尺寸，只覆写 `size` 即可。

## Prompt 写法

- 先写“这张图要服务哪段内容”，再写视觉方案。
- 优先写成“编辑插图”而不是“信息图”。
- 默认明确写出“偏宫崎骏动画气质的暖色手绘编辑插图”或等价要求，避免只写成宽泛的 illustration style。
- 优先让模型画场景、角色、物体、空间关系、光线、构图、气氛。
- 避免要求模型在图里写很多字。
- 避免要求模型准确渲染表格、流程框、复杂箭头网络。
- 优先强调单一主题和主次层级，不要让多个信息点抢同一张图的注意力。
- 可以要求少量中文标签来点题，但不要让英文词成为默认选择。

### 开头 thesis 图专门规则

- 开头图不是封面气氛图，而是“全文论点总图”。
- prompt 里要明确写出这张图需要帮助读者一眼识别的两个信息：文章主题是什么，读完后能获得什么判断框架或价值。
- thesis 图优先画清楚一组中心对比，例如“标准答案 vs 结果责任”“流程外供给 vs 工作流控制”，不要同时塞进三四个并列比喻。
- 如不加短标签，画面本身也必须能看出主次与方向；如必须加标签，限制在 1 到 3 个短中文词组，每个尽量不超过 6 个汉字。
- thesis 图要更像杂志专题的 opening spread，不要像抽象意境图，也不要像信息密集海报。

推荐结构：

1. 核心概念
2. 场景化隐喻
3. 构图要求
4. 风格要求
5. 禁止项

thesis 图推荐额外补一句：
6. 读者收益提示

示例补法：

- “让读者一眼看懂本文要讨论哪类商业模式最脆弱，并预告文中会给出判断框架。”

推荐风格词：

- editorial illustration
- conceptual illustration
- magazine feature visual
- warm hand-painted illustration
- Miyazaki-inspired atmosphere
- soft natural lighting
- gentle, human, airy mood
- clean composition
- clear visual hierarchy
- single focal point
- restrained typography
- minimal text

常用禁止项：

- no dense text
- no infographic
- no poster layout
- no watermark
- no UI screenshot

## 图片计划文件

优先先写一个 JSON 计划文件，再调脚本。

示例：

```json
{
  "images": [
    {
      "filename": "01-trust-shift.jpeg",
      "alt": "",
      "prompt": "一张用于解释“AI 竞争从模型能力转向分发信任”的编辑概念插图，采用偏宫崎骏动画气质的暖色手绘风格，温馨、柔和、明亮，有空气感和生活感。前景是嘈杂的信息市场，背景是逐渐退后的通用模型能力，中间只有一条清晰可信的通路穿过噪音。画面强调单一重点、层级清楚、结构简洁、重点突出，杂讯元素少，适合杂志专题配图。图中如需可见文字，只使用极少中文标签，不使用英文口号。no dense text, no infographic, no poster layout, no watermark, no cyberpunk, no cold tech poster.",
      "size": "2560x1440"
    }
  ]
}
```

## 脚本

优先使用统一入口脚本：

```bash
python3 scripts/generate_article_images.py /path/to/project-folder/image-plan.json --output-dir /path/to/project-folder/images
```

如果确定整批都走 API，也可以直接运行：

```bash
python3 scripts/generate_seedream_images.py /path/to/project-folder/image-plan.json --output-dir /path/to/project-folder/images
```

脚本会：

- 读取 JSON 计划文件
- 逐张调用 API
- 下载本地图片
- 生成 `generated-image-manifest.json`

## 与 Markdown / DOCX 的衔接

- 图片下载后，把本地图片路径插回 Markdown。
- 默认使用 `images/文件名` 这种相对路径，不要把图片散放在项目根目录。
- 需要无图注时，使用空 alt：`![](images/01-trust-shift.jpeg)`
- 需要短图注时，再写很短的 alt。
- 不要把图注写成长解释。
