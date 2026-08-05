#!/usr/bin/env python3
"""
根据本地 HTML 计划生成公众号 16:9 横图优先的极简关键词图。

计划文件支持两种格式：
1. 顶层为数组
2. 顶层为对象，且包含 images 数组

单条计划最少包含：
{
  "filename": "01-thesis.png",
  "html": "<section>...</section>"
}

支持两种输入方式：
- html: 直接提供完整 HTML 或 HTML 片段
- html_path: 提供一个 HTML 文件路径
"""

from __future__ import annotations

import argparse
import html
import json
import os
from pathlib import Path
from typing import Any

from playwright.sync_api import Browser, Playwright, sync_playwright


DEFAULT_SIZE = "2560x1440"
DEFAULT_BACKGROUND = "#f7f1e8"
SOURCE_DIRNAME = "_local_sources"
DEFAULT_REVIEW_SELECTOR = "[data-compose-root]"
DEFAULT_CAPTURE_PADDING = 32


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate minimal 16:9 local explainer images from HTML plans.")
    parser.add_argument("plan", help="Path to the image plan JSON file.")
    parser.add_argument(
        "--output-dir",
        help="Directory to store generated images. Defaults to <plan_dir>/images.",
    )
    parser.add_argument(
        "--size",
        default=DEFAULT_SIZE,
        help="Default image size. Built-in default: 2560x1440.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing files with the same name.",
    )
    return parser.parse_args()


def load_plan(path: Path) -> list[dict[str, Any]]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(raw, list):
        items = raw
    elif isinstance(raw, dict) and isinstance(raw.get("images"), list):
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
        normalized.append(normalize_local_item(item, index))
    return normalized


def normalize_local_item(item: dict[str, Any], index: int) -> dict[str, Any]:
    spec = item.get("spec")
    if spec is not None and not isinstance(spec, dict):
        raise ValueError(f"Plan item #{index} has a non-object 'spec'.")

    merged = dict(spec or {})
    merged.update({k: v for k, v in item.items() if k != "spec"})

    html_value = merged.get("html")
    html_path_value = merged.get("html_path")

    has_html = isinstance(html_value, str) and bool(html_value.strip())
    has_html_path = isinstance(html_path_value, str) and bool(html_path_value.strip())

    if has_html and has_html_path:
        raise ValueError(f"Plan item #{index} cannot provide both 'html' and 'html_path'. Pick one.")
    if not has_html and not has_html_path:
        raise ValueError(f"Plan item #{index} must provide a non-empty 'html' or 'html_path'.")
    return merged


def parse_size(size: str) -> tuple[int, int]:
    try:
        width_str, height_str = size.lower().split("x", 1)
        width = int(width_str)
        height = int(height_str)
    except ValueError as error:
        raise ValueError(f"Invalid size '{size}'. Expected WIDTHxHEIGHT, for example 2560x1440.") from error

    if width <= 0 or height <= 0:
        raise ValueError(f"Invalid size '{size}'. Width and height must be positive.")
    return width, height


def escape_text(value: Any) -> str:
    return html.escape("" if value is None else str(value))


def render_document(item: dict[str, Any], document: str, width: int, height: int) -> str:
    if "<html" in document.lower():
        return document

    background = escape_text(item.get("background", DEFAULT_BACKGROUND))
    title = escape_text(item.get("title", Path(item["filename"]).stem))

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{title}</title>
  <style>
    :root {{
      --bg: {background};
      --text: #5c3321;
    }}

    * {{
      box-sizing: border-box;
    }}

    html, body {{
      width: {width}px;
      height: {height}px;
      margin: 0;
      overflow: hidden;
      background:
        radial-gradient(circle at 18% 14%, rgba(255, 255, 255, 0.92), transparent 26%),
        linear-gradient(180deg, #fcf7f0 0%, var(--bg) 100%);
      color: var(--text);
      font-family: "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
    }}

    body {{
      position: relative;
    }}

    img, svg, canvas {{
      max-width: 100%;
      max-height: 100%;
      display: block;
    }}

    #app {{
      width: 100%;
      height: 100%;
    }}
  </style>
