#!/usr/bin/env python3
"""生成短视频脚本docx：AI经济增速是互联网的3倍——但你的转型速度跟上了吗？"""

from docx import Document
from docx.shared import Inches, Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
import os

doc = Document()

# ── 页面设置 ──
for section in doc.sections:
    section.top_margin = Cm(2)
    section.bottom_margin = Cm(2)
    section.left_margin = Cm(2.5)
    section.right_margin = Cm(2.5)

style = doc.styles['Normal']
font = style.font
font.name = '微软雅黑'
font.size = Pt(11)
style.element.rPr.rFonts.set(qn('w:eastAsia'), '微软雅黑')

# ── 辅助函数 ──
def add_heading_styled(text, level=1):
    h = doc.add_heading(text, level=level)
    for run in h.runs:
        run.font.name = '微软雅黑'
        run._element.rPr.rFonts.set(qn('w:eastAsia'), '微软雅黑')
    return h

def add_para(text, bold=False, size=11, color=None, align=None, space_after=6):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(space_after)
    if align:
        p.alignment = align
    run = p.add_run(text)
    run.font.name = '微软雅黑'
    run._element.rPr.rFonts.set(qn('w:eastAsia'), '微软雅黑')
    run.font.size = Pt(size)
    run.bold = bold
    if color:
        run.font.color.rgb = RGBColor(*color)
    return p

def set_cell_shading(cell, color_hex):
    """设置单元格底色"""
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    shading = OxmlElement('w:shd')
    shading.set(qn('w:fill'), color_hex)
    shading.set(qn('w:val'), 'clear')
    tcPr.append(shading)

def add_cell_text(cell, text, bold=False, size=10, color=None, align=None):
    # 清除默认段落
    cell.paragraphs[0].clear()
    p = cell.paragraphs[0]
    if align is not None:
        p.alignment = align
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(2)
    run = p.add_run(text)
    run.font.name = '微软雅黑'
    run._element.rPr.rFonts.set(qn('w:eastAsia'), '微软雅黑')
    run.font.size = Pt(size)
    run.bold = bold
    if color:
        run.font.color.rgb = RGBColor(*color)
    return run

# ═══════════════════════════════════════
# 封面
# ═══════════════════════════════════════
doc.add_paragraph()  # 空行

title = doc.add_paragraph()
title.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = title.add_run('短视频拍摄脚本')
run.font.name = '微软雅黑'
run._element.rPr.rFonts.set(qn('w:eastAsia'), '微软雅黑')
run.font.size = Pt(28)
run.bold = True
run.font.color.rgb = RGBColor(0x1a, 0x1a, 0x2e)

subtitle = doc.add_paragraph()
subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = subtitle.add_run('当 AI 经济增速远超人类学习速度——\n我们正在被自己的造物甩在身后吗？')
run.font.name = '微软雅黑'
run._element.rPr.rFonts.set(qn('w:eastAsia'), '微软雅黑')
run.font.size = Pt(14)
run.font.color.rgb = RGBColor(0x55, 0x55, 0x55)

doc.add_paragraph()

# 元信息表格
meta_table = doc.add_table(rows=7, cols=2, style='Table Grid')
meta_table.alignment = WD_TABLE_ALIGNMENT.CENTER
meta_data = [
    ('选题编号', '🥇 推荐 1'),
    ('核心选题', 'AI 经济增速是互联网的 3 倍——但你的转型速度跟上了吗？'),
    ('冲突点', 'AI 营收增速每 2 天新增 10 亿美元，而人类掌握一项新技能至少需要 3-6 个月。这条"速度差曲线"正在把大量职场人甩出轨道。'),
    ('传播锚点', '双曲线对比图——红色 AI 营收曲线陡峭直冲，蓝色人类技能迭代曲线平缓爬升，裂缝处大字标注"你的转型窗口正在关闭"。'),
    ('8 维打分', '情绪 4 / 传播 5 / 独家 4 / 身份 5 / 时效 5 / 锚点 4 / 可视化 5 / 门槛 5 = 总分 37/40'),
    ('基因组合', '情绪钩子（焦虑→共鸣）+ 信息差（3x 互联网增速数据）+ 身份标签（每一个职场人）'),
    ('核心基调', '用数据制造认知冲击，用真实案例引发共鸣，最终回归人文关怀——不是贩卖焦虑，是唤醒行动。'),
]
for i, (label, value) in enumerate(meta_data):
    add_cell_text(meta_table.cell(i, 0), label, bold=True, size=10, color=(0x33, 0x33, 0x33))
    add_cell_text(meta_table.cell(i, 1), value, size=10)
    set_cell_shading(meta_table.cell(i, 0), 'F5F5F5')
    meta_table.cell(i, 0).width = Cm(3.5)

