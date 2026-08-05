# 微信公众号 HTML 排版规范

## 目标
把已经写好的 Markdown 或纯文本文章，转换成一份可直接复制粘贴到微信公众号后台的内联样式 HTML，并且与本 skill 的 `.docx` 成稿保持同一篇文章、同一组图片、同一份来源。

## 强制要求
- 全文输出，不能删减原文的任何一个字、任何一个图表或数据
- 只使用行内样式，不要输出 `<style>` 标签
- 不要输出微信自带的冗余类名，例如 `js_insertlocalimg`
- 整篇文章必须包裹在全局外层容器中
- 默认交付的 `.html` 文件必须可被用户整段复制后直接粘贴到公众号后台
- 默认交付“无图占位标记版” HTML，而不是本地路径图片版
- 导出前默认自动规范图片目录，不要求用户先手动整理 `images/`

## 全局视觉规范
- 排版字体：`'Plus Jakarta Sans', 'Noto Sans SC', 'PingFang SC', 'Microsoft YaHei', sans-serif`
- 正文字号：`16px`
- 注释字号：`14px` 或 `13px`
- 全局行高：`2em`
- 全局字间距：`0.5px`
- 正文段间距：`24px` 或 `1.5em`
- 正文默认色：`rgb(51, 51, 51)`
- 主色 / 强调色 1：`rgb(12, 35, 64)`
- 辅色 / 强调色 2：`rgb(212, 168, 67)`
- 说明文字色：`rgb(136, 136, 136)`
- 引用底色：`rgb(248, 249, 250)`

## 组件代码库

### 1. 全局外层容器
所有内容必须包裹在下面这个 `section` 中：

```html
<section style="max-width: 600px; margin: 0px auto; background-color: rgb(255, 255, 255); font-family: 'Plus Jakarta Sans', 'Noto Sans SC', 'PingFang SC', 'Microsoft YaHei', sans-serif; color: rgb(51, 51, 51); line-height: 2em; font-size: 16px; letter-spacing: 0.5px; overflow-wrap: break-word; padding: 0px 10px;">
</section>
```

### 2. 标题处理

默认 HTML **不输出顶部主标题区域**。

使用规则：
- HTML 文件只包含正文，不包含主标题、副标题、英文副标题、作者、日期等头部信息
- 文章标题默认以输出文件名为准，供用户在文件系统或公众号后台识别
- `article.md` 里的第一个 `# 标题` 仍可保留，作为文章元信息和其他导出流程的输入，但不进入 HTML
- 如果正文第一段会重复主标题内容，应在写作时自行避免

### 3. 引言 / 金句模块

```html
<section style="border-left: 4px solid rgb(212, 168, 67); background-color: rgb(248, 249, 250); padding: 20px; margin-bottom: 40px;">
  <p style="margin: 0px 0px 10px; color: rgb(12, 35, 64); font-size: 16px; font-weight: bold; font-style: italic;">
    "引言或金句正文"
  </p>
  <p style="margin: 0px; color: rgb(136, 136, 136); font-size: 13px; text-align: right;">
    — 引言出处
  </p>
</section>
```

### 4. 正文段落与文内强调
普通段落：

```html
<p style="margin-bottom: 24px;">段落文本内容</p>
```

文内重点加粗（海军蓝）：

```html
<strong style="color: rgb(12, 35, 64); font-weight: bold;">加粗重点词汇</strong>
```

文内重点加粗（暗金）：

```html
<strong style="color: rgb(212, 168, 67); font-weight: bold;">加粗重点词汇</strong>
```

使用规则：
- 正文默认沿用普通段落组件
- 重点强调只能使用上面两种颜色的 `strong`
- 不要发明新的彩色标签体系

### 5. 分割线

```html
<hr style="border-right: none; border-bottom: none; border-left: none; border-top: 1px solid rgb(212, 168, 67); margin: 40px 0px;">
```

用于章节之间的大分隔，尤其适合正文和来源区之间。

### 6. 二级标题

```html
<section style="margin-bottom: 25px; margin-top: 40px;">
  <section style="display: flex; align-items: flex-start;">
    <section style="width: 34px; height: 34px; background-color: rgb(212, 168, 67); color: rgb(255, 255, 255); font-size: 18px; font-weight: bold; text-align: center; line-height: 34px; margin-right: 12px; flex-shrink: 0;">
      1
    </section>
    <section style="flex: 1 1 0%;">
      <h2 style="color: rgb(12, 35, 64); font-size: 21px; font-weight: bold; margin: 0px;">
        中文标题名称
      </h2>
      <p style="color: rgb(136, 136, 136); font-size: 13px; font-weight: normal; margin: 4px 0px 0px; letter-spacing: 0.5px; text-transform: uppercase;">
        ENGLISH TITLE (如果有)
      </p>
    </section>
  </section>
</section>
```

使用规则：
- 正文主结构默认用这种编号 H2
- 序号按文章顺序递增
- 如果没有英文标题，可省略英文标题行
- 推荐在 Markdown 中写成 `## 中文标题 | ENGLISH TITLE`，便于稳定拆分

### 7. 极简表格

