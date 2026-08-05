#!/usr/bin/env python3
"""
公众号文章统一生图入口。

默认使用 Seedream API。
如果计划文件顶层或单条图片显式指定 generator=local-html，
则切换到本地 HTML 截图模式。
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from generate_local_html_images import (
    DEFAULT_SIZE as LOCAL_DEFAULT_SIZE,
    LocalScreenshotRenderer,
    generate_plan_item as generate_local_item,
    normalize_local_item,
)
from generate_seedream_images import (
    DEFAULT_SIZE as API_DEFAULT_SIZE,
    generate_plan_item as generate_seedream_item,
)


GENERATOR_ALIASES = {
    "seedream": "seedream",
    "api": "seedream",
    "default": "seedream",
    "local": "local-html",
    "local-html": "local-html",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate article images with API or local HTML rendering.")
    parser.add_argument("plan", help="Path to the image plan JSON file.")
    parser.add_argument(
        "--output-dir",
        help="Directory to store generated images. Defaults to <plan_dir>/images.",
    )
    parser.add_argument(
        "--size",
        default=None,
        help=(
            "Optional global image size override. "
            f"Seedream default: {API_DEFAULT_SIZE}. Local HTML default: {LOCAL_DEFAULT_SIZE}."
        ),
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing files with the same name.",
    )
    return parser.parse_args()


def normalize_generator(value: Any) -> str:
    key = "seedream" if value is None else str(value).strip().lower()
    if key not in GENERATOR_ALIASES:
        raise ValueError(
            f"Unsupported generator '{value}'. Supported values: {', '.join(sorted(GENERATOR_ALIASES))}."
        )
    return GENERATOR_ALIASES[key]


def load_plan(path: Path) -> tuple[str, list[dict[str, Any]]]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(raw, list):
        default_generator = "seedream"
        items = raw
    elif isinstance(raw, dict) and isinstance(raw.get("images"), list):
        default_generator = normalize_generator(raw.get("generator"))
        items = raw["images"]
    else:
        raise ValueError("Image plan must be a list or an object with an 'images' list.")

    if not items:
        raise ValueError("Image plan is empty.")

    normalized: list[dict[str, Any]] = []
    for index, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"Plan item #{index} must be an object.")
        filename = item.get("filename")
        if not filename or not isinstance(filename, str):
            raise ValueError(f"Plan item #{index} is missing a string 'filename'.")

        generator = normalize_generator(item.get("generator", default_generator))
        prepared = dict(item)
        prepared["generator"] = generator

        if generator == "seedream":
            prompt = prepared.get("prompt")
            if not prompt or not isinstance(prompt, str):
                raise ValueError(f"Seedream item #{index} is missing a string 'prompt'.")
        else:
            prepared = normalize_local_item(prepared, index)
            prepared["generator"] = generator

        normalized.append(prepared)

    return default_generator, normalized


def main() -> int:
    args = parse_args()

    plan_path = Path(args.plan).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve() if args.output_dir else plan_path.parent / "images"
    output_dir.mkdir(parents=True, exist_ok=True)

    _, items = load_plan(plan_path)
    manifest: list[dict[str, Any]] = []
    local_default_size = args.size or LOCAL_DEFAULT_SIZE
    api_default_size = args.size or API_DEFAULT_SIZE

    with LocalScreenshotRenderer() as local_renderer:
        for item in items:
            if item["generator"] == "local-html":
                saved = generate_local_item(
                    item,
                    output_dir,
                    plan_path.parent,
                    default_size=local_default_size,
                    overwrite=args.overwrite,
                    renderer=local_renderer,
                )
            else:
                saved = generate_seedream_item(
                    item,
                    output_dir,
                    plan_path.parent,
                    default_size=api_default_size,
                    overwrite=args.overwrite,
                )

            manifest.append(saved)
            print(f"saved {saved['filename']} [{saved['generator']}]")
            warnings = saved.get("layout_review", {}).get("warnings", [])
            if warnings:
                print(f"layout warnings for {saved['filename']}: {'; '.join(warnings)}")

    manifest_path = output_dir / "generated-image-manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"manifest {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