doc.add_paragraph()

# ═══════════════════════════════════════
# 一、视频概要
# ═══════════════════════════════════════
add_heading_styled('一、视频概要', level=2)

summary_table = doc.add_table(rows=7, cols=2, style='Table Grid')
summary_table.alignment = WD_TABLE_ALIGNMENT.CENTER
summary_data = [
    ('视频形态', '真人口播 + 数据动画/屏幕录制混剪'),
    ('建议总时长', '约 120 秒（2 分钟）'),
    ('目标平台', '抖音 / 微信视频号 / 小红书（优先竖屏 9:16）'),
    ('目标受众', '25-45 岁职场人 / 企业中层管理者 / 知识工作者 / 科技从业者'),
    ('情绪弧线', '好奇（这是什么）→ 震惊（数据冲击）→ 共鸣（说的就是我）→ 温暖（还有希望）→ 行动（我要试试）'),
    ('BGM 推荐', '前段：低频电子脉冲/紧张氛围（例：Hans Zimmer 风格底鼓）；中段：钢琴低音单音；尾段：温暖弦乐渐入（例：Max Richter 风格）'),
    ('参考视觉风格', '暗调+镭射光效为主，数据动画部分用霓虹蓝/紫，人文部分切换暖黄调'),
]
for i, (label, value) in enumerate(summary_data):
    add_cell_text(summary_table.cell(i, 0), label, bold=True, size=10, color=(0x33, 0x33, 0x33))
    add_cell_text(summary_table.cell(i, 1), value, size=10)
    set_cell_shading(summary_table.cell(i, 0), 'F5F5F5')
    summary_table.cell(i, 0).width = Cm(3.5)

doc.add_paragraph()

# ═══════════════════════════════════════
# 二、镜次脚本（核心）
# ═══════════════════════════════════════
add_heading_styled('二、镜次脚本（镜次表）', level=2)

add_para('以下为分镜级别的完整拍摄脚本，每个镜次的"画面"列描述摄影/剪辑应呈现的内容，"文案/对白"列为主播口播稿，"字幕/音效"列为后期标注。', size=10, color=(0x66, 0x66, 0x66))

doc.add_paragraph()

# 创建镜次表
shot_table = doc.add_table(rows=1, cols=5, style='Table Grid')
shot_table.alignment = WD_TABLE_ALIGNMENT.CENTER

# 表头
headers = ['镜次', '时长', '画面（摄影/剪辑说明）', '文案/对白（口播稿）', '字幕·音效·备注']
for j, header in enumerate(headers):
    add_cell_text(shot_table.cell(0, j), header, bold=True, size=10, color=(0xFF, 0xFF, 0xFF), align=WD_ALIGN_PARAGRAPH.CENTER)
    set_cell_shading(shot_table.cell(0, j), '1A1A2E')

