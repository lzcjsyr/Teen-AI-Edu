from __future__ import annotations

import html
import importlib.util
import json
import re
from collections import defaultdict
from pathlib import Path

from openpyxl import load_workbook
from openpyxl.styles import Alignment, Font, PatternFill, Border, Side
from openpyxl.utils import get_column_letter


BASE_SCRIPT = Path('/Users/dielangli/Desktop/职场AI培训/AI培训/02_采购明细自动分类/验证输出/iteration-1/verify_delivery_xlsx.py')
INPUT = Path('/Users/dielangli/Desktop/职场AI培训/AI培训/02_采购明细自动分类/饭堂4月进货明细.xls')
REFERENCE = Path('/Users/dielangli/Desktop/职场AI培训/AI培训/02_采购明细自动分类/参考成果/饭堂4月进货明细_已分类.xlsx')
RULES = Path('/Users/dielangli/Desktop/职场AI培训/AI培训/02_采购明细自动分类/skills/delivery-xlsx/references/classification_rules.md')
OUTDIR = Path('/Users/dielangli/Desktop/职场AI培训/AI培训/02_采购明细自动分类/验证输出/iteration-2')


def load_base_module():
    spec = importlib.util.spec_from_file_location('delivery_xlsx_base', BASE_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f'无法加载基础生成逻辑：{BASE_SCRIPT}')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def normalize(value):
    return re.sub(r'\s+', '', str(value or '').replace('\r', '').replace('\n', '')).strip()


def scan_reference(base):
    wb = load_workbook(REFERENCE, data_only=True, read_only=False)
    selected = None
    for ws in wb.worksheets:
        for row_idx in range(1, ws.max_row + 1):
            values = [ws.cell(row_idx, col).value for col in range(1, ws.max_column + 1)]
            if base.looks_like_header(values):
                selected = (ws, row_idx)
                break
        if selected:
            break
    if not selected:
        raise RuntimeError('参考成果中未识别到包含商品名称和金额的表头')
    ws, header_row = selected
    headers = [base.normalize_text(ws.cell(header_row, col).value) for col in range(1, ws.max_column + 1)]
    item_col = base.find_column(headers, ('商品名称', '品名', '货物名称', '物料名称'))
    code_col = base.find_column(headers, ('科目代码',))
    subject_col = base.find_column(headers, ('科目名称',))
    amount_col = base.find_column(headers, ('金额', '金额合计', '实收金额', '合计金额'))
    if None in (item_col, code_col, subject_col, amount_col):
        raise RuntimeError('参考成果缺少商品名称、科目代码、科目名称或金额列')

    mapping = {}
    mapping_conflicts = []
    summary = defaultdict(lambda: {'code': '', 'count': 0, 'amount': 0.0})
    names = set()
    detail_rows = 0
    total_row = None
    for r in range(header_row + 1, ws.max_row + 1):
        values = [ws.cell(r, col).value for col in range(1, ws.max_column + 1)]
        if base.is_total_row(values):
            total_row = r
            continue
        name = normalize(values[item_col])
        code = normalize(values[code_col])
        subject = normalize(values[subject_col])
        if not name:
            continue
        detail_rows += 1
        names.add(name)
        if name in mapping and mapping[name][:2] != (code, subject):
            mapping_conflicts.append({'name': name, 'previous': mapping[name][:2], 'current': (code, subject), 'source_row': r + 1})
        else:
            mapping[name] = (code, subject, 'high', False, '沿用参考成果中的相同/标准化商品名称分类')
        amount = base.parse_amount(values[amount_col])
        summary[subject]['code'] = code
        summary[subject]['count'] += 1
        summary[subject]['amount'] += float(amount or 0)
    return {
        'sheet': ws.title,
        'header_row': header_row - 1,
        'data_start_row': header_row,
        'data_end_row': (total_row - 2) if total_row else ws.max_row - 1,
        'total_row': (total_row - 1) if total_row else None,
        'headers': headers,
        'columns': {'item_name': item_col, 'amount': amount_col, 'code': code_col, 'subject': subject_col},
        'mapping': mapping,
        'names': names,
        'detail_rows': detail_rows,
        'summary': {k: {'code': v['code'], 'count': v['count'], 'amount': round(v['amount'], 2)} for k, v in summary.items()},
        'mapping_conflicts': mapping_conflicts,
    }