</head>
<body>
  <div id="app">
    {document}
  </div>
</body>
</html>
"""


class LocalScreenshotRenderer:
    def __init__(self) -> None:
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None

    def __enter__(self) -> "LocalScreenshotRenderer":
        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if self._browser is not None:
            self._browser.close()
        if self._playwright is not None:
            self._playwright.stop()

    def review_layout(self, page, selector: str) -> dict[str, Any]:
        result = page.evaluate(
            """
            ({ selector }) => {
              const viewportWidth = window.innerWidth;
              const viewportHeight = window.innerHeight;
              const node = document.querySelector(selector);
              if (!node) {
                return {
                  found: false,
                  selector,
                  viewportWidth,
                  viewportHeight,
                };
              }

              const rect = node.getBoundingClientRect();
              const widthRatio = rect.width / viewportWidth;
              const heightRatio = rect.height / viewportHeight;
              const areaRatio = (rect.width * rect.height) / (viewportWidth * viewportHeight);
              const warnings = [];

              if (widthRatio < 0.68) warnings.push("构图宽度占比偏小");
              if (heightRatio < 0.52) warnings.push("构图高度占比偏小");
              if (areaRatio < 0.38) warnings.push("构图整体覆盖率偏低");

              return {
                found: true,
                selector,
                viewportWidth,
                viewportHeight,
                x: rect.x,
                y: rect.y,
                width: rect.width,
                height: rect.height,
                widthRatio,
                heightRatio,
                areaRatio,
                warnings,
              };
            }
            """,
            {"selector": selector},
        )
        if not result.get("found"):
            result["warnings"] = [f"未找到 review selector: {selector}"]
        return result

    def screenshot(
        self,
        html_path: Path,
        destination: Path,
        size: str,
        capture_selector: str | None = None,
        capture_padding: int = DEFAULT_CAPTURE_PADDING,
        review_selector: str = DEFAULT_REVIEW_SELECTOR,
    ) -> dict[str, Any]:
        if self._browser is None:
            raise RuntimeError("Renderer is not started.")

        width, height = parse_size(size)
        page = self._browser.new_page(viewport={"width": width, "height": height}, device_scale_factor=1)
        try:
            page.goto(html_path.as_uri(), wait_until="load")
            page.wait_for_timeout(120)
            review = self.review_layout(page, review_selector)

            screenshot_kwargs: dict[str, Any] = {}
            selector_to_use = capture_selector
            if not selector_to_use:
                try:
                    if page.query_selector("[data-capture-root]"):
                        selector_to_use = "[data-capture-root]"
                except Exception:
                    pass

            if selector_to_use:
                locator = page.locator(selector_to_use).first
                box = locator.bounding_box()
                if box is None:
                    raise ValueError(f"Capture selector not found or not visible: {selector_to_use}")

                padding = max(0, int(capture_padding))
                clip_x = max(0, box["x"] - padding)
                clip_y = max(0, box["y"] - padding)
                clip_width = min(width - clip_x, box["width"] + padding * 2)
                clip_height = min(height - clip_y, box["height"] + padding * 2)
                screenshot_kwargs["clip"] = {
                    "x": clip_x,
                    "y": clip_y,
                    "width": clip_width,
                    "height": clip_height,
                }

            suffix = destination.suffix.lower()
            if suffix in {".jpg", ".jpeg"}:
                page.screenshot(path=str(destination), type="jpeg", quality=92, **screenshot_kwargs)
            else:
                page.screenshot(path=str(destination), type="png", **screenshot_kwargs)
            return review
        finally:
            page.close()


def infer_output_filename(item: dict[str, Any]) -> str:
    filename = item["filename"]
    suffix = Path(filename).suffix.lower()
    if suffix in {".png", ".jpg", ".jpeg"}:
        return filename
    return f"{Path(filename).stem}.png"


def write_source_files(item: dict[str, Any], source_dir: Path, item_base_dir: Path, size: str) -> tuple[Path, list[str]]:
    width, height = parse_size(size)
    stem = Path(item["filename"]).stem
    written: list[str] = []

    html_value = item.get("html")
    html_path_value = item.get("html_path")

    if isinstance(html_path_value, str) and html_path_value.strip():
        source_html_path = (item_base_dir / html_path_value).resolve()
        if not source_html_path.exists():
            raise FileNotFoundError(f"HTML source not found: {source_html_path}")
        html_document = source_html_path.read_text(encoding="utf-8")
        written.append(str(source_html_path))
        if "<html" in html_document.lower():
            return source_html_path, written
    elif isinstance(html_value, str) and html_value.strip():
        html_document = html_value
    else:
        raise ValueError("Local HTML items must provide 'html' or 'html_path'.")

    html_path = source_dir / f"{stem}.html"
    html_path.write_text(render_document(item, html_document, width, height), encoding="utf-8")
    written.append(str(html_path))
    return html_path, written


def generate_plan_item(
    item: dict[str, Any],
    output_dir: Path,
    markdown_base_dir: Path,
    default_size: str = DEFAULT_SIZE,
    overwrite: bool = False,
    renderer: LocalScreenshotRenderer | None = None,
) -> dict[str, Any]:
    size = item.get("size", default_size)
    destination = output_dir / infer_output_filename(item)
    if destination.exists() and not overwrite:
        raise FileExistsError(f"Refusing to overwrite existing file: {destination}")

    source_dir = output_dir / SOURCE_DIRNAME
    source_dir.mkdir(parents=True, exist_ok=True)
    html_path, source_files = write_source_files(item, source_dir, markdown_base_dir, size)

    owns_renderer = renderer is None
    active_renderer = renderer or LocalScreenshotRenderer()
    if owns_renderer:
        active_renderer.__enter__()
    try:
        review = active_renderer.screenshot(
            html_path,
            destination,
            size=size,
            capture_selector=item.get("capture_selector"),
            capture_padding=item.get("capture_padding", DEFAULT_CAPTURE_PADDING),
            review_selector=item.get("review_selector", DEFAULT_REVIEW_SELECTOR),
        )
    finally:
        if owns_renderer:
            active_renderer.__exit__(None, None, None)

    relative_path = os.path.relpath(destination, markdown_base_dir)
    alt_text = item.get("alt", "")
    markdown = f"![{alt_text}]({relative_path})" if alt_text else f"![]({relative_path})"

    return {
        "generator": "local-html",
        "filename": destination.name,
        "path": str(destination),
        "markdown": markdown,
        "alt": alt_text,
        "size": size,
        "source_files": source_files,
        "layout_review": review,
        "review_status": "pending_visual_review",
        "review_checklist": [
            "居中与对齐正常",
            "文字未出框且未贴边过近",
            "颜色搭配与对比合理",
            "信息层级清楚",
            "手机宽度下仍可快速扫读",
            "构图主体覆盖大部分画布，没有只占中间一小块",
        ],
    }


def main() -> int:
    args = parse_args()

    plan_path = Path(args.plan).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve() if args.output_dir else plan_path.parent / "images"
    output_dir.mkdir(parents=True, exist_ok=True)

    items = load_plan(plan_path)
    manifest: list[dict[str, Any]] = []

    with LocalScreenshotRenderer() as renderer:
        for item in items:
            saved = generate_plan_item(
                item,
                output_dir,
                plan_path.parent,
                default_size=args.size,
                overwrite=args.overwrite,
                renderer=renderer,
            )
            manifest.append(saved)
            print(f"saved {saved['filename']}")
            warnings = saved.get("layout_review", {}).get("warnings", [])
            if warnings:
                print(f"layout warnings for {saved['filename']}: {'; '.join(warnings)}")

    manifest_path = output_dir / "generated-image-manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"manifest {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