# 镜次数据
shots = [
    (
        'S1\n开场钩子',
        '0-5s',
        '【画面】纯黑背景，中央一条红色曲线从屏幕左下角开始急速拉升，曲线上方浮现一行白色大字。曲线拉升过程中边缘带微弱的数字噪点效果，像一个正在启动的仪表盘。\n【构图】竖屏居中，红色曲线占画面下方 1/3，文字占上方 2/3。\n【拍摄备注】后期纯动画，无需实拍。',
        '你知道过去一年，AI 行业新增收入的速度变了多少吗？从 180 天，变成了 2 天。',
        '【字幕】全屏居中大字，逐字浮现：\n"180 天 → 2 天"\n【音效】低频心跳声，节奏由慢变快，在"2 天"处一个重拍落下。\n【备注】开场必须在前 3 秒内显示第一个数字"180 天"，否则用户划走。'
    ),
    (
        'S2\n建场',
        '5-15s',
        '【画面】切入博主正面近景口播。博主穿深色简约外套，背景为柔化的暗调书房/工作室环境，右侧有一盏暖黄台灯作为唯一光源，形成温暖与冷峻的视觉对比。博主表情：认真、沉稳，不是震惊体，是"跟你说一件真事"的语气。\n【构图】竖屏 9:16，博主占画面中央偏上 2/3，下巴与屏幕底部对齐。',
        '今年 6 月 25 号，外媒 Exponentialview 出了份报告，说现在全球 AI 经济的年化收入已经超过 1750 亿美元。注意，这不是预测，是已经发生的数字。而且它的增速是当年互联网普及浪潮的——3 倍。',
        '【字幕】"$1750 亿 AI 经济" 在数字出现时用蓝紫色发光字体强调。\n"3x 互联网时代增速" 红色加粗。\n【音效】每出现一个数据数字，配一个轻微的低频"砰"声，像计数器的跳动。\n【备注】博主念"3 倍"时做手势强调（三根手指），给后期裁剪短视频封面用。'
    ),
    (
        'S3\n数据冲击#1',
        '15-35s',
        '【画面】全屏数据动画。\n时间轴从 2023 年初开始快速滚动。画面底部的进度条标注"新增 $10 亿所需天数"，数字不断跳动缩短：180 天→90 天→60 天→30 天→7 天→2 天。每跳动一次，背景红色区域扩大一格，给人一种"加速逼近"的压迫感。\n结尾画面定格在"不到 2 天"，进度条几乎被红色吞没。',
        '2023 年初，AI 行业要新增 10 亿美元营收，需要 180 天。到今年年初，变成了 60 天。上个月，30 天。到了这个星期——不到 2 天。你上一次认真地学一项新技能，花了多久？',
        '【字幕】每个时间数字以大号字体居中震动出现，配合"倒计时音效"。\n最后一个问题"你上一次……花了多久？"切换为白色宋体，字号缩小，节奏突然放慢。\n【音效】进度条滚动的声音从低沉到尖锐，在"不到 2 天"处戛然而止，留白 1 秒。\n【备注】这是全片第一个情绪转折点——从冲击到反思。后期务必在最后一句留 1 秒静默。'
    ),
    (
        'S4\n数据冲击#2',
        '35-45s',
        '【画面】回到博主近景，但这次机位稍退，露出上半身更多。博主面前放了一台笔记本，屏幕朝向镜头方向翻折，屏幕上是报告的封面图（可用设计替代）。博主手指轻敲屏幕上的数字。\n【画中画效果】屏幕区域叠加一个透明对比框：左边"互联网时代渗透速度"，右边"AI 时代渗透速度"，右边的速度条疯狂推进，直接把左边甩出画面。',
        '互联网从普及到改变我们所有人的工作方式，用了大概 15 年。AI 呢？从 ChatGPT 发布到今天，不到 3 年。我再说一遍——不到 3 年。而且它不是停下了，它还在加速。',
        '【字幕】"15 年 vs 3 年" 大号对比，15 年用灰色/划掉效果，3 年用亮红色。\n"它还在加速" 四个字以逐字放大的动效呈现。\n【音效】"不到 3 年"处一个闷重的底鼓落下，然后渐弱的回响。\n【备注】博主说"我再说一遍"时语气要稍微压低，不是愤怒，是强调的沉重感。'
    ),
    (
        'S5\n真实案例',
        '45-70s',
        '【画面】快速切换三组真实案例素材（素材来源标注：Runway 官网 demo / Meta 官方公告 / General Intuition 融资报道截图）：\n① Runway Agent 2.0 界面——输入一句需求，自动生成三版广告并裁切成 9:16/16:9/1:1 的 demo 录制。上标"市场部"。\n② Meta 内部流出的 AI 审核统计图——AI 替代 50% 人工，错误率比人低 13%。上标"内容审核部"，下标小字"每一盏灭掉的灯，都是一个裁撤的岗位"。\n③ General Intuition 融资报道截图——$23 亿估值，用 Fortnite 数据训练 AI 同时打游戏和操控真实机器人。上标"研发部"。\n【转场】每组素材之间用快速闪白过渡，节奏紧凑。',
        '如果我们只看数字，那叫"行业趋势"。但如果我告诉你这些数字正在你的公司里落地——\nRunway 出了个 Agent，可以一次性生成一整周的营销内容，自动裁切好所有平台规格。Meta 用 AI 替代了超过一半的内容审核岗位，而且错误率比人还低 13%。还有家公司的 AI 在打游戏的过程里学会了怎么控制真实机器人，8 分钟就能上街干活。\n你告诉我，你的岗位在哪条安全线上？',
        '【字幕】三个部门的标签（市场部/内容审核部/研发部）用不同颜色的标签条标注。\n"错误率比人低 13%" 后面叠加一行小字："这 13% 的背后是几千个家庭。"\n【音效】三段画面切换时各配一个短促的"切割声"，像纸张被撕裂。\n最后一句"你的岗位在哪条安全线上？"配一个低频嗡鸣，拉长 2 秒。\n【备注】这是全片情绪最低点——无力感和焦虑到达峰值。博主最后一句的语气要从质问转向停顿，不是咄咄逼人，是留白让观众自己回答。'
    ),
    (
        'S6\n情绪翻转',
        '70-95s',
        '【画面】色调从冷蓝紫突然切换为暖黄。博主从面向镜头转为略微侧身，手里拿着一张便签纸（或一本书），表情从严肃转为坦诚、有温度。\n【画中画】屏幕右侧浮现三行白色手写字："被替代的不是人 / 是那个不再学习的自己 / 你从来不只是你的岗位"。\n【镜头运动】极缓慢的推进（dolly in），让观众感觉博主在靠近自己说话。',
        '但我今天做这期视频，不是来吓你们的。\n我想说的是——你感受到的那种不安，是真实的。那个每天早上打开电脑，不知道今天 AI 又会不会抢走什么的感觉——你不是一个人。\n但我们换个角度想：AI 能替代的，从来都是那些可以被流程化、可以被量化、可以被"定义"的东西。而人是不能被定义的。你的直觉、你的共情、你知道"这个产品不应该这样做"不是出于数据而是出于活了这么多年对人的理解——这些东西，AI 没有。',
        '【字幕】手写体逐行浮现，速度与博主口播同步。\n"你从来不只是你的岗位" 最后定格，字号最大。\n【音效】从 S6 开始，BGM 切换为一首温暖的钢琴曲（推荐：Max Richter - "On the Nature of Daylight" 前奏风格），音量渐入，不压口播。\n【备注】这是全片的"温度转折"——从冷到暖、从恐惧到力量。博主的语气要真诚、不加表演感。'
    ),
    (
        'S7\n行动建议',
        '95-110s',
        '【画面】博主正对镜头，画面底部浮现三个图标+短文案的卡片，像 iOS 通知一样逐条弹入：\n① 🧠 "重新理解你的价值"——你的不可替代性在哪里？\n② 🔧 "学会用 AI 放大你的优势"——不是学编程，是学会提问。\n③ 📅 "给自己一个 3 个月的转型计划"——不要等公司来培训你。\n【构图】博主在画面上方 1/3 说话，下方 2/3 留给卡片动画。',
        '所以如果你问我，现在到底该怎么办？我有三句话想送给你：\n第一，重新理解自己的价值。你擅长的到底是什么？不是你的岗位描述上写了什么，是那个让你自己都觉得自己很厉害的东西。\n第二，学会用 AI 放大你的优势。不需要去学编程，但至少要会用 AI 帮你写邮件、做分析、查资料。\n第三，给自己一个 3 个月的转型计划。不要让公司来决定你什么时候被替代——让自己来决定你什么时候升级。',
        '【字幕】三条建议以卡片形式逐条弹入，建议标题加粗，小字说明用常规字重。\n【音效】每条卡片弹入时配一个柔和的"叮"提示音（类似 iOS 消息提示）。\n【备注】三条建议的语速稍快于前面，给人"有希望、有办法"的行动感。'
    ),
    (
        'S8\n收束金句',
        '110-120s',
        '【画面】从博主缓慢拉远（dolly out），博主保持看着镜头的姿势，周围灯光逐渐暗下，只剩博主脸部被一盏顶光照亮。\n屏幕中央浮现前面出现过的所有数据数字——"$1750亿""3x""2天""15年 vs 3年"——像字幕一样从下往上滚动，最后一行定格为金句。\n【终帧】全黑背景，中央一行白色大字。下方小字引导评论+关注。',
        'AI 替代的不是你的工作，它替代的是——你还在用三年前的方式解决今天的问题。而你，从来不只是你的工作。你是那个知道"为什么"的人。',
        "【字幕】金句分两行居中：\u201cAI 替代的不是你的工作 / 它替代的是你还在用旧方法解决新问题\u201d\n【终帧字幕】下方：\u201c你的岗位，AI 能替代多少？评论区告诉我 / 关注我，下期出\u2018转型指南\u2019\u201d\n【音效】说到\u201c而你\u201d时，钢琴和弦落下收束。终帧留 2 秒静默后淡出。\n【备注】关注引导文字要小，不压金句。"
    ),
]