def scan_current_detail(base, path):
    wb = load_workbook(path, data_only=True, read_only=False)
    ws = wb[wb.sheetnames[0]]
    selected = None
    for row_idx in range(1, ws.max_row + 1):
        values = [ws.cell(row_idx, col).value for col in range(1, ws.max_column + 1)]
        if base.looks_like_header(values):
            selected = (ws, row_idx)
            break
    if not selected:
        raise RuntimeError('本轮已分类明细中未识别到表头')
    ws, header_row = selected
    headers = [base.normalize_text(ws.cell(header_row, col).value) for col in range(1, ws.max_column + 1)]
    item_col = base.find_column(headers, ('商品名称', '品名', '货物名称', '物料名称'))
    amount_col = base.find_column(headers, ('金额', '金额合计', '实收金额', '合计金额'))
    code_col = base.find_column(headers, ('科目代码',))
    subject_col = base.find_column(headers, ('科目名称',))
    summary = defaultdict(lambda: {'code': '', 'count': 0, 'amount': 0.0})
    mapping = {}
    detail_rows = 0
    for r in range(header_row + 1, ws.max_row + 1):
        values = [ws.cell(r, col).value for col in range(1, ws.max_column + 1)]
        if base.is_total_row(values):
            continue
        name = normalize(values[item_col])
        if not name:
            continue
        detail_rows += 1
        code = normalize(values[code_col])
        subject = normalize(values[subject_col])
        mapping[name] = (code, subject)
        amount = base.parse_amount(values[amount_col])
        summary[subject]['code'] = code
        summary[subject]['count'] += 1
        summary[subject]['amount'] += float(amount or 0)
    return {'sheet': ws.title, 'header_row': header_row, 'headers': headers, 'columns': {'item_name': item_col, 'amount': amount_col, 'code': code_col, 'subject': subject_col}, 'mapping': mapping, 'detail_rows': detail_rows, 'summary': {k: {'code': v['code'], 'count': v['count'], 'amount': round(v['amount'], 2)} for k, v in summary.items()}}


def write_comparison_sheet(summary_path, base, reference_scan, current_scan):
    wb = load_workbook(summary_path)
    if '参考对比' in wb.sheetnames:
        del wb['参考对比']
    ws = wb.create_sheet('参考对比')
    ws.append(['参考分类汇总 vs 本轮分类汇总'])
    ws.merge_cells('A1:H1')
    ws['A1'].font = Font(name='Arial', size=14, bold=True, color='FFFFFF')
    ws['A1'].fill = PatternFill('solid', fgColor='1F4E78')
    ws['A1'].alignment = Alignment(horizontal='center')
    ws.append(['科目代码', '科目名称', '参考明细条数', '本轮明细条数', '条数差异', '参考金额', '本轮金额', '金额差异', '结果'])
    for c in range(1, 10):
        cell = ws.cell(2, c)
        cell.font = Font(name='Arial', bold=True)
        cell.fill = PatternFill('solid', fgColor='D9EAF7')
        cell.alignment = Alignment(horizontal='center', wrap_text=True)
    for code, subject in base.CATEGORIES:
        ref = reference_scan['summary'].get(subject, {'count': 0, 'amount': 0.0, 'code': code})
        cur = current_scan['summary'].get(subject, {'count': 0, 'amount': 0.0, 'code': code})
        row = ws.max_row + 1
        values = [code, subject, ref['count'], cur['count'], cur['count'] - ref['count'], ref['amount'], cur['amount'], round(cur['amount'] - ref['amount'], 2), '一致' if ref['count'] == cur['count'] and round(ref['amount'] - cur['amount'], 2) == 0 else '有差异']
        ws.append(values)
        for col in (6, 7, 8):
            ws.cell(row, col).number_format = '#,##0.00;(#,##0.00);-'
    row = ws.max_row + 1
    ref_count = sum(v['count'] for v in reference_scan['summary'].values())
    cur_count = sum(v['count'] for v in current_scan['summary'].values())
    ref_amount = round(sum(v['amount'] for v in reference_scan['summary'].values()), 2)
    cur_amount = round(sum(v['amount'] for v in current_scan['summary'].values()), 2)
    ws.append(['', '合计', ref_count, cur_count, cur_count - ref_count, ref_amount, cur_amount, round(cur_amount - ref_amount, 2), '一致' if ref_count == cur_count and ref_amount == cur_amount else '有差异'])
    for c in range(1, 10):
        ws.cell(row, c).font = Font(name='Arial', bold=True)
        ws.cell(row, c).fill = PatternFill('solid', fgColor='FFF2CC')
    for c in (6, 7, 8):
        ws.cell(row, c).number_format = '#,##0.00;(#,##0.00);-'
    ws.freeze_panes = 'A3'
    ws.sheet_view.showGridLines = False
    widths = {1: 16, 2: 18, 3: 14, 4: 14, 5: 12, 6: 14, 7: 14, 8: 14, 9: 10}
    for c, width in widths.items():
        ws.column_dimensions[get_column_letter(c)].width = width
    thin = Side(style='hair', color='D9E2F3')
    for row_cells in ws.iter_rows(min_row=3, max_row=ws.max_row, min_col=1, max_col=9):
        for cell in row_cells:
            cell.border = Border(bottom=thin)
            cell.alignment = Alignment(vertical='center')
    wb.save(summary_path)


