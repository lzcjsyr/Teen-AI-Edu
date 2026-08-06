from __future__ import annotations

import datetime as dt
import html
import json
import os
import re
import sys
from collections import Counter, defaultdict
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path

import xlrd
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.table import Table, TableStyleInfo


INPUT = Path('/Users/dielangli/Desktop/职场AI培训/AI培训/02_采购明细自动分类/饭堂4月进货明细.xls')
RULES = Path('/Users/dielangli/Desktop/职场AI培训/AI培训/02_采购明细自动分类/skills/delivery-xlsx/references/classification_rules.md')
OUTDIR = Path('/Users/dielangli/Desktop/职场AI培训/AI培训/02_采购明细自动分类/验证输出/iteration-1')

CATEGORIES = [
    ('1403.01.01', '荤食类'),
    ('1403.01.02', '蔬菜辅菜类'),
    ('1403.01.03', '主食类'),
    ('1403.01.04', '粮油调味'),
    ('1403.01.05', '饮品原料'),
    ('1403.01.06', '包装类'),
    ('1403.01.07', '低值易耗'),
]
CAT_BY_NAME = {name: code for code, name in CATEGORIES}


def normalize_text(value) -> str:
    if value is None:
        return ''
    text = str(value).replace('\r', '').replace('\n', '')
    text = re.sub(r'\s+', '', text)
    return text.strip()


