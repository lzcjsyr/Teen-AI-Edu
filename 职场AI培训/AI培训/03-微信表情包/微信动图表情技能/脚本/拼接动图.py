#!/usr/bin/env python3
"""精准裁切版：不抠图、不重心对齐、不归一化。

设计理念（用户明确要求）：
- 抠图/重心对齐/大小归一化每次都不够准 → 全部去掉。
- 只做「精准等分裁切 → 每格整体居中缩放 → 脚本叠加中文字 → 导出 GIF」。
- 角色与背景的反差、四格角色的一致性，全部靠 ImageGen 提示词保证
  （宫崎骏水彩风 + 角色穿彩色衣服 + 纯白底）。
- 中文字不再让 AI 画（渲染不可靠、字体乱），改由本脚本用系统黑体
  精准叠加，带白色描边，保证在任何画面上都清晰规整。

关键参数：
- --gutter：每格四边裁去的像素，用来切掉 AI 可能画出的分割线，保证切分干净。
- --texts：每格文字，用竖线 | 分隔（如 "起不来|？|……|上班"）；留空或 NONE 表示该格无字。
- --text-pos：文字位置 top / bottom（默认 bottom）。
"""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

目标边长 = 240
最大字节数 = 500 * 1024
白色 = (255, 255, 255)
文字颜色 = (45, 45, 45)
描边颜色 = (255, 255, 255)

# 系统中文字体候选（按优先级），第一个存在的即被使用
字体候选 = [
    "/System/Library/Fonts/PingFang.ttc",
    "/System/Library/Fonts/STHeiti Medium.ttc",
    "/System/Library/Fonts/STHeiti Light.ttc",
    "/System/Library/Fonts/Supplemental/Songti.ttc",
]


def 找中文字体() -> str:
    for 路径 in 字体候选:
        if Path(路径).exists():
            return 路径
    raise SystemExit("找不到可用的系统中文字体，请检查 字体候选 列表")


def 读取参数():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--rows", type=int, required=True)
    parser.add_argument("--cols", type=int, required=True)
    parser.add_argument("--gutter", type=int, default=6,
                        help="每格四边裁去的像素，用于去掉分隔线（保证切分干净）")
    parser.add_argument("--durations", required=True,
                        help="每格时长（毫秒），英文逗号分隔")
    parser.add_argument("--texts", default="",
                        help="每格文字，竖线 | 分隔；单格留空或 NONE 表示无字")
    parser.add_argument("--text-pos", default="bottom",
                        choices=["top", "bottom"])
    parser.add_argument("--target-size", type=int, default=目标边长)
    parser.add_argument("--max-bytes", type=int, default=最大字节数)
    return parser.parse_args()