def inject_html_comparison(html_path, base, reference_scan, current_scan, comparison):
    path = Path(html_path)
    text = path.read_text(encoding='utf-8')
    rows = []
    for code, subject in base.CATEGORIES:
        ref = reference_scan['summary'].get(subject, {'count': 0, 'amount': 0.0})
        cur = current_scan['summary'].get(subject, {'count': 0, 'amount': 0.0})
        count_diff = cur['count'] - ref['count']
        amount_diff = round(cur['amount'] - ref['amount'], 2)
        status = '一致' if count_diff == 0 and amount_diff == 0 else '有差异'
        rows.append(f'<tr><td>{code}</td><td>{html.escape(subject)}</td><td>{ref["count"]:,}</td><td>{cur["count"]:,}</td><td>{count_diff:+,}</td><td>¥{ref["amount"]:,.2f}</td><td>¥{cur["amount"]:,.2f}</td><td>¥{amount_diff:+,.2f}</td><td>{status}</td></tr>')
    ref_total = sum(v['count'] for v in reference_scan['summary'].values())
    cur_total = sum(v['count'] for v in current_scan['summary'].values())
    ref_amount = round(sum(v['amount'] for v in reference_scan['summary'].values()), 2)
    cur_amount = round(sum(v['amount'] for v in current_scan['summary'].values()), 2)
    rows.append(f'<tr><td></td><td><b>合计</b></td><td><b>{ref_total:,}</b></td><td><b>{cur_total:,}</b></td><td><b>{cur_total-ref_total:+,}</b></td><td><b>¥{ref_amount:,.2f}</b></td><td><b>¥{cur_amount:,.2f}</b></td><td><b>¥{cur_amount-ref_amount:+,.2f}</b></td><td><b>{"一致" if ref_total == cur_total and ref_amount == cur_amount else "有差异"}</b></td></tr>')
    new_count = len(comparison['new_names'])
    diff_count = len(comparison['classification_differences'])
    conflict_count = len(reference_scan['mapping_conflicts'])
    panel = f'''<section class="panel"><h2>参考成果一致性对比</h2><div class="notice {'ok' if not new_count and not diff_count and not conflict_count else ''}">参考成果：{html.escape(str(REFERENCE))}。标准化商品名匹配 {len(reference_scan['mapping']):,} 个；新商品 {new_count} 个；分类映射差异 {diff_count} 个；参考成果内部冲突 {conflict_count} 个。逐科目对比如下：</div><div class="scroll"><table><thead><tr><th>科目代码</th><th>科目名称</th><th>参考条数</th><th>本轮条数</th><th>条数差异</th><th>参考金额</th><th>本轮金额</th><th>金额差异</th><th>结果</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div></section>'''
    marker = '<section class="panel"><h2>方法与结构</h2>'
    if marker not in text:
        raise RuntimeError('HTML 中未找到方法说明插入位置')
    text = text.replace(marker, panel + marker, 1)
    text = text.replace('分类方式</div><div>先对 211 个唯一商品名统一归类，再映射回 1,170 条明细；未新增科目。</div>', f'分类方式</div><div>优先沿用参考成果中的相同/标准化商品名分类；本轮匹配 {len(reference_scan["mapping"]):,} 个，新商品 {new_count} 个，再对新商品按固定 7 类规则分类。</div>')
    path.write_text(text, encoding='utf-8')