for shot in shots:
    row = shot_table.add_row()
    for j, cell_text in enumerate(shot):
        align = WD_ALIGN_PARAGRAPH.CENTER if j in (0, 1) else WD_ALIGN_PARAGRAPH.LEFT
        add_cell_text(row.cells[j], cell_text, bold=(j == 0), size=9, align=align)
    # 交替行底色
    if shots.index(shot) % 2 == 1:
        for j in range(5):
            set_cell_shading(row.cells[j], 'FAFAFA')

# 设置列宽
widths = [Cm(1.8), Cm(1.2), Cm(5.5), Cm(5.5), Cm(4.5)]
for row in shot_table.rows:
    for j, width in enumerate(widths):
        row.cells[j].width = width

doc.add_paragraph()

# ═══════════════════════════════════════
# 三、主播备注
# ═══════════════════════════════════════
add_heading_styled('三、主播表演指导', level=2)

perf_notes = [
    ('整体基调', '不是"贩卖焦虑"的紧张感，而是"说一件真的很重要的事"的坦诚感。语速：中等偏慢，给观众反应时间。关键数据可以稍快一口气说完再停顿。'),
    ('关键表情节点', 'S2 要认真；S3-S4 可以带一点"我查到这个数据的时候也震惊了"的微表情；S5 语气下沉，但不要沉重到压抑，要留一点"但还有希望"的余地；S6 是真诚的表达，不要表演"温暖"，是真的温暖；S7 语速稍提，给人以行动力。'),
    ('手势建议', 'S2 说"3 倍"时伸三根手指（用作封面素材）；S5 说到"你的岗位"时可以指向镜头（打破第四面墙）；S7 说三条建议时可以逐根伸出手指数数。'),
    ('服装建议', '深色简约外套（藏蓝/深灰/黑），内搭纯色。避免大面积 logo 和过于休闲的卫衣。这套视频的视觉气质是"可信赖的专业朋友"。'),
    ('眼神', '全片保持看镜头。S5 和 S6 的关键句可以略微停顿、眨眼更慢，让观众感觉到你不是在读稿——你是在跟他们对话。'),
]

