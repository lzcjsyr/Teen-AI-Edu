#!/usr/bin/env python3
"""分帧独立图简化拼接：无抠图、无重心对齐、无归一化。

输入：4 张独立的居中角色图（每张已由 ImageGen 单独生成，角色天然居中）。
流程：缩放→贴白底画布→堆帧→闪白→导出 GIF。

对比原版（拼接动图.py）：
- 砍掉：白边兜底 / BFS连通域检测 / 重心与包围盒 / 中位数基准归一化 /
       面积保护降级 / 双重抹净（近白+中性灰）
- 保留：闪白接缝标记 / GIF 压缩导出循环 / 质量检查（四角纯白 + 文件大小）
- 新增：轻量边缘清理（仅抹掉贴边灰/水印残留）
"""
from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path

from PIL import Image, ImageDraw

目标边长 = 240
最大字节数 = 500 * 1024
白色 = (255, 255, 255)


def 读取参数():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--frames", nargs="+", type=Path, required=True,
                        help="4 张独立分帧图的路径（按顺序）")
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--durations", required=True,
                        help="每帧时长（毫秒），逗号分隔")
    parser.add_argument("--target-size", type=int, default=目标边长)
    parser.add_argument("--max-bytes", type=int, default=最大字节数)
    return parser.parse_args()


def 轻量清理(图像: Image.Image, 边长: int) -> Image.Image:
    """把缩放后的帧贴到正方形白底画布上，然后做轻量背景清理：

    Step 1 — 居中缩放贴图到白底画布（保持长宽比）。
    Step 2 — 双重抹净（从原版简化而来，无抠图）：
             Pass 1 近白涂白：偏差 < 55 的像素强制涂白（清除暖色晕染底）
             Pass 2 中性灰涂白：检测「R≈G≈B 且中等亮度」的像素，
                   这是 ImageGen 灰色背景的特征（RGB~177），
                   角色有颜色不会误杀。条件：偏差 < 190 且 色差 < 50。
    """
    # Step 1: 按比例缩放并居中贴到白底画布
    缩略 = 图像.copy()
    缩略.thumbnail((边长, 边长), Image.Resampling.LANCZOS)
    画布 = Image.new("RGB", (边长, 边长), 白色)
    左上x = (边长 - 缩略.width) // 2
    左上y = (边长 - 缩略.height) // 2
    画布.paste(缩略, (左上x, 左上y))

    # Step 2: 双重抹净
    像素 = 画布.load()
    近白阈值 = 55   # 覆盖吉卜力暖色底(~25偏差)
    中性灰亮阈 = 190  # 覆盖ImageGen灰底(RGB~177, 偏差~78)
    中性灰色差阈 = 50  # 灰色的 R/G/B 差异极小; 角色肤色差异大
    for y in range(边长):
        for x in range(边长):
            r, g, b = 像素[x, y]
            偏差 = max(abs(r - 255), abs(g - 255), abs(b - 255))
            色差 = max(abs(r - g), abs(g - b), abs(r - b))
            # Pass 1: 近白直接涂白
            if 偏差 < 近白阈值:
                像素[x, y] = 白色
            # Pass 2: 中性灰涂白（不重复涂已白的）
            elif 偏差 < 中性灰亮阈 and 色差 < 中性灰色差阈:
                像素[x, y] = 白色
    return 画布


def 保存动作预览图(帧列表, 路径: Path):
    """横向排列所有帧的缩小版预览。"""
    缩略边长 = 120
    预览 = Image.new("RGB", (缩略边长 * len(帧列表), 缩略边长), 白色)
    for 序号, 帧 in enumerate(帧列表):
        缩略图 = 帧.copy()
        缩略图.thumbnail((缩略边长, 缩略边长), Image.Resampling.LANCZOS)
        x = 序号 * 缩略边长 + (缩略边长 - 缩略图.width) // 2
        y = (缩略边长 - 缩略图.height) // 2
        预览.paste(缩略图, (x, y))
        ImageDraw.Draw(预览).text(
            (序号 * 缩略边长 + 5, 5), str(序号 + 1),
            fill="#333333")
    预览.save(路径)


def 生成闪白帧(帧: Image.Image, 白度: float = 0.78) -> Image.Image:
    """在循环接缝处插入的轻微闪白帧，标出新一轮开始位置。"""
    return Image.blend(帧, Image.new("RGB", 帧.size, 白色), 白度)


