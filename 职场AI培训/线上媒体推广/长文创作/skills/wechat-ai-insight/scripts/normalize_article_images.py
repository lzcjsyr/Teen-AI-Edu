#!/usr/bin/env python3
"""
按文章中的图片出现顺序，规范 images/ 目录中的文件名，并把未使用图片移到 _unused/。

默认行为：
- 只重命名 Markdown 中实际引用到的图片
- 新文件名格式：01-<slug>.<ext>
- 未使用的图片移动到 images/_unused/
- 自动回写 article.md 中的图片路径
"""

from __future__ import annotations

import argparse
import re
import shutil
from pathlib import Path


IMAGE_RE = re.compile(r"^!\[(.*?)\]\((.*?)\)\s*$", re.M)
SAFE_RE = re.compile(r"[^a-z0-9]+")


def slugify(text: str) -> str:
    ascii_text = text.strip().lower()
    ascii_text = SAFE_RE.sub("-", ascii_text)
    ascii_text = ascii_text.strip("-")
    return ascii_text or "image"


def build_slug(alt_text: str, source_path: Path) -> str:
    if alt_text.strip():
        return slugify(alt_text)
    return slugify(source_path.stem)


def normalize_images(article_path: Path, images_dir: Path) -> None:
    text = article_path.read_text(encoding="utf-8")
    matches = list(IMAGE_RE.finditer(text))
    if not matches:
        return

    used_paths: list[Path] = []
    replacements: list[tuple[str, str]] = []
    planned_moves: list[tuple[Path, Path]] = []
    reserved: set[Path] = set()

    for index, match in enumerate(matches, start=1):
        alt_text, raw_ref = match.group(1), match.group(2)
        source = Path(raw_ref)
        if not source.is_absolute():
            source = (article_path.parent / raw_ref).resolve()
        if not source.exists():
            raise FileNotFoundError(f"图片不存在：{source}")
        used_paths.append(source.resolve())

        slug = build_slug(alt_text, source)
        destination = images_dir / f"{index:02d}-{slug}{source.suffix.lower()}"
        counter = 2
        while destination in reserved and destination != source:
            destination = images_dir / f"{index:02d}-{slug}-{counter}{source.suffix.lower()}"
            counter += 1
        reserved.add(destination)
        planned_moves.append((source, destination))
        new_ref = f"images/{destination.name}"
        replacements.append((match.group(0), f"![{alt_text}]({new_ref})"))

    temp_moves: list[tuple[Path, Path]] = []
    for source, destination in planned_moves:
        if source.resolve() == destination.resolve():
            continue
        temp = source.with_name(f".__tmp__{source.name}")
        while temp.exists():
            temp = source.with_name(f".__tmp__x_{temp.name}")
        source.rename(temp)
        temp_moves.append((temp, destination))

    for temp, destination in temp_moves:
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            destination.unlink()
        temp.rename(destination)

    for old, new in replacements:
        text = text.replace(old, new, 1)
    article_path.write_text(text, encoding="utf-8")

    unused_dir = images_dir / "_unused"
    unused_dir.mkdir(exist_ok=True)
    used_resolved = {destination.resolve() for _, destination in planned_moves}
    for path in images_dir.iterdir():
        if not path.is_file():
            continue
        if path.resolve() in used_resolved:
            continue
        shutil.move(str(path), str(unused_dir / path.name))


def main() -> None:
    parser = argparse.ArgumentParser(description="按文章顺序规范 images 目录中的图片。")
    parser.add_argument("article_md", type=Path, help="文章 Markdown 路径。")
    parser.add_argument(
        "--images-dir",
        type=Path,
        default=None,
        help="图片目录。默认使用 <article_dir>/images",
    )
    args = parser.parse_args()

    article_path = args.article_md.expanduser().resolve()
    images_dir = (args.images_dir.expanduser().resolve() if args.images_dir else article_path.parent / "images")
    images_dir.mkdir(parents=True, exist_ok=True)
    normalize_images(article_path, images_dir)


if __name__ == "__main__":
    main()