for label, note in perf_notes:
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(4)
    run_label = p.add_run(f'【{label}】')
    run_label.bold = True
    run_label.font.name = '微软雅黑'
    run_label._element.rPr.rFonts.set(qn('w:eastAsia'), '微软雅黑')
    run_label.font.size = Pt(10)
    run_label.font.color.rgb = RGBColor(0x1A, 0x1A, 0x2E)
    run_text = p.add_run(f' {note}')
    run_text.font.name = '微软雅黑'
    run_text._element.rPr.rFonts.set(qn('w:eastAsia'), '微软雅黑')
    run_text.font.size = Pt(10)

doc.add_paragraph()

# ═══════════════════════════════════════
# 四、后期制作清单
# ═══════════════════════════════════════
add_heading_styled('四、后期制作清单', level=2)

post_items = [
    ('数据动画素材', '① 红色加速曲线（0→180 天→2 天）；② 双曲线对比图（AI 增速 vs 人类学习速度）；③ 时间轴滚动缩短动画；④ "15 年 vs 3 年"对比框。建议用 After Effects 制作，霓虹蓝紫色系 + 暗黑底色。'),
    ('实拍素材/参考图', '① Runway Agent 2.0 操作录屏（官网 demo 可截取）；② Meta AI 审核界面概念图（可用 UI 设计替代，标注数据来源）；③ General Intuition 融资报道截图；④ Exponentialview 报告封面。'),
    ('转场风格', 'S2→S3：数据"炸开"效果转场；S3→S4：博主推镜转场；S4→S5：快速闪白三次；S5→S6：色调从冷到暖的渐变换色（关键！）；S6→S7：柔和的交叉溶解；S7→S8：缓慢推向黑暗。'),
    ('调色方案', 'S1-S5：暗调为主，阴影偏蓝紫色，高光偏冷白。S6-S8：阴影色调从蓝紫逐渐过渡到橙红暖调，高光保留暖黄色，模拟"天亮"的感觉。'),
    ('字幕样式', '数字/数据用粗体霓虹蓝紫色字体（例：Montserrat Bold）；口播字幕用白色细体描深色阴影；金句用手写体（例：站酷快乐体或类似的温暖手写风格）。字号根据竖屏 1080×1920 适配。'),
    ('终帧封面', '建议从 S8 结尾截取一帧，叠加金句文字。封面需包含：① 主标题（12 字以内）；② 副标题（数据钩子）；③ 博主大头照或视频内高情绪帧。'),
]

