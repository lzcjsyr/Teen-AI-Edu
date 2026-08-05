#!/usr/bin/env python3
"""切开规则连环分镜，白底抠出主体并按重心对齐，导出纯白背景的微信 GIF 表情。

关键改进（消除分割线残留与帧间跳动）：
1. 裁切后把每格最外圈涂白（白边兜底），抹掉 AI 画出的淡灰分割线残留。
2. 以“非近白像素”作为主体遮罩，相当于白底抠图。
3. 计算每帧主体重心（center of mass），并把主体缩放到统一高度后，
   将重心钉在画布正中——四格角色位置、大小一致，GIF 不再跳动。
"""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from PIL import Image, ImageDraw

目标边长 = 240
最大字节数 = 500 * 1024
白色 = (255, 255, 255)
近白阈值 = 48          # 与纯白的单通道最大偏差超过此值即视为"主体"像素；
                        # 32→48 是为了兼容宫崎骏/吉卜力水彩风等带大面积浅暖色背景晕染的画风：
                        #   暖色晕染（RGB~245,235,210，偏差~25-40）被当白底排除，
                        #   真正角色彩色（肤色、头发、衣服，偏差>50）保留为主体。
白边宽度 = 16          # 裁切后最外圈涂白的像素数（需覆盖 ImageGen 可能画出的粗灰分割线）
主体占画布比 = 0.82     # 归一化后主体高度占输出边长的比例


def 读取参数():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--rows", type=int, required=True)
    parser.add_argument("--cols", type=int, required=True)
    parser.add_argument("--gutter", type=int, default=0, help="每格四边裁去的像素，用于去掉分隔线")
    parser.add_argument("--durations", required=True, help="每格时长（毫秒），以英文逗号分隔")
    parser.add_argument("--target-size", type=int, default=目标边长)
    parser.add_argument("--max-bytes", type=int, default=最大字节数)
    return parser.parse_args()


def 白边兜底(图像: Image.Image, 边宽: int = 白边宽度) -> Image.Image:
    """把图像最外圈 边宽 像素涂成纯白，抹掉贴边的分割线残留。"""
    画布 = 图像.copy()
    像素 = 画布.load()
    W, H = 画布.size
    for x in range(W):
        for dy in range(边宽):
            if dy < H:
                像素[x, dy] = 白色
            if H - 1 - dy >= 0:
                像素[x, H - 1 - dy] = 白色
    for y in range(H):
        for dx in range(边宽):
            if dx < W:
                像素[dx, y] = 白色
            if W - 1 - dx >= 0:
                像素[W - 1 - dx, y] = 白色
    return 画布


def 检测主体(图像: Image.Image):
    """返回最大连通非白区域的坐标列表（白底抠图 + 去除背景碎片/场景色块）。
    
    用 BFS 找到所有非白像素的连通域，只保留最大的那个作为"主体"遮罩。
    这样即使 AI 画了宫崎骏风的水彩背景晕染或场景元素色块（被子、衣物阴影等），
    只要它们与角色主体不连通（或比角色小），就会被自动排除，重心对齐不受干扰。
    """
    像素 = 图像.load()
    W, H = 图像.size
    # 标记所有非白像素
    is_subject = [[False] * W for _ in range(H)]
    for y in range(H):
        for x in range(W):
            r, g, b = 像素[x, y]
            if abs(r - 255) > 近白阈值 or abs(g - 255) > 近白阈值 or abs(b - 255) > 近白阈值:
                is_subject[y][x] = True

    # BFS 找最大连通域（4-邻接）
    visited = [[False] * W for _ in range(H)]
    max_region: list[tuple[int, int]] = []
    directions = [(0, 1), (0, -1), (1, 0), (-1, 0)]

    for sy in range(H):
        for sx in range(W):
            if is_subject[sy][sx] and not visited[sy][sx]:
                region: list[tuple[int, int]] = []
                queue = [(sx, sy)]
                visited[sy][sx] = True
                while queue:
                    cx, cy = queue.pop(0)
                    region.append((cx, cy))
                    for dx, dy in directions:
                        nx, ny = cx + dx, cy + dy
                        if 0 <= nx < W and 0 <= ny < H and is_subject[ny][nx] and not visited[ny][nx]:
                            visited[ny][nx] = True
                            queue.append((nx, ny))
                if len(region) > len(max_region):
                    max_region = region

    return max_region


def 重心与包围盒(坐标):
    if not 坐标:
        return None
    xs = [p[0] for p in 坐标]
    ys = [p[1] for p in 坐标]
    n = len(xs)
    return {
        "cx": sum(xs) / n,
        "cy": sum(ys) / n,
        "w": max(xs) - min(xs) + 1,
        "h": max(ys) - min(ys) + 1,
    }