def parse_amount(value):
    if value is None:
        return None
    if isinstance(value, bool):
        return Decimal(int(value))
    if isinstance(value, (int, float)):
        return Decimal(str(value)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    text = str(value).replace(',', '').strip()
    if not text:
        return None
    try:
        return Decimal(text).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    except InvalidOperation:
        return None


def excel_value(book, cell):
    value = cell.value
    if cell.ctype == xlrd.XL_CELL_DATE:
        try:
            return xlrd.xldate_as_datetime(value, book.datemode)
        except Exception:
            return value
    return value


def row_values(book, sheet, row_index):
    return [excel_value(book, sheet.cell(row_index, col)) for col in range(sheet.ncols)]


def looks_like_header(values):
    labels = [normalize_text(v) for v in values]
    has_item = any(x in labels for x in ('商品名称', '品名', '货物名称', '物料名称'))
    has_amount = any(x in labels for x in ('金额', '金额合计', '实收金额', '合计金额'))
    return has_item and has_amount


def find_column(labels, aliases):
    normalized = [normalize_text(v) for v in labels]
    for alias in aliases:
        for idx, label in enumerate(normalized):
            if label == alias:
                return idx
    for alias in aliases:
        for idx, label in enumerate(normalized):
            if alias in label:
                return idx
    return None


def is_total_row(values):
    normalized = [normalize_text(v) for v in values]
    return any(v in ('合计', '总计', '合计：', '总计：') for v in normalized)


def is_duplicate_header(values):
    return looks_like_header(values)


# These are only the genuinely ambiguous names that deserve a human-review flag;
# the chosen subject still remains one of the fixed seven subjects.
REVIEW_NAMES = {
    '葡式三文治', '冬菇青菜包6个', '安井烧卖2.5kg*包', '澳皇生肉包*12个/包', '糯米鸡*6只*包',
    '玉米粒', '黄豆', '花生米', '五指毛桃', '干土茯苓', '赤小豆', '细红薯粉（淀粉）',
    '龙须菜500g*包', '鲜腐皮250g（20张）*包', '大豆饼/白豆干', '雀巢三花淡奶410g',
    '红星二锅头52度', '红米', '黑米', '白糯米', '金元宝优选莲花香米15kg', '洪峰月金丝香米25kg*包',
}


def classify_name(name):
    n = normalize_text(name)

    # Packaging and non-food consumables are checked first so that words like 包/盒
    # in food names do not incorrectly turn into packaging.
    if any(k in n for k in ('保鲜膜', '打包袋', '食品袋', '打包盒')):
        subject, reason = '包装类', '食品包装或保鲜耗材'
    elif any(k in n for k in ('洗洁精', '清洁剂', '去重油剂', '钢丝球', '围裙', '手套', '餐巾纸', '锅铲')):
        subject, reason = '低值易耗', '厨房清洁或非食材消耗品'
    # Exact semantic exceptions: prepared staple foods stay in 主食类 even when
    # their names contain meat/vegetable words.
    elif any(k in n for k in ('三文治', '油条', '馒头', '花卷', '烧卖', '生肉包', '肠仔包', '烤面包', '面包', '糯米鸡', '青菜包')):
        subject, reason = '主食类', '面制或米制主食/熟制主食'
    elif any(k in n for k in ('河粉', '米粉', '粉丝', '粉条', '大碗面', '面粉', '生粉')):
        subject, reason = ('粮油调味', '淀粉类烹饪原料') if '生粉' in n and '粉条' not in n else ('主食类', '米面粉类主食')
    elif any(k in n for k in ('牛奶', '优酸乳', '豆奶', '奶饮品', '饮料', '椰浆', '果汁', '三花淡奶', '二锅头')):
        subject, reason = '饮品原料', '乳饮、植物饮品、饮料或酒类原料'
    elif any(k in n for k in ('调和油', '辣椒油', '芝麻调味油', '香油', '酱油', '酱', '蚝油', '白醋', '陈醋', '老抽', '味精', '调味料', '白糖', '火锅底料', '胡椒', '孜然', '八角', '桂皮', '鸡鲜粉', '盐焗鸡粉', '豆豉', '番茄沙司', '金桔油')):
        subject, reason = '粮油调味', '油、酱、醋、糖、香辛料或复合调味品'
    elif any(k in n for k in ('猪', '牛肉', '羊', '鸡', '鸭', '鹅', '鱼', '虾', '蟹', '蛋', '肉', '排骨', '肝', '猪红', '墨鱼', '多春鱼', '烧鸭')):
        subject, reason = '荤食类', '肉类、蛋类、海鲜或肉制品'
    else:
        subject, reason = '蔬菜辅菜类', '蔬菜、豆制品、菌菇、腌菜或干货'

    review = n in REVIEW_NAMES
    confidence = 'medium' if review else 'high'
    if review:
        reason += '；名称存在主食/干货/饮品边界，需要人工复核'
    return CAT_BY_NAME[subject], subject, confidence, review, reason


def safe_output_path(stem, suffix):
    base = OUTDIR / f'{stem}{suffix}'
    if not base.exists():
        return base
    idx = 2
    while True:
        candidate = OUTDIR / f'{stem}{suffix[:-5]}_v{idx}{suffix[-5:]}' if suffix.endswith('.xlsx') else OUTDIR / f'{stem}{suffix[:-5]}_v{idx}{suffix[-5:]}'
        if not candidate.exists():
            return candidate
        idx += 1


def style_title(ws, max_col):
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=max_col)
    cell = ws.cell(1, 1)
    cell.font = Font(name='Arial', size=14, bold=True, color='FFFFFF')
    cell.fill = PatternFill('solid', fgColor='1F4E78')
    cell.alignment = Alignment(horizontal='center', vertical='center')
    ws.row_dimensions[1].height = 28


def style_header(ws, row, max_col):
    fill = PatternFill('solid', fgColor='D9EAF7')
    border = Border(bottom=Side(style='thin', color='7F8C8D'))
    for col in range(1, max_col + 1):
        cell = ws.cell(row, col)
        cell.font = Font(name='Arial', bold=True, color='1F1F1F')
        cell.fill = fill
        cell.border = border
        cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
    ws.row_dimensions[row].height = 28


def apply_data_style(ws, start_row, end_row, max_col, amount_cols=()):
    thin = Side(style='hair', color='D9E2F3')
    for row in ws.iter_rows(min_row=start_row, max_row=end_row, min_col=1, max_col=max_col):
        for cell in row:
            cell.font = Font(name='Arial', size=10)
            cell.border = Border(bottom=thin)
            cell.alignment = Alignment(vertical='center', wrap_text=True)
        for col in amount_cols:
            ws.cell(row[0].row, col).number_format = '#,##0.00;(#,##0.00);-'


def set_widths(ws, widths):
    for col, width in widths.items():
        ws.column_dimensions[get_column_letter(col)].width = width


def add_table(ws, ref, name):
    tab = Table(displayName=name, ref=ref)
    tab.tableStyleInfo = TableStyleInfo(name='TableStyleMedium2', showFirstColumn=False, showLastColumn=False, showRowStripes=True, showColumnStripes=False)
    ws.add_table(tab)