for label, detail in post_items:
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(4)
    run_label = p.add_run(f'【{label}】')
    run_label.bold = True
    run_label.font.name = '微软雅黑'
    run_label._element.rPr.rFonts.set(qn('w:eastAsia'), '微软雅黑')
    run_label.font.size = Pt(10)
    run_label.font.color.rgb = RGBColor(0x1A, 0x1A, 0x2E)
    run_text = p.add_run(f' {detail}')
    run_text.font.name = '微软雅黑'
    run_text._element.rPr.rFonts.set(qn('w:eastAsia'), '微软雅黑')
    run_text.font.size = Pt(10)

doc.add_paragraph()

# ═══════════════════════════════════════
# 五、素材来源清单
# ═══════════════════════════════════════
add_heading_styled('五、数据与素材来源', level=2)

sources = [
    ('Exponentialview《State of the AI Economy》报告', 'https://x.com/rohanpaul_ai/status/2070288396644491317'),
    ('Runway Agent 2.0 官方发布', 'https://runwayml.com/news/introducing-agent-2'),
    ('Meta AI 内容审核替代人工（The Decoder 报道）', 'https://the-decoder.com/meta-employees-warn-ai-moderation-rollout-is-too-fast'),
    ('General Intuition $32 亿融资（TechCrunch 报道）', 'https://techcrunch.com/2026/06/25/from-fortnite-to-robots-general-intuitions-2-3b-bet-that-video-games-can-train-ai-agents-for-the-real-world'),
    ('AI HOT 聚合平台', 'https://aihot.virxact.com'),
]

for i, (desc, url) in enumerate(sources, 1):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(3)
    run = p.add_run(f'{i}. {desc}\n   {url}')
    run.font.name = '微软雅黑'
    run._element.rPr.rFonts.set(qn('w:eastAsia'), '微软雅黑')
    run.font.size = Pt(9)
    run.font.color.rgb = RGBColor(0x88, 0x88, 0x88)

doc.add_paragraph()

# ═══════════════════════════════════════
# 六、多形态分发建议
# ═══════════════════════════════════════
add_heading_styled('六、配套传播物料', level=2)

add_para('本条短视频为"三连发"策略的第一枪（抢流量+建立情绪认知），后续配套：', size=10)

companion = [
    '视频发布后 2h：朋友圈配文 + 金句海报（"AI 不是在抢你的工作，它是在问你——除了这份工作，你还是谁？"）——引流到视频号。',
    '次日 10:00：公众号深度长文（3000-4000 字，含完整数据拆解 + 转型行动指南 + 真人故事）——做收藏和二次传播。',
    '次日 16:00：H5 互动测试《你的岗位 AI 替代指数》上线——评论区引导用户晒测试结果，做第二轮自然裂变。',
    'Day 3：评论区精选 5 条最扎心的留言，录制"回应视频"——"上周你们说最怕被替代的 5 个岗位，我帮你们分析了一下。"',
]
for item in companion:
    p = doc.add_paragraph(item, style='List Bullet')
    for run in p.runs:
        run.font.name = '微软雅黑'
        run._element.rPr.rFonts.set(qn('w:eastAsia'), '微软雅黑')
        run.font.size = Pt(10)

# ── 保存 ──
output_dir = '/Users/dielangli/Desktop/优创Hub AI工作坊/线上媒体推广/视频创作'
os.makedirs(output_dir, exist_ok=True)
output_path = os.path.join(output_dir, '短视频脚本_AI速度差_人文关怀.docx')
doc.save(output_path)
print(f'✅ 已保存：{output_path}')
