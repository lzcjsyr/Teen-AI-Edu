#!/usr/bin/env python3
"""
把 Markdown 文章转换成适合微信公众号后台粘贴发布的内联样式 HTML。

支持的 Markdown 子集：
- #、##、### 标题
- 普通段落
- 无序列表：-、*、+
- 有序列表：1.
- 引用：>
- 加粗：**text**
- 行内代码：`text`
- 独占一行的图片：![alt](path)
- 简单 Markdown 表格

约定：
- 第一个一级标题仅作为文章标题元信息，不进入 HTML 正文。
- 标题后的可选元信息行支持：副标题、英文副标题、作者、日期，但默认不进入 HTML。
- 二级标题可写成“中文标题 | ENGLISH TITLE”以映射公众号编号标题。
- “来源 / 信息来源 / 参考资料”等章节统一输出到来源组件。
- 默认输出“无图占位标记版” HTML，便于粘贴到公众号后台后逐张替换上传。
- 默认 HTML 只包含正文，不输出顶部标题区；文章标题以文件名为准。
"""

from __future__ import annotations

import argparse
import html
import re
from pathlib import Path
from normalize_article_images import normalize_images


HEADING_RE = re.compile(r"^(#{1,3})\s+(.*)$")
UL_RE = re.compile(r"^\s*[-*+]\s+(.*)$")
OL_RE = re.compile(r"^\s*\d+\.\s+(.*)$")
IMAGE_RE = re.compile(r"^!\[(.*?)\]\((.*?)\)\s*$")
INLINE_RE = re.compile(r"(\*\*.*?\*\*|`.*?`)")
META_RE = re.compile(r"^(副标题|英文副标题|作者|日期)[:：]\s*(.+)$")
SOURCE_HEADING_KEYWORDS = (
    "信息来源",
    "来源",
    "参考资料",
    "参考来源",
    "资料来源",
    "参考文献",
    "参考链接",
    "sources",
)
SUMMARY_HEADING_KEYWORDS = ("结语", "总结", "小结", "尾声", "最后")


def normalize_heading_text(text: str) -> str:
    cleaned = re.sub(r"^[^A-Za-z0-9\u4e00-\u9fff]+", "", text).strip()
    return cleaned.strip("：: ").replace(" ", "").lower()


def is_source_heading(text: str) -> bool:
    normalized = normalize_heading_text(text)
    return any(keyword in normalized for keyword in SOURCE_HEADING_KEYWORDS)


def is_summary_heading(text: str) -> bool:
    normalized = normalize_heading_text(text)
    return any(keyword in normalized for keyword in SUMMARY_HEADING_KEYWORDS)


def split_heading_text(text: str) -> tuple[str, str | None]:
    for sep in (" | ", "｜", " / "):
        if sep in text:
            left, right = text.split(sep, 1)
            return left.strip(), right.strip() or None
    return text.strip(), None


def parse_inline(text: str) -> str:
    parts = INLINE_RE.split(text)
    html_parts: list[str] = []
    for part in parts:
        if not part:
            continue
        if part.startswith("**") and part.endswith("**"):
            html_parts.append(
                '<strong style="color: rgb(12, 35, 64); font-weight: bold;">'
                f"{html.escape(part[2:-2])}</strong>"
            )
        elif part.startswith("`") and part.endswith("`"):
            html_parts.append(
                '<code style="font-family: Menlo, Consolas, monospace; '
                'font-size: 14px; background-color: rgb(248, 249, 250); '
                'padding: 1px 4px;">'
                f"{html.escape(part[1:-1])}</code>"
            )
        else:
            html_parts.append(html.escape(part))
    return "".join(html_parts)


def render_paragraph(text: str) -> str:
    return f'<p style="margin-bottom: 24px;">{parse_inline(text)}</p>'


def render_h3(text: str) -> str:
    return (
        '<p style="margin-bottom: 18px;">'
        f'<strong style="color: rgb(12, 35, 64); font-weight: bold;">{html.escape(text)}</strong>'
        "</p>"
    )


def render_list(items: list[str], ordered: bool) -> str:
    tag = "ol" if ordered else "ul"
    return (
        f'<{tag} style="margin: 0px 0px 24px 22px; padding: 0px; color: rgb(51, 51, 51);">'
        + "".join(
            f'<li style="margin-bottom: 10px;">{parse_inline(item)}</li>'
            for item in items
        )
        + f"</{tag}>"
    )