def 导出一次(帧列表, 时长列表, 路径: Path, 边长: int,
             色彩数: int, 抽帧间隔: int):
    选择帧 = 帧列表[::抽帧间隔]
    选择时长 = [sum(时长列表[i:i + 抽帧间隔])
                for i in range(0, len(时长列表), 抽帧间隔)]
    调色板帧 = []
    for 帧 in 选择帧:
        画布 = 帧.copy()
        画布.thumbnail((边长, 边长), Image.Resampling.LANCZOS)
        调色板帧.append(
            画布.convert("P",
                         palette=Image.Palette.ADAPTIVE,
                         colors=色彩数,
                         dither=Image.Dither.NONE))
    调色板帧[0].save(
        路径, save_all=True, append_images=调色板帧[1:],
        duration=选择时长, loop=0, disposal=2, optimize=True)
    return {"尺寸": 边长, "色彩数": 色彩数, "抽帧间隔": 抽帧间隔,
            "文件字节数": 路径.stat().st_size, "帧数": len(调色板帧)}


def main():
    参数 = 读取参数()
    时长列表 = [int(v) for v in 参数.durations.split(",")]
    if len(参数.frames) != len(时长列表):
        raise SystemExit(f"帧数量({len(参数.frames)})与时长数量({len(时长列表)})不匹配")
    if any(v < 20 for v in 时长列表):
        raise SystemExit("每帧时长至少 20 毫秒")

    项目 = 参数.project
    分帧图片 = 项目 / "分帧图片"
    最终成品 = 项目 / "最终成品"
    质检报告 = 项目 / "质检报告"
    for 文件夹 in (分帧图片, 最终成品, 质检报告):
        文件夹.mkdir(parents=True, exist_ok=True)

    # ====== 核心流程：逐帧加载 → 缩放居中 → 轻量清理 ======
    对齐帧 = []
    for 序号, 帧路径 in enumerate(参数.frames):
        原图 = Image.open(帧路径).convert("RGB")
        处理后 = 轻量清理(原图, 参数.target_size)
        对齐帧.append(处理后)
        # 同时保存单帧到分帧目录供检查
        处理后.save(分帧图片 / f"第{序号 + 1:02d}帧.png")

    # 循环接缝标记
    闪白帧 = 生成闪白帧(对齐帧[0])
    导出帧列表 = 对齐帧 + [闪白帧]
    导出时长 = 时长列表 + [140]

    # 预览图
    保存动作预览图(对齐帧, 质检报告 / "动作预览图.png")
    导出帧列表[0].save(最终成品 / "首帧预览.png")

    # GIF 压缩导出（尝试不同参数组合直到满足文件大小限制）
    成品路径 = 最终成品 / f"{项目.name}.gif"
    尝试记录 = []
    for 边长 in (参数.target_size, 220, 200, 180):
        for 色彩数 in (128, 96, 64, 48, 32):
            for 抽帧间隔 in (1, 2):
                尝试 = 导出一次(导出帧列表, 导出时长, 成品路径,
                               边长, 色彩数, 抽帧间隔)
                尝试记录.append(尝试)
                if 尝试["文件字节数"] <= 参数.max_bytes:
                    动图 = Image.open(成品路径).convert("RGB")
                    四角 = [动图.getpixel((x, y)) for x, y in (
                        (0, 0), (动图.width - 1, 0),
                        (0, 动图.height - 1),
                        (动图.width - 1, 动图.height - 1))]
                    白底通过 = all(
                        max(abs(c - 255) for c in 像素) <= 8
                        for 像素 in 四角)
                    报告 = {
                        "是否通过": 白底通过, "格式": "GIF",
                        "尺寸": [动图.width, 动图.height],
                        "帧数": getattr(Image.open(成品路径),
                                       "n_frames", 1),
                        "总时长毫秒": sum(导出时长),
                        "文件字节数": 成品路径.stat().st_size,
                        "最大允许字节数": 参数.max_bytes,
                        "背景检查": ("白色背景通过" if 白底通过
                                     else "白色背景失败"),
                        "导出尝试": 尝试记录,
                        "方案": "分帧独立生成_无抠图版"}
                    (质检报告 / "质量检查.json").write_text(
                        json.dumps(报告, ensure_ascii=False, indent=2),
                        encoding="utf-8")
                    if not 白底通过:
                        raise SystemExit(json.dumps(
                            报告, ensure_ascii=False))
                    print(json.dumps(报告, ensure_ascii=False))
                    return
    报告 = {
        "是否通过": False,
        "原因": "无法压缩到文件体积限制以内",
        "导出尝试": 尝试记录}
    (质检报告 / "质量检查.json").write_text(
        json.dumps(报告, ensure_ascii=False, indent=2),
        encoding="utf-8")
    raise SystemExit(json.dumps(报告, ensure_ascii=False))


if __name__ == "__main__":
    main()
