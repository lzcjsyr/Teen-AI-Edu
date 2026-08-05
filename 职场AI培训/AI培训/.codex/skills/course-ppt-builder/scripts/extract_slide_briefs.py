#!/usr/bin/env python3
"""从按课程页组织的 Markdown 文件中提取每页内容。"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


SLIDE_HEADING_RE = re.compile(r"^####\s*【第\s*(\d+)\s*页：(.+?)】\s*$")


def extract_slides(markdown_text: str) -> list[dict[str, object]]:
    lines = markdown_text.splitlines()
    slides: list[dict[str, object]] = []
    current: dict[str, object] | None = None
    body_lines: list[str] = []

    for line in lines:
        if current is not None and line.startswith("## 附录"):
            current["body"] = "\n".join(body_lines).strip()
            slides.append(current)
            current = None
            body_lines = []
            break

        match = SLIDE_HEADING_RE.match(line)
        if match:
            if current is not None:
                current["body"] = "\n".join(body_lines).strip()
                slides.append(current)
            current = {
                "page": int(match.group(1)),
                "title": match.group(2).strip(),
            }
            body_lines = []
            continue

        if current is not None:
            if re.match(r"^#{1,3}\s+", line) or line.strip() in {"---", "***"}:
                continue
            body_lines.append(line)

    if current is not None:
        current["body"] = "\n".join(body_lines).strip()
        slides.append(current)

    return slides


def main() -> None:
    parser = argparse.ArgumentParser(description="提取 Markdown 中的课程页内容")
    parser.add_argument("markdown", type=Path, help="输入 Markdown 文件")
    parser.add_argument("--out", type=Path, required=True, help="输出 JSON 文件")
    args = parser.parse_args()

    text = args.markdown.read_text(encoding="utf-8")
    slides = extract_slides(text)
    if not slides:
        raise SystemExit("没有找到任何课程页。请检查标题格式是否为：#### 【第 N 页：标题】")

    pages = [slide["page"] for slide in slides]
    expected = list(range(min(pages), max(pages) + 1))
    if pages != expected:
        raise SystemExit(f"页码不连续或顺序异常：找到 {pages}，期望 {expected}")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(
            {
                "source": str(args.markdown),
                "slide_count": len(slides),
                "slides": slides,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print(f"已提取 {len(slides)} 页：{args.out}")


if __name__ == "__main__":
    main()