def render_blockquote(lines: list[str]) -> str:
    quote_lines = [line.strip() for line in lines if line.strip()]
    source = None
    if quote_lines and quote_lines[-1].startswith(("—", "--")):
        source = quote_lines.pop().lstrip("-— ").strip()
    quote_text = "<br>".join(html.escape(line) for line in quote_lines)
    source_html = ""
    if source:
        source_html = (
            '<p style="margin: 0px; color: rgb(136, 136, 136); font-size: 13px; text-align: right;">'
            f"— {html.escape(source)}</p>"
        )
    return (
        '<section style="border-left: 4px solid rgb(212, 168, 67); '
        'background-color: rgb(248, 249, 250); padding: 20px; margin-bottom: 40px;">'
        '<p style="margin: 0px 0px 10px; color: rgb(12, 35, 64); font-size: 16px; '
        'font-weight: bold; font-style: italic;">'
        f'"{quote_text}"</p>{source_html}</section>'
    )


def render_image(base_dir: Path, alt_text: str, image_ref: str, image_mode: str, image_index: int) -> str:
    image_path = Path(image_ref)
    if not image_path.is_absolute():
        image_path = (base_dir / image_ref).resolve()
    alt = html.escape(alt_text)
    if image_mode == "local":
        src = html.escape(str(image_path))
        caption = ""
        if alt_text:
            caption = (
                '<p style="margin: 10px 0px 0px; color: rgb(136, 136, 136); '
                'font-size: 13px; text-align: center;">'
                f"{alt}</p>"
            )
        return (
            '<section style="margin-bottom: 28px; text-align: center;">'
            f'<img src="{src}" alt="{alt}" style="max-width: 100%; height: auto; display: inline-block;">'
            f"{caption}</section>"
        )

    placeholder_desc = alt_text.strip() or Path(image_ref).name
    placeholder_path = html.escape(str(image_path))
    caption = (
        '<p style="margin: 10px 0px 0px; color: rgb(136, 136, 136); '
        'font-size: 13px; text-align: center;">'
        f"{html.escape(placeholder_desc)}</p>"
    )
    return (
        '<section style="margin-bottom: 28px;">'
        '<section style="border: 1px dashed rgb(212, 168, 67); background-color: rgb(248, 249, 250); '
        'padding: 20px; text-align: center; border-radius: 4px;">'
        f'<p style="margin: 0px 0px 8px; color: rgb(12, 35, 64); font-size: 16px; font-weight: bold;">'
        f'[图片占位 {image_index}]</p>'
        f'<p style="margin: 0px 0px 10px; color: rgb(51, 51, 51); font-size: 14px; line-height: 1.7;">'
        f'待替换原图：{placeholder_path}</p>'
        '<p style="margin: 0px; color: rgb(136, 136, 136); font-size: 12px; line-height: 1.6;">'
        '粘贴到公众号后台后，请在此处上传并替换对应图片。'
        '</p>'
        '</section>'
        f"{caption}"
        '</section>'
    )


def split_table_row(line: str) -> list[str]:
    stripped = line.strip().strip("|")
    return [cell.strip() for cell in stripped.split("|")]


def is_table_divider(line: str) -> bool:
    stripped = line.strip().replace("|", "").replace(":", "").replace("-", "").replace(" ", "")
    return stripped == ""


def render_table(rows: list[list[str]]) -> str:
    if not rows:
        return ""
    headers = rows[0]
    body_rows = rows[1:]
    head_html = "".join(
        (
            f'<th style="padding: 12px; font-weight: bold;{" width: 30%;" if index == 0 else ""}">'
            f"{parse_inline(cell)}</th>"
        )
        for index, cell in enumerate(headers)
    )
    body_html = "".join(
        '<tr style="border-bottom: 1px solid #EEEEEE;">'
        + "".join(
            (
                f'<td style="padding: 12px;{" font-weight: bold; color: rgb(12, 35, 64);" if idx == 0 else ""}">'
                f"{parse_inline(cell)}</td>"
            )
            for idx, cell in enumerate(row)
        )
        + "</tr>"
        for row in body_rows
    )
    return (
        '<section style="margin-bottom: 25px; overflow-x: auto;">'
        '<table style="width: 100%; border-collapse: collapse; font-size: 14px; '
        'text-align: left; min-width: 500px;">'
        '<thead><tr style="background-color: rgba(235, 235, 235, 1); color: rgb(12, 35, 64);">'
        f"{head_html}</tr></thead><tbody>{body_html}</tbody></table></section>"
    )


