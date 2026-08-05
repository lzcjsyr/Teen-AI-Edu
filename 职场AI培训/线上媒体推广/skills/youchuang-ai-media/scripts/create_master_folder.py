#!/usr/bin/env python3
"""创建优创Hub AI内容母版目录。"""

from __future__ import annotations

import argparse
import re
from datetime import date
from pathlib import Path


FILES = [
    ("master_content.md", "# 内容母版\n\n"),
]


def slugify(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r"[\\/:*?\"<>|#%&{}$!'@+`=]", "", text)
    text = re.sub(r"\s+", "-", text)
    text = text.strip(".-")
    return text[:48] or "ai-topic"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("title", help="短选题标题")
    parser.add_argument("--base", default="线上媒体推广/内容母版", help="内容母版输出目录")
    parser.add_argument("--date", default=date.today().strftime("%m%d"), help="MMDD")
    args = parser.parse_args()

    folder = Path(args.base) / f"{slugify(args.title)}-{args.date}"

    folder.mkdir(parents=True, exist_ok=False)
    (folder / "sources").mkdir()

    for filename, content in FILES:
        (folder / filename).write_text(content, encoding="utf-8")

    print(folder)


if __name__ == "__main__":
    main()
