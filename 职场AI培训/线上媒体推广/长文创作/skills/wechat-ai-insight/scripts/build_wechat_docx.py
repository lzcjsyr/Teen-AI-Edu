#!/usr/bin/env python3
"""
把 Markdown 文章转换成适合微信公众号后台导入的保守版 DOCX。

支持的 Markdown 子集：
- #、##、### 标题
- 普通段落
- 无序列表：-、*、+
- 有序列表：1.
- 引用：>
- 加粗：**text**
- 行内代码：`text`
- 独占一行的图片：![alt](path)

约定：
- 第一个一级标题只作为文章标题元信息，不写入正文。
- 正文主体章节使用二级标题，导出后会居中、加粗，并比正文大一号。
- “来源 / 信息来源 / 参考资料”等章节前会自动插入明显分隔线，并统一输出为“信息来源”。
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml.parser import OxmlElement
from docx.shared import Inches, Pt
from normalize_article_images import normalize_images


HEADING_RE = re.compile(r"^(#{1,3})\s+(.*)$")
UL_RE = re.compile(r"^\s*[-*+]\s+(.*)$")
OL_RE = re.compile(r"^\s*\d+\.\s+(.*)$")
IMAGE_RE = re.compile(r"^!\[(.*?)\]\((.*?)\)\s*$")
INLINE_RE = re.compile(r"(\*\*.*?\*\*|`.*?`)")
SOURCE_HEADING_KEYWORDS = (
    "信息来源",
    "来源",
    "参考资料",
    "参考来源",
    "资料来源",
    "参考文献",
    "参考链接",
)
SOURCE_DIVIDER_TEXT = "------------------------------"
STANDARD_SOURCE_HEADING = "信息来源"


def set_east_asia_font(style, font_name: str) -> None:
    rpr = style.element.get_or_add_rPr()
    rfonts = rpr.rFonts
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.append(rfonts)
    rfonts.set(qn("w:eastAsia"), font_name)
    rfonts.set(qn("w:ascii"), font_name)
    rfonts.set(qn("w:hAnsi"), font_name)


def set_run_font(run, ascii_font: str, east_asia_font: str | None = None, size: Pt | None = None) -> None:
    run.font.name = ascii_font
    if size is not None:
        run.font.size = size

    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.rFonts
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.append(rfonts)

    east_asia = east_asia_font or ascii_font
    rfonts.set(qn("w:eastAsia"), east_asia)
    rfonts.set(qn("w:ascii"), ascii_font)
    rfonts.set(qn("w:hAnsi"), ascii_font)


def configure_document(doc: Document) -> None:
    section = doc.sections[0]
    section.top_margin = Inches(0.75)
    section.bottom_margin = Inches(0.75)
    section.left_margin = Inches(0.75)
    section.right_margin = Inches(0.75)

    normal = doc.styles["Normal"]
    normal.font.name = "Aptos"
    normal.font.size = Pt(11)
    set_east_asia_font(normal, "等线")
    normal.paragraph_format.space_after = Pt(10)
    normal.paragraph_format.line_spacing = 1.35

    title = doc.styles["Title"]
    title.font.name = "Aptos"
    title.font.size = Pt(20)
    title.font.bold = True
    set_east_asia_font(title, "等线")
    title.paragraph_format.space_after = Pt(14)

    heading_1 = doc.styles["Heading 1"]
    heading_1.font.name = "Aptos"
    heading_1.font.size = Pt(13)
    heading_1.font.bold = True
    set_east_asia_font(heading_1, "等线")
    heading_1.paragraph_format.space_before = Pt(12)
    heading_1.paragraph_format.space_after = Pt(6)

    heading_2 = doc.styles["Heading 2"]
    heading_2.font.name = "Aptos"
    heading_2.font.size = Pt(12)
    heading_2.font.bold = True
    set_east_asia_font(heading_2, "等线")
    heading_2.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    heading_2.paragraph_format.space_before = Pt(16)
    heading_2.paragraph_format.space_after = Pt(8)

    heading_3 = doc.styles["Heading 3"]
    heading_3.font.name = "Aptos"
    heading_3.font.size = Pt(11.5)
    heading_3.font.bold = True
    set_east_asia_font(heading_3, "等线")
    heading_3.paragraph_format.space_before = Pt(10)
    heading_3.paragraph_format.space_after = Pt(6)

    quote = doc.styles["Quote"]
    quote.font.name = "Aptos"
    quote.font.size = Pt(10.5)
    set_east_asia_font(quote, "等线")


def add_runs(paragraph, text: str) -> None:
    parts = INLINE_RE.split(text)
    for part in parts:
        if not part:
            continue
        if part.startswith("**") and part.endswith("**"):
            run = paragraph.add_run(part[2:-2])
            run.bold = True
        elif part.startswith("`") and part.endswith("`"):
            run = paragraph.add_run(part[1:-1])
            set_run_font(run, "Menlo", size=Pt(10))
        else:
            paragraph.add_run(part)


def normalize_heading_text(text: str) -> str:
    cleaned = re.sub(r"^[^A-Za-z0-9\u4e00-\u9fff]+", "", text).strip()
    return cleaned.strip("：: ").replace(" ", "")


def is_source_heading(text: str) -> bool:
    normalized = normalize_heading_text(text)
    return any(keyword in normalized for keyword in SOURCE_HEADING_KEYWORDS)


def add_source_divider(doc: Document) -> None:
    paragraph = doc.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    paragraph.paragraph_format.space_before = Pt(18)
    paragraph.paragraph_format.space_after = Pt(8)
    run = paragraph.add_run(SOURCE_DIVIDER_TEXT)
    set_run_font(run, "Aptos", "等线", Pt(10))


def add_image(doc: Document, base_dir: Path, alt_text: str, image_ref: str) -> None:
    image_path = Path(image_ref)
    if not image_path.is_absolute():
        image_path = (base_dir / image_ref).resolve()
    if not image_path.exists():
        placeholder = doc.add_paragraph()
        placeholder.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = placeholder.add_run(f"[图片缺失，导出时未插入：{image_path.name}]")
        set_run_font(run, "Aptos", "等线", Pt(10))
        if alt_text:
            caption = doc.add_paragraph(alt_text)
            caption.alignment = WD_ALIGN_PARAGRAPH.CENTER
        return

    paragraph = doc.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = paragraph.add_run()
    run.add_picture(str(image_path), width=Inches(5.4))

    if alt_text:
        caption = doc.add_paragraph(alt_text)
        caption.alignment = WD_ALIGN_PARAGRAPH.CENTER


def build_docx(input_path: Path, output_path: Path, normalize_before_export: bool = True) -> None:
    if normalize_before_export:
        normalize_images(input_path, input_path.parent / "images")

    lines = input_path.read_text(encoding="utf-8").splitlines()
    doc = Document()
    configure_document(doc)
    doc.core_properties.title = output_path.stem
    base_dir = input_path.parent

    buffer: list[str] = []
    first_h1_skipped = False
    source_divider_added = False

    def flush_buffer() -> None:
        nonlocal buffer
        if not buffer:
            return
        text = " ".join(line.strip() for line in buffer).strip()
        if text:
            paragraph = doc.add_paragraph(style="Normal")
            add_runs(paragraph, text)
        buffer = []

    for raw_line in lines:
        line = raw_line.rstrip()
        stripped = line.strip()

        if not stripped:
            flush_buffer()
            continue

        image_match = IMAGE_RE.match(stripped)
        if image_match:
            flush_buffer()
            add_image(doc, base_dir, image_match.group(1), image_match.group(2))
            continue

        heading_match = HEADING_RE.match(stripped)
        if heading_match:
            flush_buffer()
            level = len(heading_match.group(1))
            content = heading_match.group(2).strip()
            if level == 1 and not first_h1_skipped:
                first_h1_skipped = True
                continue

            if is_source_heading(content):
                content = STANDARD_SOURCE_HEADING
                level = 2

            if not source_divider_added and content == STANDARD_SOURCE_HEADING:
                add_source_divider(doc)
                source_divider_added = True

            paragraph = doc.add_paragraph(style=f"Heading {level}")
            if level == 2:
                paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            add_runs(paragraph, content)
            continue

        ul_match = UL_RE.match(stripped)
        if ul_match:
            flush_buffer()
            paragraph = doc.add_paragraph(style="List Bullet")
            add_runs(paragraph, ul_match.group(1).strip())
            continue

        ol_match = OL_RE.match(stripped)
        if ol_match:
            flush_buffer()
            paragraph = doc.add_paragraph(style="List Number")
            add_runs(paragraph, ol_match.group(1).strip())
            continue

        if stripped.startswith(">"):
            flush_buffer()
            content = stripped[1:].strip()
            paragraph = doc.add_paragraph(style="Quote")
            add_runs(paragraph, content)
            continue

        buffer.append(stripped)

    flush_buffer()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(output_path)


def main() -> None:
    parser = argparse.ArgumentParser(description="把 Markdown 转换成适合微信公众号导入的 DOCX。")
    parser.add_argument("input_md", type=Path, help="输入 Markdown 文件路径。")
    parser.add_argument("output_docx", type=Path, help="输出 DOCX 文件路径。")
    parser.add_argument(
        "--skip-normalize-images",
        action="store_true",
        help="跳过导出前的图片顺序规范化。",
    )
    args = parser.parse_args()
    build_docx(args.input_md, args.output_docx, normalize_before_export=not args.skip_normalize_images)


if __name__ == "__main__":
    main()
