#!/usr/bin/env python3
"""
根据插图计划调用火山方舟 Seedream 文生图 API，下载图片到本地。

计划文件支持两种格式：
1. 顶层为数组
2. 顶层为对象，且包含 images 数组

单条图片计划最少包含：
{
  "filename": "01-opening.jpeg",
  "prompt": "..."
}

可选字段：
- alt: 用于 Markdown 图片 alt 文本；若希望 DOCX 不显示图注，建议置空
- size: 覆盖默认尺寸
"""

from __future__ import annotations

import argparse
import base64
from dataclasses import dataclass
import json
import os
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


DEFAULT_ENDPOINT = "https://ark.cn-beijing.volces.com/api/v3/images/generations"
DEFAULT_MODEL = "doubao-seedream-5-0-260128"
DEFAULT_SIZE = "2560x1440"  # 16:9
DEFAULT_OUTPUT_FORMAT = "jpeg"
DEFAULT_RESPONSE_FORMAT = "url"
DEFAULT_WATERMARK = False
DEFAULT_SEQUENTIAL_IMAGE_GENERATION = "disabled"
DEFAULT_STREAM = False
PROJECT_ROOT = Path(__file__).resolve().parents[3]


@dataclass(frozen=True)
class SeedreamConfig:
    api_key: str
    endpoint: str = DEFAULT_ENDPOINT
    model: str = DEFAULT_MODEL


def parse_env_line(line: str) -> tuple[str, str] | None:
    stripped = line.strip()
    if not stripped or stripped.startswith("#") or "=" not in stripped:
        return None
    key, value = stripped.split("=", 1)
    key = key.strip()
    value = value.strip().strip('"').strip("'")
    if not key:
        return None
    return key, value


def load_env_file(path: Path = PROJECT_ROOT / ".env") -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        parsed = parse_env_line(line)
        if parsed is None:
            continue
        key, value = parsed
        os.environ.setdefault(key, value)


def load_seedream_config(env_path: Path = PROJECT_ROOT / ".env") -> SeedreamConfig:
    load_env_file(env_path)
    api_key = os.environ.get("ARK_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError(
            "Missing ARK_API_KEY. Add it to the project .env file or set it as an environment variable."
        )
    endpoint = os.environ.get("ARK_ENDPOINT", DEFAULT_ENDPOINT).strip() or DEFAULT_ENDPOINT
    model = os.environ.get("ARK_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL
    return SeedreamConfig(api_key=api_key, endpoint=endpoint, model=model)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate local images from a Seedream image plan.")
    parser.add_argument("plan", help="Path to the image plan JSON file.")
    parser.add_argument(
        "--output-dir",
        help="Directory to store generated images. Defaults to <plan_dir>/images.",
    )
    parser.add_argument(
        "--size",
        default=DEFAULT_SIZE,
        help="Default image size. The built-in default is a 16:9 frame: 2560x1440.",
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
        prompt = item.get("prompt")
        if not filename or not isinstance(filename, str):
            raise ValueError(f"Plan item #{index} is missing a string 'filename'.")
        if not prompt or not isinstance(prompt, str):
            raise ValueError(f"Plan item #{index} is missing a string 'prompt'.")
        normalized.append(item)
    return normalized


def post_json(url: str, payload: dict[str, Any], api_key: str) -> dict[str, Any]:
    request = Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    try:
        with urlopen(request) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"API request failed with HTTP {error.code}: {body}") from error
    except URLError as error:
        raise RuntimeError(f"API request failed: {error}") from error


def download_file(url: str, destination: Path) -> None:
    request = Request(url, headers={"User-Agent": "codex-seedream-image-fetcher"})
    try:
        with urlopen(request) as response:
            destination.write_bytes(response.read())
    except HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Image download failed with HTTP {error.code}: {body}") from error
    except URLError as error:
        raise RuntimeError(f"Image download failed: {error}") from error


def infer_suffix(item: dict[str, Any], fallback: str) -> str:
    filename = item["filename"]
    suffix = Path(filename).suffix.lower()
    if suffix:
        return suffix
    return ".png" if fallback == "png" else ".jpg"


def generate_doubao_image(prompt: str, size: str = DEFAULT_SIZE) -> dict[str, Any]:
    config = load_seedream_config()
    payload: dict[str, Any] = {
        "model": config.model,
        "prompt": prompt,
        "sequential_image_generation": DEFAULT_SEQUENTIAL_IMAGE_GENERATION,
        "response_format": DEFAULT_RESPONSE_FORMAT,
        "size": size,
        "stream": DEFAULT_STREAM,
        "watermark": DEFAULT_WATERMARK,
        "output_format": DEFAULT_OUTPUT_FORMAT,
    }
    return post_json(config.endpoint, payload, config.api_key)


def save_from_response(
    response: dict[str, Any],
    item: dict[str, Any],
    output_dir: Path,
    markdown_base_dir: Path,
    fallback_output_format: str,
    overwrite: bool,
) -> dict[str, Any]:
    data = response.get("data")
    if not isinstance(data, list) or not data:
        raise RuntimeError(f"API response does not contain generated image data: {response}")

    first = data[0]
    if not isinstance(first, dict):
        raise RuntimeError(f"Unexpected image data item: {first}")

    suffix = infer_suffix(item, item.get("output_format", fallback_output_format))
    destination = output_dir / Path(item["filename"]).with_suffix(suffix).name
    if destination.exists() and not overwrite:
        raise FileExistsError(f"Refusing to overwrite existing file: {destination}")

    if "url" in first:
        download_file(first["url"], destination)
    elif "b64_json" in first:
        destination.write_bytes(base64.b64decode(first["b64_json"]))
    else:
        raise RuntimeError(f"API response does not contain url or b64_json: {first}")

    relative_path = os.path.relpath(destination, markdown_base_dir)
    alt_text = item.get("alt", "")
    markdown = f"![{alt_text}]({relative_path})" if alt_text else f"![]({relative_path})"

    return {
        "generator": "seedream",
        "filename": destination.name,
        "path": str(destination),
        "markdown": markdown,
        "prompt": item["prompt"],
        "alt": alt_text,
        "api_size": first.get("size"),
    }


def generate_plan_item(
    item: dict[str, Any],
    output_dir: Path,
    markdown_base_dir: Path,
    default_size: str = DEFAULT_SIZE,
    overwrite: bool = False,
) -> dict[str, Any]:
    size = item.get("size", default_size)
    response = generate_doubao_image(item["prompt"], size=size)
    saved = save_from_response(
        response,
        item,
        output_dir,
        markdown_base_dir,
        DEFAULT_OUTPUT_FORMAT,
        overwrite,
    )
    saved["requested_size"] = size
    return saved


def main() -> int:
    args = parse_args()

    plan_path = Path(args.plan).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve() if args.output_dir else plan_path.parent / "images"
    output_dir.mkdir(parents=True, exist_ok=True)

    items = load_plan(plan_path)
    manifest: list[dict[str, Any]] = []

    for item in items:
        saved = generate_plan_item(
            item,
            output_dir,
            plan_path.parent,
            default_size=args.size,
            overwrite=args.overwrite,
        )
        manifest.append(saved)
        print(f"saved {saved['filename']}")

    manifest_path = output_dir / "generated-image-manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"manifest {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