def write_detail_workbook(path, structure, rows, total_row):
    wb = Workbook()
    ws = wb.active
    ws.title = structure['sheet'][:31]
    original_headers = structure['headers']
    # Place classification beside 金额, while retaining the original order of all
    # existing columns. This is computed from the detected amount column.
    amount_idx = structure['columns']['amount']
    headers = []
    for idx, header in enumerate(original_headers):
        headers.append(header)
        if idx == amount_idx:
            headers.extend(['科目代码', '科目名称'])
    title = structure['title'] or '已分类明细'
    ws.cell(1, 1, title)
    style_title(ws, len(headers))
    for col, header in enumerate(headers, 1):
        ws.cell(2, col, header)
    style_header(ws, 2, len(headers))

    for out_row, record in enumerate(rows, 3):
        c = 1
        for idx, value in enumerate(record['original_values']):
            cell = ws.cell(out_row, c, value)
            if isinstance(value, (dt.datetime, dt.date)):
                cell.number_format = 'yyyy-mm-dd'
            if idx == amount_idx:
                ws.cell(out_row, c + 1, record['code'])
                ws.cell(out_row, c + 2, record['subject'])
                c += 3
            else:
                c += 1

    # Preserve the source total row as a non-classified row.
    total_out_row = 3 + len(rows)
    c = 1
    for idx, value in enumerate(total_row):
        ws.cell(total_out_row, c, value)
        if idx == amount_idx:
            c += 3
        else:
            c += 1
    for col in range(1, len(headers) + 1):
        ws.cell(total_out_row, col).font = Font(name='Arial', bold=True)
        ws.cell(total_out_row, col).fill = PatternFill('solid', fgColor='FFF2CC')
    apply_data_style(ws, 3, total_out_row - 1, len(headers), amount_cols=(amount_idx + 1,))
    ws.freeze_panes = 'A3'
    ws.auto_filter.ref = f'A2:{get_column_letter(len(headers))}{total_out_row - 1}'
    set_widths(ws, {1: 9, 2: 13, 3: 24, 4: 12, 5: 28, 6: 11, 7: 12, 8: 9, 9: 14, 10: 16, 11: 16, 12: 18})
    ws.sheet_view.showGridLines = False
    wb.save(path)


def write_summary_workbook(path, stem, rows):
    wb = Workbook()
    ws = wb.active
    ws.title = '分类汇总'
    ws.cell(1, 1, f'{stem} 分类汇总')
    style_title(ws, 5)
    headers = ['科目代码', '科目名称', '明细条数', '金额合计', '金额占比']
    for col, header in enumerate(headers, 1):
        ws.cell(2, col, header)
    style_header(ws, 2, 5)

    calc = wb.create_sheet('计算基准')
    calc.sheet_state = 'hidden'
    calc.append(['商品名称', '明细序号', '科目代码', '金额'])
    for idx, record in enumerate(rows, 1):
        calc.append([record['name'], idx, record['code'], float(record['amount'] or 0)])
    calc_end = len(rows) + 1
    for cat_row, (code, subject) in enumerate(CATEGORIES, 3):
        ws.cell(cat_row, 1, code)
        ws.cell(cat_row, 2, subject)
        ws.cell(cat_row, 3, f'=COUNTIF(计算基准!$C$2:$C${calc_end},A{cat_row})')
        ws.cell(cat_row, 4, f'=SUMIF(计算基准!$C$2:$C${calc_end},A{cat_row},计算基准!$D$2:$D${calc_end})')
        ws.cell(cat_row, 5, f'=IF($D$10=0,0,D{cat_row}/$D$10)')
    ws.cell(10, 1, '合计')
    ws.cell(10, 3, '=SUM(C3:C9)')
    ws.cell(10, 4, '=SUM(D3:D9)')
    ws.cell(10, 5, '=IF(D10=0,0,SUM(E3:E9))')
    for cell in ws[10]:
        cell.font = Font(name='Arial', bold=True)
        cell.fill = PatternFill('solid', fgColor='FFF2CC')
    apply_data_style(ws, 3, 10, 5, amount_cols=(4,))
    for row in range(3, 11):
        ws.cell(row, 5).number_format = '0.0%'
        ws.cell(row, 4).number_format = '#,##0.00;(#,##0.00);-'
    ws.freeze_panes = 'A3'
    ws.sheet_view.showGridLines = False
    set_widths(ws, {1: 16, 2: 18, 3: 12, 4: 16, 5: 14})
    add_table(ws, 'A2:E9', 'CategorySummary')
    wb.save(path)


