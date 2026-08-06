#!/usr/bin/env python3
"""
海报图像生成脚本 (Gemini 生图 capability)
参考 AIGC_Video 系统的第四步 (Step 4) 图像生成能力实现。
自动解析《海报提示词.md》中的 Prompt，调用 Google Gemini 图像大模型生成宣传海报。
"""

import os
import sys
import re
import time
import argparse
from typing import Optional, List, Dict, Any
import datetime

try:
    from google import genai
    from google.genai import types
except ImportError:
    print("❌ 缺少依赖包 google-genai，请在终端执行: pip install google-genai")
    sys.exit(1)


def load_env_file():
    """尝试加载环境变量 (支持当前目录及 AIGC_Video 目录下的 .env)"""
    candidate_paths = [
        os.path.join(os.path.dirname(__file__), ".env"),
        "/Users/dielangli/Desktop/Coding/AIGC_Video/.env",
    ]
    for env_path in candidate_paths:
        if os.path.exists(env_path):
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.split("#")[0].strip().strip('"').strip("'")
                        if k not in os.environ:
                            os.environ[k] = v


def extract_prompt_from_md(md_path: str) -> str:
    """从 Markdown 文件提取生图 Prompt"""
    if not os.path.exists(md_path):
        raise FileNotFoundError(f"提示词文件不存在: {md_path}")

    with open(md_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 优先匹配 "## 三" 标题下的 ```text ... ``` 代码块
    pattern_sec3 = re.search(r"##\s*三[^\n]*\n+```(?:text)?\n(.*?)```", content, re.DOTALL)
    if pattern_sec3:
        return pattern_sec3.group(1).strip()

    # 备选：匹配任意包含 9:16 的 ```text 代码块
    pattern_block = re.findall(r"```(?:text)?\n(.*?)```", content, re.DOTALL)
    for block in pattern_block:
        if "9:16" in block or "poster" in block.lower():
            return block.strip()

    if pattern_block:
        return pattern_block[0].strip()

    # 回退：返回整个文件内容
    return content.strip()


def generate_poster_image(
    prompt: str,
    output_path: str,
    logo_path: Optional[str] = None,
    model: str = "gemini-3.1-flash-image",
    aspect_ratio: str = "9:16",
    image_size: str = "2K",
    api_key: Optional[str] = None,
) -> str:
    """
    调用 Gemini 图像生成模型生成海报图片

    Args:
        prompt: 生图提示词
        output_path: 保存结果的文件路径
        logo_path: 可选的品牌 Logo 图片路径
        model: 模型名称 (默认 gemini-3.1-flash-image)
        aspect_ratio: 比例 (默认 9:16)
        image_size: 分辨率级别 (1K/2K/0.5K)
        api_key: Google Cloud API Key
    """
    if not api_key:
        api_key = os.getenv("GOOGLE_CLOUD_API_KEY")

    if not api_key:
        raise ValueError(
            "未找到 GOOGLE_CLOUD_API_KEY！"
            "请在环境变量或 AIGC_Video/.env 文件中配置 GOOGLE_CLOUD_API_KEY。"
        )

    print(f"🚀 初始化 Gemini Client (模型: {model})...")
    client = genai.Client(vertexai=True, api_key=api_key)

    parts = []

    # 如果提供了 Logo 并且文件存在，加入多模态输入
    if logo_path and os.path.exists(logo_path):
        print(f"🖼️  包含 Logo 参考图: {logo_path}")
        with open(logo_path, "rb") as f:
            logo_bytes = f.read()

        ext = os.path.splitext(logo_path)[1].lower()
        mime_type = "image/png" if ext == ".png" else "image/jpeg"
        parts.append(types.Part.from_bytes(data=logo_bytes, mime_type=mime_type))

    # 加入 Prompt 文字 Part
    parts.append(types.Part.from_text(text=prompt))

    print(f"🎨 正在生成海报图片 (比例: {aspect_ratio}, 尺寸: {image_size})...")
    print(f"📝 提示词预览: {prompt[:120]}...\n")

    generate_config = types.GenerateContentConfig(
        response_modalities=["TEXT", "IMAGE"],
        safety_settings=[
            types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="OFF"),
            types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="OFF"),
            types.SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="OFF"),
            types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="OFF"),
        ],
        image_config=types.ImageConfig(
            aspect_ratio=aspect_ratio,
            image_size=image_size,
            output_mime_type="image/png",
        ),
    )

    max_retries = 4
    response = None
    for attempt in range(1, max_retries + 1):
        try:
            response = client.models.generate_content(
                model=model,
                contents=types.Content(role="user", parts=parts),
                config=generate_config,
            )
            break
        except Exception as exc:
            err_str = str(exc).lower()
            if ("429" in err_str or "resource_exhausted" in err_str) and attempt < max_retries:
                wait_time = attempt * 4
                print(f"⚠️ 触发 API 频率限制 (429)，等待 {wait_time} 秒后自动重试 (第 {attempt}/{max_retries} 次)...")
                time.sleep(wait_time)
            else:
                raise

    image_bytes = None
    if getattr(response, "candidates", None):
        for candidate in response.candidates:
            content = getattr(candidate, "content", None)
            parts_list = getattr(content, "parts", None) or []
            for part in parts_list:
                inline_data = getattr(part, "inline_data", None)
                if inline_data and getattr(inline_data, "data", None):
                    image_bytes = inline_data.data
                    if isinstance(image_bytes, memoryview):
                        image_bytes = image_bytes.tobytes()
                    break

    if not image_bytes:
        raise RuntimeError("Gemini API 未返回有效的图片数据！")

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "wb") as f:
        f.write(image_bytes)

    print(f"✅ 海报生成成功，已保存至: {output_path}")
    return output_path