def render_h2(number: int, title: str, english_title: str | None) -> str:
    english_html = ""
    if english_title:
        english_html = (
            '<p style="color: rgb(136, 136, 136); font-size: 13px; font-weight: normal; '
            'margin: 4px 0px 0px; letter-spacing: 0.5px; text-transform: uppercase;">'
            f"{html.escape(english_title)}</p>"
        )
    return (
        '<section style="margin-bottom: 25px; margin-top: 40px;"><section style="display: flex; '
        'align-items: flex-start;"><section style="width: 34px; height: 34px; '
        'background-color: rgb(212, 168, 67); color: rgb(255, 255, 255); font-size: 18px; '
        'font-weight: bold; text-align: center; line-height: 34px; margin-right: 12px; '
        f'flex-shrink: 0;">{number}</section><section style="flex: 1 1 0%;"><h2 style="color: '
        'rgb(12, 35, 64); font-size: 21px; font-weight: bold; margin: 0px;">'
        f'{html.escape(title)}</h2>{english_html}</section></section></section>'
    )


def render_summary_box(paragraphs: list[str]) -> str:
    if not paragraphs:
        return ""
    lead = paragraphs[0]
    tail = " ".join(paragraphs[1:]).strip()
    return (
        '<section style="background-color: rgb(248, 249, 250); border-radius: 4px; '
        'padding: 20px; margin-bottom: 30px; text-align: center;">'
        '<p style="color: rgb(12, 35, 64); font-size: 16px; font-weight: bold; '
        f'margin-bottom: 10px; text-align: justify;">{parse_inline(lead)}</p>'
        + (
            '<p style="color: rgb(51, 51, 51); font-size: 15px; margin-bottom: 20px; '
            f'text-align: justify;">{parse_inline(tail)}</p>'
            if tail
            else ""
        )
        + "</section>"
    )


def render_sources(items: list[str]) -> str:
    cleaned_items = [
        re.sub(r"https?://\S+", "", item).strip(" ,;，；")
        for item in items
        if item.strip()
    ]
    li_html = "".join(
        f'<li style="margin-bottom: 6px;">{html.escape(item)}</li>'
        for item in cleaned_items
        if item
    )
    return (
        '<section style="border-top: 1px solid #EEEEEE; padding-top: 20px; margin-bottom: 40px;">'
        '<p style="color: rgb(136, 136, 136); font-size: 14px; font-weight: bold; margin-bottom: 10px;">'
        "参考来源 / Sources"
        f"</p><ol style=\"color: rgb(136, 136, 136); font-size: 12px; line-height: 1.6; "
        f"padding-left: 20px; margin: 0; word-break: break-all;\">{li_html}</ol></section>"
    )