```html
<section style="margin-bottom: 25px; overflow-x: auto;">
  <table style="width: 100%; border-collapse: collapse; font-size: 14px; text-align: left; min-width: 500px;">
    <thead>
      <tr style="background-color: rgba(235, 235, 235, 1); color: rgb(12, 35, 64);">
        <th style="padding: 12px; font-weight: bold; width: 30%;">维度/项目</th>
        <th style="padding: 12px; font-weight: bold;">信息1</th>
        <th style="padding: 12px; font-weight: bold;">信息2</th>
      </tr>
    </thead>
    <tbody>
      <tr style="border-bottom: 1px solid #EEEEEE;">
        <td style="padding: 12px; font-weight: bold; color: rgb(12, 35, 64);">核心字段</td>
        <td style="padding: 12px;">具体数据或内容</td>
        <td style="padding: 12px;">具体数据或内容</td>
      </tr>
    </tbody>
  </table>
</section>
```

使用规则：
- Markdown 表格必须映射成这个表格组件
- 表头使用浅灰底蓝字
- 首列默认加粗并使用海军蓝
- 只保留行底分割线，不要添加额外外边框

### 8. 文末总结框

```html
<section style="background-color: rgb(248, 249, 250); border-radius: 4px; padding: 20px; margin-bottom: 30px; text-align: center;">
  <p style="color: rgb(12, 35, 64); font-size: 16px; font-weight: bold; margin-bottom: 10px; text-align: justify;">
    总结性金句或观点。
  </p>
  <p style="color: rgb(51, 51, 51); font-size: 15px; margin-bottom: 20px; text-align: justify;">
    补充说明内容。
  </p>
  <p style="color: rgb(212, 168, 67); font-size: 16px; font-weight: bold; margin: 0px; text-align: right;">
    — 作者署名
  </p>
</section>
```

使用规则：
- 仅在原文本来就有总结性结尾时使用
- 不要为了凑组件而伪造一句“金句”

### 9. 图片占位块

当图片尚未上传到公众号后台或公网图床时，默认使用下面这个占位组件，不要把本地文件路径直接写进 `img src`：

```html
<section style="margin-bottom: 28px;">
  <section style="border: 1px dashed rgb(212, 168, 67); background-color: rgb(248, 249, 250); padding: 20px; text-align: center; border-radius: 4px;">
    <p style="margin: 0px 0px 8px; color: rgb(12, 35, 64); font-size: 16px; font-weight: bold;">[图片占位 1]</p>
    <p style="margin: 0px 0px 10px; color: rgb(51, 51, 51); font-size: 14px; line-height: 1.7;">待替换原图：/absolute/path/to/image.jpg</p>
    <p style="margin: 0px; color: rgb(136, 136, 136); font-size: 12px; line-height: 1.6;">粘贴到公众号后台后，请在此处上传并替换对应图片。</p>
  </section>
  <p style="margin: 10px 0px 0px; color: rgb(136, 136, 136); font-size: 13px; text-align: center;">这里填写图片说明或 alt 文本</p>
</section>
```

使用规则：
- Markdown 里有图片时，默认输出占位块，不能直接省略
- 占位序号按全文顺序递增
- 框外图注优先使用图片 alt；没有 alt 时可退回文件名
- 框内第二行用于替换操作提示，不承担最终图注职责
- 只有当图片已经有公网 URL，或用户明确要求保留真实 `<img>` 时，才输出真实图片组件
- 占位顺序必须与正文中的图片顺序一致，并与规范化后的 `images/` 目录顺序一致

### 10. 参考来源列表

```html
<section style="border-top: 1px solid #EEEEEE; padding-top: 20px; margin-bottom: 40px;">
  <p style="color: rgb(136, 136, 136); font-size: 14px; font-weight: bold; margin-bottom: 10px;">
    参考来源 / Sources
  </p>
  <ol style="color: rgb(136, 136, 136); font-size: 12px; line-height: 1.6; padding-left: 20px; margin: 0; word-break: break-all;">
    <li style="margin-bottom: 6px;">来源文献 1 及其链接</li>
    <li style="margin-bottom: 6px;">来源文献 2 及其链接</li>
  </ol>
</section>
```

使用规则：
- 最终内容保留来源文字，但默认不展示 URL
- “信息来源 / Sources / 参考来源”等同类章节，统一归并到这个来源区组件

## 推荐的 Markdown 约定
- 第一条 `# ` 一级标题作为文章标题元信息，不进入 HTML 正文
- `## 中文标题 | ENGLISH TITLE` 对应编号二级标题
- 独占一行的 `![alt](path)` 保留为正文图片位置；默认导出为占位块
- Markdown 表格照常写，导出时转成极简表格
- `> 引言` 或多行引用默认转成引言模块；若最后一行为 `— 出处`，则作为引用来源
- 如果需要给其他导出流程或归档保留元信息，可在文章开头空行后追加这些可选元信息行：
  - `副标题：......`
  - `英文副标题：......`
  - `作者：......`
  - `日期：......`
- 上述元信息默认不会进入 HTML

## 导出要求
- 默认同时导出 `.docx` 和 `.html`
- `.html` 必须是单文件、UTF-8 编码、纯内联样式
- 默认 HTML 应为无图占位标记版，便于公众号后台逐张替换上传
- 交付给用户时，应明确说明这个 HTML 文件可以整段复制到公众号后台
- 正常使用时，`build_wechat_html.py` 应自动先执行图片规范化，再生成最终 HTML