def main():
    parser = argparse.ArgumentParser(description="调用 Gemini 生图能力生成宣传海报")
    parser.add_argument(
        "--prompt-file",
        default=os.path.join(os.path.dirname(__file__), "海报提示词.md"),
        help="海报提示词 Markdown 文件路径",
    )
    parser.add_argument(
        "--logo-file",
        default=os.path.join(os.path.dirname(__file__), "优创Hub Logo.jpg"),
        help="Logo 参考图文件路径",
    )
    parser.add_argument(
        "--output",
        default="",
        help="指定输出图片路径（未指定时自动命名为 海报_9x16_月日_时分.png）",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=1,
        help="批量生成张数 (默认: 1)",
    )
    parser.add_argument(
        "--model",
        default="gemini-3.1-flash-image",
        help="Gemini 图像生成模型 (默认: gemini-3.1-flash-image)",
    )
    parser.add_argument(
        "--aspect-ratio",
        default="9:16",
        help="海报比例 (默认: 9:16)",
    )
    parser.add_argument(
        "--image-size",
        default="2K",
        help="图片分辨率级别 (1K/2K/0.5K)",
    )

    args = parser.parse_args()

    load_env_file()

    prompt_file = os.path.abspath(args.prompt_file)
    logo_file = os.path.abspath(args.logo_file)

    print(f"📄 读取提示词文件: {prompt_file}")
    prompt = extract_prompt_from_md(prompt_file)

    count = max(1, args.count)
    generated_files = []

    for i in range(count):
        print(f"\n🖼️  [批量生成 {i+1}/{count}]")
        now_str = datetime.datetime.now().strftime("%m%d_%H%M")
        
        if args.output:
            if count > 1:
                base, ext = os.path.splitext(os.path.abspath(args.output))
                current_output = f"{base}_{now_str}_{i+1}{ext or '.png'}"
            else:
                current_output = os.path.abspath(args.output)
        else:
            if count > 1:
                current_output = os.path.join(
                    os.path.dirname(prompt_file),
                    f"海报_9x16_{now_str}_{i+1}.png",
                )
            else:
                current_output = os.path.join(
                    os.path.dirname(prompt_file),
                    f"海报_9x16_{now_str}.png",
                )

        try:
            out = generate_poster_image(
                prompt=prompt,
                output_path=current_output,
                logo_path=logo_file if os.path.exists(logo_file) else None,
                model=args.model,
                aspect_ratio=args.aspect_ratio,
                image_size=args.image_size,
            )
            generated_files.append(out)
        except Exception as e:
            print(f"❌ 第 {i+1} 张海报生图失败: {e}")

        if i < count - 1:
            time.sleep(1)

    print(f"\n🎉 全部完成！共成功生成 {len(generated_files)}/{count} 张海报：")
    for filepath in generated_files:
        print(f"  - {filepath}")


if __name__ == "__main__":
    main()