def build_html(
    input_path: Path,
    output_path: Path,
    image_mode: str = "placeholder",
    normalize_before_export: bool = True,
) -> None:
    if normalize_before_export:
        normalize_images(input_path, input_path.parent / "images")

    lines = input_path.read_text(encoding="utf-8").splitlines()
    base_dir = input_path.parent

    started_body = False
    first_h1_consumed = False
    current_section_is_sources = False
    current_section_is_summary = False
    h2_index = 0

    body_parts: list[str] = []
    paragraph_buffer: list[str] = []
    list_buffer: list[str] = []
    list_ordered = False
    blockquote_buffer: list[str] = []
    table_buffer: list[list[str]] = []
    source_items: list[str] = []
    summary_paragraphs: list[str] = []
    image_index = 0

    def flush_paragraph() -> None:
        nonlocal paragraph_buffer
        if not paragraph_buffer:
            return
        text = " ".join(line.strip() for line in paragraph_buffer).strip()
        if not text:
            paragraph_buffer = []
            return
        if current_section_is_sources:
            source_items.append(text)
        elif current_section_is_summary:
            summary_paragraphs.append(text)
        else:
            body_parts.append(render_paragraph(text))
        paragraph_buffer = []

    def flush_list() -> None:
        nonlocal list_buffer
        if not list_buffer:
            return
        if current_section_is_sources:
            source_items.extend(list_buffer)
        else:
            body_parts.append(render_list(list_buffer, list_ordered))
        list_buffer = []

    def flush_blockquote() -> None:
        nonlocal blockquote_buffer
        if blockquote_buffer:
            body_parts.append(render_blockquote(blockquote_buffer))
            blockquote_buffer = []

    def flush_table() -> None:
        nonlocal table_buffer
        if table_buffer:
            body_parts.append(render_table(table_buffer))
            table_buffer = []

    def flush_all() -> None:
        flush_paragraph()
        flush_list()
        flush_blockquote()
        flush_table()

    for raw_line in lines:
        line = raw_line.rstrip("\n")
        stripped = line.strip()

        if not started_body and stripped and not first_h1_consumed:
            heading_match = HEADING_RE.match(stripped)
            if heading_match and len(heading_match.group(1)) == 1:
                first_h1_consumed = True
                continue

        if not started_body and first_h1_consumed and stripped:
            meta_match = META_RE.match(stripped)
            if meta_match:
                continue
            started_body = True

        if table_buffer and is_table_divider(stripped):
            continue

        if "|" in stripped and stripped.startswith("|") and stripped.endswith("|"):
            flush_paragraph()
            flush_list()
            flush_blockquote()
            table_buffer.append(split_table_row(stripped))
            continue
        if table_buffer and not (stripped.startswith("|") and stripped.endswith("|")):
            flush_table()

        if not stripped:
            flush_all()
            continue

        image_match = IMAGE_RE.match(stripped)
        if image_match:
            flush_all()
            image_index += 1
            body_parts.append(
                render_image(base_dir, image_match.group(1), image_match.group(2), image_mode, image_index)
            )
            continue

        heading_match = HEADING_RE.match(stripped)
        if heading_match:
            flush_all()
            level = len(heading_match.group(1))
            content = heading_match.group(2).strip()

            current_section_is_sources = is_source_heading(content)
            current_section_is_summary = is_summary_heading(content) and not current_section_is_sources

            if level == 1:
                continue
            if current_section_is_sources:
                continue
            if current_section_is_summary:
                continue
            if level == 2:
                h2_index += 1
                zh_title, en_title = split_heading_text(content)
                body_parts.append(render_h2(h2_index, zh_title, en_title))
            elif level == 3:
                body_parts.append(render_h3(content))
            continue

        if stripped == "---":
            flush_all()
            body_parts.append(
                '<hr style="border-right: none; border-bottom: none; border-left: none; '
                'border-top: 1px solid rgb(212, 168, 67); margin: 40px 0px;">'
            )
            continue

        if stripped.startswith(">"):
            flush_paragraph()
            flush_list()
            flush_table()
            blockquote_buffer.append(stripped[1:].strip())
            continue

        ul_match = UL_RE.match(stripped)
        if ul_match:
            flush_paragraph()
            flush_blockquote()
            flush_table()
            if list_buffer and list_ordered:
                flush_list()
            list_ordered = False
            list_buffer.append(ul_match.group(1).strip())
            continue

        ol_match = OL_RE.match(stripped)
        if ol_match:
            flush_paragraph()
            flush_blockquote()
            flush_table()
            if list_buffer and not list_ordered:
                flush_list()
            list_ordered = True
            list_buffer.append(ol_match.group(1).strip())
            continue

        paragraph_buffer.append(stripped)

    flush_all()

    if summary_paragraphs:
        body_parts.append(render_summary_box(summary_paragraphs))
    if source_items:
        body_parts.append(render_sources(source_items))

    final_html = (
        '<section style="max-width: 600px; margin: 0px auto; background-color: rgb(255, 255, 255); '
        "font-family: 'Plus Jakarta Sans', 'Noto Sans SC', 'PingFang SC', 'Microsoft YaHei', sans-serif; "
        'color: rgb(51, 51, 51); line-height: 2em; font-size: 16px; letter-spacing: 0.5px; '
        'overflow-wrap: break-word; padding: 0px 10px;">'
        + "".join(body_parts)
        + "</section>\n"
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(final_html, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="把 Markdown 转换成适合微信公众号粘贴发布的 HTML。")
    parser.add_argument("input_md", type=Path, help="输入 Markdown 文件路径。")
    parser.add_argument("output_html", type=Path, help="输出 HTML 文件路径。")
    parser.add_argument(
        "--image-mode",
        choices=("placeholder", "local"),
        default="placeholder",
        help="图片输出模式：placeholder 为无图占位标记版，local 为本地路径图片版。",
    )
    parser.add_argument(
        "--skip-normalize-images",
        action="store_true",
        help="跳过导出前的图片顺序规范化。",
    )
    args = parser.parse_args()
    build_html(
        args.input_md,
        args.output_html,
        image_mode=args.image_mode,
        normalize_before_export=not args.skip_normalize_images,
    )


if __name__ == "__main__":
    main()