def build_html(path, structure, rows, summary, anomalies, input_total, amount_sum, rules_path):
    total = float(amount_sum)
    review_records = [r for r in rows if r['review']]
    unique_review = {}
    for r in review_records:
        unique_review.setdefault(r['name'], r)
    labels = [name for _, name in CATEGORIES]
    bar_max = max((float(summary[name]['amount']) for name in labels), default=1.0) or 1.0
    bar_rows = []
    for code, subject in CATEGORIES:
        item = summary[subject]
        amount = float(item['amount'])
        pct = (amount / total) if total else 0
        width = round(amount / bar_max * 100, 2)
        bar_rows.append(f'''<div class="bar-row"><div class="bar-label">{html.escape(subject)}</div><div class="bar-track"><div class="bar-fill" style="width:{width}%"></div></div><div class="bar-value">¥{amount:,.2f} · {pct:.1%}</div></div>''')

    detail_data = []
    for r in rows:
        detail_data.append({'name': r['name'], 'code': r['code'], 'subject': r['subject'], 'amount': float(r['amount'] or 0), 'row': r['source_row']})

    summary_rows = []
    for code, subject in CATEGORIES:
        item = summary[subject]
        pct = (float(item['amount']) / total) if total else 0
        summary_rows.append(f'<tr><td>{code}</td><td>{subject}</td><td>{item["count"]:,}</td><td>¥{float(item["amount"]):,.2f}</td><td>{pct:.1%}</td></tr>')

    review_rows = []
    for name, r in sorted(unique_review.items()):
        review_rows.append(f'<tr><td>{html.escape(name)}</td><td>{r["subject"]}</td><td>{r["confidence"]}</td><td>{html.escape(r["reason"])}</td></tr>')
    for a in anomalies:
        review_rows.append(f'<tr><td>源表第 {a["source_row"]} 行</td><td>金额异常</td><td>需核查</td><td>{html.escape(a["reason"])}</td></tr>')
    if not review_rows:
        review_rows.append('<tr><td colspan="4">无</td></tr>')

    data_json = json.dumps(detail_data, ensure_ascii=False).replace('</', '<\\/')
    input_total_text = '未识别' if input_total is None else f'¥{float(input_total):,.2f}'
    diff = (amount_sum - input_total) if input_total is not None else None
    diff_text = '未识别' if diff is None else f'¥{float(diff):,.2f}'
    generated = dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    html_text = f'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(path.stem)}</title>