def main():
    OUTDIR.mkdir(parents=True, exist_ok=True)
    if not BASE_SCRIPT.exists() or not INPUT.exists() or not REFERENCE.exists() or not RULES.exists():
        raise FileNotFoundError('基础脚本、输入文件、参考成果或规则文件缺失')
    base = load_base_module()
    reference_scan = scan_reference(base)
    input_book = __import__('xlrd').open_workbook(str(INPUT), on_demand=True)
    input_sheet = input_book.sheet_by_name(input_book.sheet_names()[0])
    input_names = {normalize(input_sheet.cell(r, 4).value) for r in range(2, input_sheet.nrows) if normalize(input_sheet.cell(r, 4).value)}
    new_names = sorted(input_names - reference_scan['names'])

    old_classifier = base.classify_name

    def classify_with_reference(name):
        key = normalize(name)
        if key in reference_scan['mapping']:
            return reference_scan['mapping'][key]
        code, subject, confidence, review, reason = old_classifier(name)
        return code, subject, confidence, review, f'新商品，按固定 7 类规则分类：{reason}'

    base.INPUT = INPUT
    base.RULES = RULES
    base.OUTDIR = OUTDIR
    base.classify_name = classify_with_reference
    base.main()

    result_path = OUTDIR / '验证结果.json'
    result = json.loads(result_path.read_text(encoding='utf-8'))
    detail_path = Path(result['detail_path'])
    summary_path = Path(result['summary_path'])
    html_path = Path(result['html_path'])
    current_scan = scan_current_detail(base, detail_path)
    classification_differences = []
    for name in sorted(input_names & reference_scan['names']):
        ref = reference_scan['mapping'][name][:2]
        cur = current_scan['mapping'].get(name)
        if cur != ref:
            classification_differences.append({'name': name, 'reference': ref, 'current': cur})

    comparison = {
        'reference_path': str(REFERENCE),
        'reference_sheet': reference_scan['sheet'],
        'reference_detail_rows': reference_scan['detail_rows'],
        'reference_unique_items': len(reference_scan['mapping']),
        'input_unique_items': len(input_names),
        'matched_reference_unique_items': len(input_names & reference_scan['names']),
        'new_names': new_names,
        'classification_differences': classification_differences,
        'reference_mapping_conflicts': reference_scan['mapping_conflicts'],
        'reference_summary': reference_scan['summary'],
        'current_summary': current_scan['summary'],
        'comparison_rows': [],
    }
    for code, subject in base.CATEGORIES:
        ref = reference_scan['summary'].get(subject, {'code': code, 'count': 0, 'amount': 0.0})
        cur = current_scan['summary'].get(subject, {'code': code, 'count': 0, 'amount': 0.0})
        comparison['comparison_rows'].append({'code': code, 'subject': subject, 'reference_count': ref['count'], 'current_count': cur['count'], 'count_diff': cur['count'] - ref['count'], 'reference_amount': ref['amount'], 'current_amount': cur['amount'], 'amount_diff': round(cur['amount'] - ref['amount'], 2), 'status': '一致' if ref['count'] == cur['count'] and round(ref['amount'] - cur['amount'], 2) == 0 else '有差异'})

    comparison_path = OUTDIR / '参考分类对比.json'
    comparison_path.write_text(json.dumps(comparison, ensure_ascii=False, indent=2), encoding='utf-8')
    write_comparison_sheet(summary_path, base, reference_scan, current_scan)
    inject_html_comparison(html_path, base, reference_scan, current_scan, comparison)

    result.update({
        'reference_path': str(REFERENCE),
        'reference_sheet': reference_scan['sheet'],
        'reference_header_row_excel': reference_scan['header_row'] + 1,
        'reference_data_start_row_excel': reference_scan['data_start_row'] + 1,
        'reference_data_end_row_excel': reference_scan['data_end_row'] + 1,
        'reference_total_row_excel': reference_scan['total_row'] + 1 if reference_scan['total_row'] else None,
        'reference_unique_items': len(reference_scan['mapping']),
        'matched_reference_unique_items': len(input_names & reference_scan['names']),
        'new_unique_items': len(new_names),
        'new_item_names': new_names,
        'classification_difference_count': len(classification_differences),
        'classification_differences': classification_differences,
        'reference_mapping_conflicts': reference_scan['mapping_conflicts'],
        'reference_summary': reference_scan['summary'],
        'current_summary': current_scan['summary'],
        'comparison_path': str(comparison_path),
        'reference_external_network_dependencies': False,
    })
    result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    (OUTDIR / '参考结构检查.json').write_text(json.dumps({k: v for k, v in reference_scan.items() if k not in ('mapping', 'names')}, ensure_ascii=False, indent=2, default=str), encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