def 合成对齐帧(原始帧: Image.Image, 边长: int) -> Image.Image:
    """白底抠图 + 主体大小归一化 + 重心居中，输出纯白画布上的对齐帧。"""
    帧 = 白边兜底(原始帧)
    坐标 = 检测主体(帧)
    if not 坐标:
        # 兜底：检测不到主体时直接居中缩略，避免空遮罩导致崩溃
        画布 = Image.new("RGB", (边长, 边长), 白色)
        缩略 = 帧.copy()
        缩略.thumbnail((边长, 边长), Image.Resampling.LANCZOS)
        画布.paste(缩略, ((边长 - 缩略.width) // 2, (边长 - 缩略.height) // 2))
        return 画布
    信息 = 重心与包围盒(坐标)
    # 归一化主体大小：让主体高度统一为 边长*主体占画布比，且宽度不超出画布
    目标主体高度 = 边长 * 主体占画布比
    比例 = 目标主体高度 / max(信息["h"], 1)
    if 信息["w"] * 比例 > 边长 * 0.92:
        比例 = 边长 * 0.92 / max(信息["w"], 1)
    新宽, 新高 = max(1, int(帧.width * 比例)), max(1, int(帧.height * 比例))
    缩放帧 = 帧.resize((新宽, 新高), Image.Resampling.LANCZOS)
    # 缩放后主体重心的画布内坐标
    重心x, 重心y = 信息["cx"] * 比例, 信息["cy"] * 比例
    画布 = Image.new("RGB", (边长, 边长), 白色)
    左上x = int(边长 / 2 - 重心x)
    左上y = int(边长 / 2 - 重心y)
    画布.paste(缩放帧, (左上x, 左上y))
    # 最终双重抹净（消除所有灰边残留）：
    # Pass 1 — 近白抹净：偏差<20 的像素强制涂白（消除抗锯齿灰边、GIF 抖动色斑）
    # Pass 2 — 中性灰抹除：检测"中性灰"像素（R≈G≈B 且中等亮度），
    #            这是 ImageGen 网格分割线的特征色，角色是有颜色的不会误杀。
    画布像素 = 画布.load()
    for y in range(边长):
        for x in range(边长):
            r, g, b = 画布像素[x, y]
            偏差 = max(abs(r - 255), abs(g - 255), abs(b - 255))
            色差 = max(abs(r - g), abs(g - b), abs(r - b))
            if 偏差 < 20 or (偏差 < 160 and 色差 < 50):
                画布像素[x, y] = 白色
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
    """在循环接缝处插入的轻微闪白帧，用来标出新一轮开始的位置，
    解决“无限循环 GIF 看不出起止”的问题。"""
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
    时长列表 = [int(value) for value in 参数.durations.split(",")]
    预期帧数 = 参数.rows * 参数.cols
    if len(时长列表) != 预期帧数 or any(value < 20 for value in 时长列表):
        raise SystemExit(f"请提供 {预期帧数} 个时长，每个至少 20 毫秒")
    项目 = 参数.project
    原始素材, 分帧图片, 最终成品, 质检报告 = (项目 / 名称 for 名称 in ("原始素材", "分帧图片", "最终成品", "质检报告"))
    for 文件夹 in (原始素材, 分帧图片, 最终成品, 质检报告):
        文件夹.mkdir(parents=True, exist_ok=True)
    分镜路径 = 原始素材 / "连环分镜.png"
    if 参数.source.resolve() != 分镜路径.resolve():
        shutil.copy2(参数.source, 分镜路径)
    分镜 = Image.open(分镜路径).convert("RGB")
    格宽, 格高 = 分镜.width // 参数.cols, 分镜.height // 参数.rows
    if 格宽 * 参数.cols != 分镜.width or 格高 * 参数.rows != 分镜.height:
        raise SystemExit("原始分镜的宽高必须能被行数和列数整除")
    原始帧 = []
    for 序号 in range(预期帧数):
        行, 列 = divmod(序号, 参数.cols)
        左, 上 = 列 * 格宽 + 参数.gutter, 行 * 格高 + 参数.gutter
        右, 下 = (列 + 1) * 格宽 - 参数.gutter, (行 + 1) * 格高 - 参数.gutter
        if 右 <= 左 or 下 <= 上:
            raise SystemExit("分隔线宽度过大，已经挤掉了画格")
        原始帧.append(分镜.crop((左, 上, 右, 下)))

    # ====== 全局中位数基准对齐（解决姿态差异导致的帧间大小不一致）======
    # 第一步：收集所有帧的主体包围盒高度，用中位数作为统一缩放基准。
    #        这样即使某一格只画了头（如"灵魂出窍"），也不会被单独放大到
    #        跟全身格一样大——所有帧共用同一个缩放比例，大小一致不跳。
    #
    # 面积保护：如果某帧的主体连通域面积超过格子的 65%，说明检测不准确
    #            （宫崎骏水彩晕染/拖尾效果被当成主体撑爆了包围盒），
    #            该帧自动降级为简单居中缩略，不污染其他帧的基准。
    import statistics
    最大主体面积比 = 0.65
    格总面积 = 参数.target_size * 参数.target_size  # 用于面积检查的参考值（近似）
    # 实际用白边帧尺寸更准确：
    白边帧列表 = [白边兜底(帧) for 帧 in 原始帧]
    实际格面积 = 白边帧列表[0].width * 白边帧列表[0].height if 白边帧列表 else 1
    包围盒列表 = []
    for 帧_白边 in 白边帧列表:
        坐标 = 检测主体(帧_白边)
        if 坐标 and len(坐标) < 实际格面积 * 最大主体面积比:
            包围盒列表.append(重心与包围盒(坐标))
        else:
            # 主体面积过大或检测失败 → 降级为 fallback（简单居中缩略）
            包围盒列表.append(None)
    有效高度 = [info["h"] for info in 包围盒列表 if info is not None]
    统一基准高度 = statistics.median(有效高度) if 有效高度 else (参数.target_size * 主体占画布比)

    # 第二步：用统一基准高度逐帧对齐（所有帧缩放比例相同 → 大小一致）
    对齐帧 = []
    for i, 帧_白边 in enumerate(白边帧列表):
        info = 包围盒列表[i]
        if not info:
            # 兜底：检测失败（主体面积过大或无主体）→ 居中缩略 + 抹净
            画布 = Image.new("RGB", (参数.target_size, 参数.target_size), 白色)
            缩略 = 原始帧[i].copy()
            缩略.thumbnail((参数.target_size, 参数.target_size), Image.Resampling.LANCZOS)
            画布.paste(缩略, ((参数.target_size - 缩略.width) // 2, (参数.target_size - 缩略.height) // 2))
            # 对兜底帧也做双重抹净（防止大面积背景晕染被贴上来）
            画布像素 = 画布.load()
            for y in range(参数.target_size):
                for x in range(参数.target_size):
                    r, g, b = 画布像素[x, y]
                    偏差 = max(abs(r - 255), abs(g - 255), abs(b - 255))
                    色差 = max(abs(r - g), abs(g - b), abs(r - b))
                    if 偏差 < 20 or (偏差 < 160 and 色差 < 50):
                        画布像素[x, y] = 白色
            对齐帧.append(画布)
            continue
        目标主体高度 = 参数.target_size * 主体占画布比
        比例 = 目标主体高度 / max(统一基准高度, 1)
        if info["w"] * 比例 > 参数.target_size * 0.92:
            比例 = (参数.target_size * 0.92) / max(info["w"], 1)
        新宽, 新高 = max(1, int(原始帧[i].width * 比例)), max(1, int(原始帧[i].height * 比例))
        缩放帧 = 原始帧[i].resize((新宽, 新高), Image.Resampling.LANCZOS)
        重心x, 重心y = info["cx"] * 比例, info["cy"] * 比例
        画布 = Image.new("RGB", (参数.target_size, 参数.target_size), 白色)
        左上x = int(参数.target_size / 2 - 重心x)
        左上y = int(参数.target_size / 2 - 重心y)
        画布.paste(缩放帧, (左上x, 左上y))
        # 最终双重抹净（同之前）
        画布像素 = 画布.load()
        for y in range(参数.target_size):
            for x in range(参数.target_size):
                r, g, b = 画布像素[x, y]
                偏差 = max(abs(r - 255), abs(g - 255), abs(b - 255))
                色差 = max(abs(r - g), abs(g - b), abs(r - b))
                if 偏差 < 20 or (偏差 < 160 and 色差 < 50):
                    画布像素[x, y] = 白色
        对齐帧.append(画布)

    # 循环接缝标记：在最后一格之后插入一帧轻微闪白，明确标出新一轮起点，
    # 解决“无限循环 GIF 看不出起止”的问题（配合高潮帧长停顿效果最佳）。
    闪白帧 = 生成闪白帧(对齐帧[0])
    导出帧列表 = 对齐帧 + [闪白帧]
    导出时长 = 时长列表 + [140]

    for 序号, 帧 in enumerate(原始帧):
        帧.save(分帧图片 / f"第{序号 + 1:02d}帧.png")
    保存动作预览图(对齐帧, 质检报告 / "动作预览图.png")
    成品路径 = 最终成品 / f"{项目.name}.gif"
    首帧 = 对齐帧[0]
    首帧.save(最终成品 / "首帧预览.png")
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
                            "导出尝试": 尝试记录, "分镜来源": str(分镜路径)}
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