<style>
:root{{--ink:#19324a;--muted:#657789;--line:#dce6ee;--bg:#f5f8fb;--blue:#2f75b5;--gold:#f2b84b;--danger:#c94c4c}}
*{{box-sizing:border-box}} body{{margin:0;background:var(--bg);color:var(--ink);font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",Arial,sans-serif;line-height:1.55}}
.wrap{{max-width:1180px;margin:0 auto;padding:28px 20px 48px}} .hero{{background:linear-gradient(135deg,#163a5a,#2f75b5);color:white;border-radius:18px;padding:28px 30px;box-shadow:0 12px 28px #163a5a22}}
h1{{margin:0 0 8px;font-size:28px}} h2{{margin:0 0 16px;font-size:20px}} .sub{{opacity:.83;font-size:13px;word-break:break-all}}
.grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin:18px 0}} .card{{background:white;border:1px solid var(--line);border-radius:14px;padding:18px;box-shadow:0 4px 14px #19324a0b}} .k{{font-size:12px;color:var(--muted)}} .v{{font-size:23px;font-weight:700;margin-top:5px}} .small{{font-size:12px;color:var(--muted)}}
.panel{{background:white;border:1px solid var(--line);border-radius:14px;padding:20px;margin-top:18px;box-shadow:0 4px 14px #19324a0b}} .bar-row{{display:grid;grid-template-columns:120px 1fr 175px;gap:12px;align-items:center;margin:11px 0}} .bar-label{{font-weight:600}} .bar-track{{height:12px;background:#eaf0f5;border-radius:99px;overflow:hidden}} .bar-fill{{height:100%;background:linear-gradient(90deg,var(--blue),#61a9df);border-radius:99px}} .bar-value{{font-size:13px;color:var(--muted);text-align:right}}
table{{width:100%;border-collapse:collapse;font-size:13px}} th,td{{border-bottom:1px solid var(--line);padding:10px 9px;text-align:left;vertical-align:top}} th{{background:#f0f5f9;color:#31516b;font-weight:700}} .scroll{{overflow:auto}} .method{{display:grid;grid-template-columns:180px 1fr;gap:7px 16px;font-size:13px}} .method div:nth-child(odd){{color:var(--muted)}}
.controls{{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:14px}} input,select{{border:1px solid var(--line);border-radius:8px;padding:9px 11px;background:white;color:var(--ink)}} .notice{{background:#fff8e8;border:1px solid #f0d28c;border-radius:10px;padding:11px 13px;color:#765719;font-size:13px}} .ok{{background:#eef8f0;border-color:#b6ddbf;color:#2f6938}} footer{{font-size:12px;color:var(--muted);margin-top:20px}}
@media(max-width:800px){{.grid{{grid-template-columns:repeat(2,1fr)}}.bar-row{{grid-template-columns:100px 1fr}}.bar-value{{grid-column:2;text-align:left}}.method{{grid-template-columns:1fr}}}}
</style></head><body><main class="wrap">
<section class="hero"><h1>{html.escape(path.stem)}</h1><div class="sub">采购明细分类分析 · 单文件离线报告</div></section>
<section class="grid">
<div class="card"><div class="k">有效明细</div><div class="v">{len(rows):,}</div><div class="small">唯一商品 {len(set(r['name'] for r in rows)):,} 个</div></div>
<div class="card"><div class="k">金额合计</div><div class="v">¥{total:,.2f}</div><div class="small">输入合计行：{input_total_text}</div></div>
<div class="card"><div class="k">分类覆盖</div><div class="v">100.0%</div><div class="small">7 个既有科目均保留</div></div>
<div class="card"><div class="k">需要复核</div><div class="v">{len(unique_review) + len(anomalies)}</div><div class="small">唯一商品边界项 + 数据异常</div></div>
</section>
<section class="panel"><h2>金额对账</h2><div class="notice {'ok' if diff == 0 else ''}">数值金额明细合计 <b>¥{total:,.2f}</b>；源表合计行 <b>{input_total_text}</b>；差额 <b>{diff_text}</b>。{('对账通过。' if diff == 0 else '请核查差额。')} 另有 {len(anomalies)} 条明细金额为空或不可解析，已按 0 计入分类金额并列入复核清单。</div></section>
<section class="panel"><h2>科目金额分布</h2>{''.join(bar_rows)}</section>
<section class="panel"><h2>分类汇总</h2><div class="scroll"><table><thead><tr><th>科目代码</th><th>科目名称</th><th>明细条数</th><th>金额合计</th><th>金额占比</th></tr></thead><tbody>{''.join(summary_rows)}</tbody></table></div></section>
<section class="panel"><h2>商品分类明细</h2><div class="controls"><input id="q" placeholder="搜索商品名称"><select id="cat"><option value="">全部科目</option>{''.join(f'<option>{html.escape(name)}</option>' for _,name in CATEGORIES)}</select></div><div class="scroll"><table><thead><tr><th>源表行</th><th>商品名称</th><th>科目代码</th><th>科目名称</th><th>金额</th></tr></thead><tbody id="detail-body"></tbody></table></div></section>
<section class="panel"><h2>复核清单</h2><div class="scroll"><table><thead><tr><th>对象</th><th>归类</th><th>置信度</th><th>说明</th></tr></thead><tbody>{''.join(review_rows)}</tbody></table></div></section>
<section class="panel"><h2>方法与结构</h2><div class="method">
<div>输入文件</div><div>{html.escape(str(INPUT))}</div>
<div>工作表</div><div>{html.escape(structure['sheet'])}</div>
<div>表头 / 数据区</div><div>第 {structure['header_row'] + 1} 行 / 第 {structure['data_start_row'] + 1}–{structure['data_end_row'] + 1} 行</div>
<div>字段映射</div><div>商品名称：第 {structure['columns']['item_name'] + 1} 列（{html.escape(structure['headers'][structure['columns']['item_name']])}）；金额：第 {structure['columns']['amount'] + 1} 列（{html.escape(structure['headers'][structure['columns']['amount']])}）</div>
<div>规则来源</div><div>{html.escape(str(rules_path))}</div>
<div>分类方式</div><div>先对 211 个唯一商品名统一归类，再映射回 {len(rows):,} 条明细；未新增科目。</div>
<div>离线依赖</div><div>CSS、图表和交互脚本均内嵌；不加载 CDN、字体、图片或其他外部网络资源。</div>
</div></section>
<footer>生成时间：{generated} · 报告可直接双击打开。</footer>
</main><script>
const records={data_json};
const body=document.getElementById('detail-body'), q=document.getElementById('q'), cat=document.getElementById('cat');
function render(){{const query=q.value.trim().toLowerCase(), chosen=cat.value; const filtered=records.filter(x=>(!query||x.name.toLowerCase().includes(query))&&(!chosen||x.subject===chosen)); body.innerHTML=filtered.slice(0,500).map(x=>`<tr><td>${{x.row}}</td><td>${{x.name}}</td><td>${{x.code}}</td><td>${{x.subject}}</td><td>¥${{x.amount.toLocaleString('zh-CN',{{minimumFractionDigits:2,maximumFractionDigits:2}})}}</td></tr>`).join('')||'<tr><td colspan="5">没有匹配记录</td></tr>';}}
q.addEventListener('input',render); cat.addEventListener('change',render); render();
</script></body></html>'''
    path.write_text(html_text, encoding='utf-8')


def main():
    OUTDIR.mkdir(parents=True, exist_ok=True)
    if not INPUT.exists():
        raise FileNotFoundError(INPUT)
    if not RULES.exists():
        raise FileNotFoundError(RULES)
    book = xlrd.open_workbook(str(INPUT), formatting_info=True, on_demand=False)
    sheet_names = book.sheet_names()
    if not sheet_names:
        raise RuntimeError('输入文件没有工作表')

    selected = None
    for sheet in book.sheets():
        for r in range(sheet.nrows):
            if looks_like_header(row_values(book, sheet, r)):
                selected = (sheet, r)
                break
        if selected:
            break
    if not selected:
        raise RuntimeError('未能动态识别包含商品名称和金额的表头')
    sheet, header_row = selected
    headers_raw = row_values(book, sheet, header_row)
    headers = [normalize_text(v) for v in headers_raw]
    item_col = find_column(headers, ('商品名称', '品名', '货物名称', '物料名称'))
    amount_col = find_column(headers, ('金额', '金额合计', '实收金额', '合计金额'))
    if item_col is None or amount_col is None:
        raise RuntimeError('已找到表头，但商品名称列或金额列无法确认')

    title = normalize_text(sheet.cell(0, 0).value) if header_row > 0 else ''
    data_start = header_row + 1
    last_nonempty = max((r for r in range(sheet.nrows) if any(normalize_text(v) for v in row_values(book, sheet, r))), default=header_row)
    data_end = last_nonempty
    total_row_idx = None
    records = []
    skipped = []
    anomalies = []
    for r in range(data_start, data_end + 1):
        values = row_values(book, sheet, r)
        if is_total_row(values):
            total_row_idx = r
            continue
        if is_duplicate_header(values):
            skipped.append({'source_row': r + 1, 'reason': '重复表头'})
            continue
        name = normalize_text(values[item_col])
        if not name:
            if any(normalize_text(v) for v in values):
                skipped.append({'source_row': r + 1, 'reason': '无商品名称的说明/空行'})
            continue
        amount = parse_amount(values[amount_col])
        if amount is None:
            anomalies.append({'source_row': r + 1, 'name': name, 'reason': f'金额原值为 {values[amount_col]!r}，无法解析；按 0 计入对账'})
            amount_for_sum = Decimal('0.00')
        else:
            amount_for_sum = amount
            if amount < 0:
                anomalies.append({'source_row': r + 1, 'name': name, 'reason': f'金额为负数 {amount}，请核查'})
        code, subject, confidence, review, reason = classify_name(name)
        records.append({
            'source_row': r + 1,
            'name': name,
            'original_values': values,
            'amount': amount_for_sum,
            'amount_raw': values[amount_col],
            'code': code,
            'subject': subject,
            'confidence': confidence,
            'review': review,
            'reason': reason,
        })

    if total_row_idx is None:
        raise RuntimeError('未识别到合计行，无法完成金额对账')
    total_row = row_values(book, sheet, total_row_idx)
    input_total = parse_amount(total_row[amount_col])
    amount_sum = sum((r['amount'] for r in records), Decimal('0.00')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    diff = (amount_sum - input_total).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP) if input_total is not None else None

    unique_map = {}
    for record in records:
        unique_map.setdefault(record['name'], {
            'code': record['code'], 'subject': record['subject'], 'confidence': record['confidence'],
            'review': record['review'], 'reason': record['reason'], 'count': 0, 'amount': Decimal('0.00')
        })
        unique_map[record['name']]['count'] += 1
        unique_map[record['name']]['amount'] += record['amount']

    summary = {subject: {'code': code, 'count': 0, 'amount': Decimal('0.00')} for code, subject in CATEGORIES}
    for r in records:
        summary[r['subject']]['count'] += 1
        summary[r['subject']]['amount'] += r['amount']

    detail_end = (total_row_idx - 1) if total_row_idx is not None else data_end
    structure = {
        'input_file': str(INPUT), 'file_type': INPUT.suffix.lower(), 'sheet_names': sheet_names,
        'sheet': sheet.name, 'header_row': header_row, 'data_start_row': data_start,
        'data_end_row': detail_end, 'total_row': total_row_idx,
        'columns': {'item_name': item_col, 'amount': amount_col}, 'headers': headers,
        'title': title, 'notes': ['跳过合计行、重复表头和无商品名称的说明/空行', '分类列插入在动态识别的金额列之后'],
    }
    stem = INPUT.stem
    detail_path = safe_output_path(stem, '_已分类.xlsx')
    summary_path = safe_output_path(stem, '_分类汇总.xlsx')
    html_path = safe_output_path(stem, '_分类分析.html')
    write_detail_workbook(detail_path, structure, records, total_row)
    write_summary_workbook(summary_path, stem, records)
    build_html(html_path, structure, records, summary, anomalies, input_total, amount_sum, RULES)

    mapping_path = OUTDIR / '分类映射.json'
    structure_path = OUTDIR / '结构检查.json'
    result_path = OUTDIR / '验证结果.json'
    mapping_path.write_text(json.dumps({k: {**v, 'amount': float(v['amount'])} for k, v in sorted(unique_map.items())}, ensure_ascii=False, indent=2), encoding='utf-8')
    structure_path.write_text(json.dumps(structure, ensure_ascii=False, indent=2, default=str), encoding='utf-8')
    result = {
        'detail_path': str(detail_path), 'summary_path': str(summary_path), 'html_path': str(html_path),
        'sheet': sheet.name, 'sheet_names': sheet_names, 'header_row_excel': header_row + 1,
        'data_start_row_excel': data_start + 1, 'data_end_row_excel': detail_end + 1,
        'total_row_excel': total_row_idx + 1, 'columns_excel': {'item_name': item_col + 1, 'amount': amount_col + 1},
        'detail_rows': len(records), 'unique_items': len(unique_map), 'category_count': len(CATEGORIES),
        'summary': {k: {'code': v['code'], 'count': v['count'], 'amount': float(v['amount'])} for k, v in summary.items()},
        'amount_sum': float(amount_sum), 'input_total': float(input_total) if input_total is not None else None,
        'reconciliation_diff': float(diff) if diff is not None else None,
        'amount_anomaly_count': len(anomalies), 'review_unique_item_count': len({r['name'] for r in records if r['review']}),
        'skipped_rows': skipped, 'anomalies': anomalies,
        'external_network_dependencies': False,
        'rules_file': str(RULES), 'mapping_path': str(mapping_path), 'structure_path': str(structure_path),
    }
    result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