def 居中缩放(格图: Image.Image, 边长: int, 留白比: float = 0.06) -> Image.Image:
    """把一格整体等比缩放后居中贴到正方形白底画布上（contain 模式）。
    不做抠图，只是把整格画面完整放进去，四周留一点白边。"""
    可用 = int(边长 * (1 - 留白比 * 2))
    缩略 = 格图.copy()
    缩略.thumbnail((可用, 可用), Image.Resampling.LANCZOS)
    画布 = Image.new("RGB", (边长, 边长), 白色)
    画布.paste(缩略, ((边长 - 缩略.width) // 2, (边长 - 缩略.height) // 2))
    return 画布


def 边缘去白外杂色(画布: Image.Image, 边宽: int = 10) -> Image.Image:
    """只清理紧贴四边的非纯白杂色（分割线残片/背景轻微溢出），
    不触碰画面中心，保护角色主体与文字。"""
    像素 = 画布.load()
    W, H = 画布.size
    for y in range(H):
        for x in range(W):
            距边 = min(x, y, W - 1 - x, H - 1 - y)
            if 距边 <= 边宽:
                r, g, b = 像素[x, y]
                偏差 = max(abs(r - 255), abs(g - 255), abs(b - 255))
                色差 = max(abs(r - g), abs(g - b), abs(r - b))
                # 边缘区域：近白 或 中性灰（分割线特征）→ 涂白
                if 偏差 < 60 or (偏差 < 170 and 色差 < 45):
                    像素[x, y] = 白色
    return 画布


def 叠加文字(画布: Image.Image, 文字: str, 字体路径: str, 位置: str) -> Image.Image:
    """在画布上用系统黑体叠加中文，带白色描边，保证清晰规整。
    字号根据文字长度自适应，横向居中，贴近上/下边缘。"""
    if not 文字 or 文字.strip().upper() == "NONE":
        return 画布
    文字 = 文字.strip()
    边长 = 画布.width
    draw = ImageDraw.Draw(画布)
    # 字号自适应：文字越多字号越小，保证不超出画布宽度的 88%
    最大宽 = 边长 * 0.88
    字号 = int(边长 * 0.20)
    描边 = max(2, 字号 // 14)
    while 字号 > 12:
        字体 = ImageFont.truetype(字体路径, 字号)
        bbox = draw.textbbox((0, 0), 文字, font=字体, stroke_width=描边)
        文宽 = bbox[2] - bbox[0]
        if 文宽 <= 最大宽:
            break
        字号 -= 2
        描边 = max(2, 字号 // 14)
    字体 = ImageFont.truetype(字体路径, 字号)
    bbox = draw.textbbox((0, 0), 文字, font=字体, stroke_width=描边)
    文宽 = bbox[2] - bbox[0]
    文高 = bbox[3] - bbox[1]
    x = (边长 - 文宽) // 2 - bbox[0]
    上边距 = int(边长 * 0.04)
    if 位置 == "top":
        y = 上边距 - bbox[1]
    else:
        y = 边长 - 文高 - 上边距 - bbox[1]
    draw.text((x, y), 文字, font=字体, fill=文字颜色,
              stroke_width=描边, stroke_fill=描边颜色)
    return 画布


def 保存动作预览图(帧列表, 路径: Path):
    缩略边长 = 120
    预览 = Image.new("RGB", (缩略边长 * len(帧列表), 缩略边长), 白色)
    for 序号, 帧 in enumerate(帧列表):
        缩略图 = 帧.copy()
        缩略图.thumbnail((缩略边长, 缩略边长), Image.Resampling.LANCZOS)
        x = 序号 * 缩略边长 + (缩略边长 - 缩略图.width) // 2
        y = (缩略边长 - 缩略图.height) // 2
        预览.paste(缩略图, (x, y))
        ImageDraw.Draw(预览).text((序号 * 缩略边长 + 5, 5), str(序号 + 1), fill="#333333")
    预览.save(路径)


def 生成闪白帧(帧: Image.Image, 白度: float = 0.78) -> Image.Image:
    """循环接缝处的轻微闪白帧，标出新一轮起点。"""
    return Image.blend(帧, Image.new("RGB", 帧.size, 白色), 白度)


def 导出一次(帧列表, 时长列表, 路径: Path, 边长: int, 色彩数: int, 抽帧间隔: int):
    选择帧 = 帧列表[::抽帧间隔]
    选择时长 = [sum(时长列表[i:i + 抽帧间隔]) for i in range(0, len(时长列表), 抽帧间隔)]
    调色板帧 = []
    for 帧 in 选择帧:
        画布 = 帧.copy()
        画布.thumbnail((边长, 边长), Image.Resampling.LANCZOS)
        调色板帧.append(画布.convert("P", palette=Image.Palette.ADAPTIVE, colors=色彩数, dither=Image.Dither.NONE))
    调色板帧[0].save(路径, save_all=True, append_images=调色板帧[1:], duration=选择时长,
                      loop=0, disposal=2, optimize=True)
    return {"尺寸": 边长, "色彩数": 色彩数, "抽帧间隔": 抽帧间隔,
            "文件字节数": 路径.stat().st_size, "帧数": len(调色板帧)}


def main():
    参数 = 读取参数()
    if 参数.rows < 1 or 参数.cols < 1 or 参数.gutter < 0:
        raise SystemExit("行数、列数必须为正数，分隔线宽度不能为负数")
    时长列表 = [int(v) for v in 参数.durations.split(",")]
    预期帧数 = 参数.rows * 参数.cols
    if len(时长列表) != 预期帧数 or any(v < 20 for v in 时长列表):
        raise SystemExit(f"请提供 {预期帧数} 个时长，每个至少 20 毫秒")

    # 解析每格文字
    if 参数.texts:
        文字列表 = 参数.texts.split("|")
    else:
        文字列表 = []
    # 补齐/截断到帧数
    文字列表 = (文字列表 + [""] * 预期帧数)[:预期帧数]

    字体路径 = 找中文字体()

    项目 = 参数.project
    原始素材, 分帧图片, 最终成品, 质检报告 = (项目 / n for n in ("原始素材", "分帧图片", "最终成品", "质检报告"))
    for 文件夹 in (原始素材, 分帧图片, 最终成品, 质检报告):
        文件夹.mkdir(parents=True, exist_ok=True)
    分镜路径 = 原始素材 / "连环分镜.png"
    if 参数.source.resolve() != 分镜路径.resolve():
        shutil.copy2(参数.source, 分镜路径)
    分镜 = Image.open(分镜路径).convert("RGB")
    格宽, 格高 = 分镜.width // 参数.cols, 分镜.height // 参数.rows
    if 格宽 * 参数.cols != 分镜.width or 格高 * 参数.rows != 分镜.height:
        raise SystemExit("原始分镜的宽高必须能被行数和列数整除")

    # ====== 精准裁切 → 居中缩放 → 边缘清杂 → 叠字 ======
    对齐帧 = []
    for 序号 in range(预期帧数):
        行, 列 = divmod(序号, 参数.cols)
        左, 上 = 列 * 格宽 + 参数.gutter, 行 * 格高 + 参数.gutter
        右, 下 = (列 + 1) * 格宽 - 参数.gutter, (行 + 1) * 格高 - 参数.gutter
        if 右 <= 左 or 下 <= 上:
            raise SystemExit("分隔线宽度过大，已经挤掉了画格")
        格图 = 分镜.crop((左, 上, 右, 下))
        画布 = 居中缩放(格图, 参数.target_size)
        画布 = 边缘去白外杂色(画布)
        画布 = 叠加文字(画布, 文字列表[序号], 字体路径, 参数.text_pos)
        对齐帧.append(画布)
        格图.save(分帧图片 / f"第{序号 + 1:02d}帧.png")

    # 循环接缝标记
    闪白帧 = 生成闪白帧(对齐帧[0])
    导出帧列表 = 对齐帧 + [闪白帧]
    导出时长 = 时长列表 + [140]

    保存动作预览图(对齐帧, 质检报告 / "动作预览图.png")
    成品路径 = 最终成品 / f"{项目.name}.gif"
    对齐帧[0].save(最终成品 / "首帧预览.png")

    尝试记录 = []
    for 边长 in (参数.target_size, 220, 200, 180):
        for 色彩数 in (128, 96, 64, 48, 32):
            for 抽帧间隔 in (1, 2):
                尝试 = 导出一次(导出帧列表, 导出时长, 成品路径, 边长, 色彩数, 抽帧间隔)
                尝试记录.append(尝试)
                if 尝试["文件字节数"] <= 参数.max_bytes:
                    动图 = Image.open(成品路径).convert("RGB")
                    四角 = [动图.getpixel((x, y)) for x, y in ((0, 0), (动图.width - 1, 0), (0, 动图.height - 1), (动图.width - 1, 动图.height - 1))]
                    白底通过 = all(max(abs(c - 255) for c in 像素) <= 8 for 像素 in 四角)
                    报告 = {"是否通过": 白底通过, "格式": "GIF", "尺寸": [动图.width, 动图.height],
                            "帧数": getattr(Image.open(成品路径), "n_frames", 1), "总时长毫秒": sum(导出时长),
                            "文件字节数": 成品路径.stat().st_size, "最大允许字节数": 参数.max_bytes,
                            "背景检查": "白色背景通过" if 白底通过 else "白色背景失败",
                            "每格文字": 文字列表, "使用字体": 字体路径,
                            "导出尝试": 尝试记录, "分镜来源": str(分镜路径), "方案": "精准裁切_脚本叠字_无抠图"}
                    (质检报告 / "质量检查.json").write_text(json.dumps(报告, ensure_ascii=False, indent=2), encoding="utf-8")
                    if not 白底通过:
                        raise SystemExit(json.dumps(报告, ensure_ascii=False))
                    print(json.dumps(报告, ensure_ascii=False))
                    return
    报告 = {"是否通过": False, "原因": "无法压缩到文件体积限制以内", "导出尝试": 尝试记录}
    (质检报告 / "质量检查.json").write_text(json.dumps(报告, ensure_ascii=False, indent=2), encoding="utf-8")
    raise SystemExit(json.dumps(报告, ensure_ascii=False))


if __name__ == "__main__":
    main()
