#!/usr/bin/env python3
"""
扫描当前工作目录下已完成或进行中的文章项目，提取标题、中心判断和机制问题，
生成一个供选题去重使用的索引文件。
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


ARTICLE_NAME = "article.md"
RESEARCH_NAME = "research.md"

RESEARCH_LABELS = (
    "最终题目",
    "中心判断",
    "文章核心判断",
    "核心判断",
    "文章要回答的问题",
    "机制问题",
)


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


def first_heading(markdown: str) -> str:
    for line in markdown.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip()
    return ""


def extract_labeled_blocks(text: str) -> dict[str, list[str]]:
    lines = text.splitlines()
    result: dict[str, list[str]] = {label: [] for label in RESEARCH_LABELS}
    current_label: str | None = None

    for raw in lines:
        line = raw.rstrip()
        stripped = line.strip()
        matched = False

        for label in RESEARCH_LABELS:
            prefix = f"{label}："
            prefix2 = f"{label}:"
            if stripped.startswith(prefix) or stripped.startswith(prefix2):
                value = stripped.split("：", 1)[1] if "：" in stripped else stripped.split(":", 1)[1]
                value = value.strip()
                if value:
                    result[label].append(value)
                current_label = label
                matched = True
                break

        if matched:
            continue

        if stripped.startswith("#"):
            current_label = None
            continue

        if current_label and stripped.startswith(("- ", "* ", "+ ", "1. ", "2. ", "3. ", "4. ", "5. ")):
            item = re.sub(r"^\s*(?:[-*+]|\d+\.)\s*", "", stripped)
            if item:
                result[current_label].append(item)
            continue

        if current_label and stripped:
            result[current_label].append(stripped)
            current_label = None

    return {key: values for key, values in result.items() if values}


def project_candidates(root: Path) -> list[Path]:
    candidates: list[Path] = []
    for path in sorted(root.iterdir()):
        if not path.is_dir():
            continue
        if path.name.startswith(".") or path.name == "__pycache__":
            continue
        if (path / ARTICLE_NAME).exists() or (path / RESEARCH_NAME).exists():
            candidates.append(path)
    return candidates


def build_entry(project_dir: Path) -> dict[str, object]:
    article_path = project_dir / ARTICLE_NAME
    research_path = project_dir / RESEARCH_NAME

    article_text = read_text(article_path)
    research_text = read_text(research_path)
    labels = extract_labeled_blocks(research_text)

    title = first_heading(article_text) or project_dir.name
    output_files = sorted(
        path.name
        for path in project_dir.iterdir()
        if path.is_file() and path.suffix.lower() in {".docx", ".html"}
    )

    return {
        "project_dir": str(project_dir),
        "folder_name": project_dir.name,
        "title": title,
        "final_topic": labels.get("最终题目", []),
        "center_judgments": labels.get("中心判断", []) + labels.get("文章核心判断", []) + labels.get("核心判断", []),
        "mechanism_questions": labels.get("机制问题", []) + labels.get("文章要回答的问题", []),
        "outputs": output_files,
    }


def render_markdown(entries: list[dict[str, object]], root: Path) -> str:
    lines = [
        "# AI选题索引",
        "",
        f"- 生成目录：`{root}`",
        f"- 项目数：`{len(entries)}`",
        "",
        "这个索引用于自主选题前的去重检查。重点不是只看标题，而是看旧稿到底在回答什么问题。",
        "",
    ]

    for index, entry in enumerate(entries, start=1):
        lines.append(f"## {index}. {entry['title']}")
        lines.append("")
        lines.append(f"- 项目目录：`{entry['folder_name']}`")
        outputs = entry["outputs"]
        if outputs:
            lines.append(f"- 成品文件：`{'`、`'.join(outputs)}`")
        final_topic = entry["final_topic"]
        if final_topic:
            lines.append(f"- 最终题目：`{'；'.join(final_topic)}`")
        judgments = entry["center_judgments"]
        if judgments:
            lines.append("- 中心判断：")
            for item in judgments:
                lines.append(f"  - {item}")
        questions = entry["mechanism_questions"]
        if questions:
            lines.append("- 机制问题：")
            for item in questions:
                lines.append(f"  - {item}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="扫描当前工作目录下的历史文章选题，并生成索引。")
    parser.add_argument(
        "root",
        nargs="?",
        default=".",
        help="要扫描的根目录，默认当前目录。",
    )
    parser.add_argument(
        "--output-md",
        default="AI选题索引.md",
        help="输出 Markdown 索引文件名，默认 AI选题索引.md。",
    )
    parser.add_argument(
        "--output-json",
        default="AI选题索引.json",
        help="输出 JSON 索引文件名，默认 AI选题索引.json。",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(args.root).expanduser().resolve()

    entries = [build_entry(path) for path in project_candidates(root)]
    md_path = root / args.output_md
    json_path = root / args.output_json

    md_path.write_text(render_markdown(entries, root), encoding="utf-8")
    json_path.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"indexed {len(entries)} projects")
    print(f"markdown {md_path}")
    print(f"json {json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
