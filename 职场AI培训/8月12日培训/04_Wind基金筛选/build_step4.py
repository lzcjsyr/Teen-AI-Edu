# -*- coding: utf-8 -*-
import openpyxl
from openpyxl.styles import PatternFill, Font, Alignment
from openpyxl.utils import get_column_letter

XLSX = "/Users/dielangli/Desktop/AI培训/职场AI培训/8月12日培训/04_Wind基金筛选/初始池_基金筛选.xlsx"
DATA_DATE = "2026-08-06"
SOURCE = "Wind金融数据MCP"

wb = openpyxl.load_workbook(XLSX)

# ---- 1. 读取 step3 (03_任职7年) 的经理/任职数据 ----
ws3 = wb["03_任职7年"]
step3 = {}
for r in ws3.iter_rows(min_row=2, values_only=True):
    code = str(r[0])
    step3[code] = {"name": r[1], "manager": r[2], "tenure": r[3]}

# ---- 2. 嵌入 step4 两次查询的近5年最大回撤 ----
perf_rows = [
    ["539002.OF","建信新兴市场优选A",-35.8475],
    ["007355.OF","汇添富科技创新A",-47.0346],
    ["257070.OF","国联安优选行业",-63.83],
    ["002450.OF","平安睿享文娱A",-41.5809],
    ["001480.OF","财通成长优选A",-58.6738],
    ["002910.OF","易方达供给改革",-40.1301],
    ["000940.OF","富国中小盘精选A",-43.2251],
    ["001856.OF","易方达环保主题A",-39.3494],
    ["003304.OF","前海开源沪港深核心资源A",-38.8984],
    ["006373.OF","国富全球科技互联人民币A",-34.5328],
    ["006555.OF","浦银安盛全球智能科技A",-37.7385],
    ["519195.OF","万家品质生活A",-42.1894],
    ["720001.OF","财通价值动量A",-54.6302],
    ["001437.OF","易方达瑞享I",-40.2456],
    ["110029.OF","易方达科讯",-49.1569],
    ["001513.OF","易方达信息产业A",-46.2539],
    ["001672.OF","国寿安保智慧生活A",-45.1467],
    ["007490.OF","南方信息创新A",-56.4081],
    ["006502.OF","财通集成电路产业A",-51.0212],
    ["100039.OF","富国通胀通缩主题A",-43.8754],
    ["006751.OF","富国互联科技A",-49.2059],
    ["007343.OF","嘉实科技创新",-46.4592],
    ["519196.OF","万家新兴蓝筹A",-37.1651],
    ["001323.OF","东吴移动互联A",-39.5277],
    ["003598.OF","华商润丰A",-27.3077],
    ["470009.OF","汇添富民营活力A",-45.6771],
    ["519005.OF","海富通股票",-63.2029],
    ["000628.OF","大成高鑫A",-25.5178],
    ["001564.OF","东方红京东大数据A",-25.8125],
    ["519674.OF","银河创新成长A",-60.8311],
    ["110001.OF","易方达平稳增长",-34.903],
    ["000480.OF","东方红新动力A",-26.9349],
    ["001071.OF","华安媒体互联网A",-43.9284],
    ["166002.OF","中欧新蓝筹A",-33.3065],
    ["001018.OF","易方达新经济",-42.1457],
    ["050009.OF","博时新兴成长",-56.2543],
    ["007280.OF","摩根日本精选A",-19.3474],
    ["110013.OF","易方达科翔",-43.8877],
    ["180031.OF","银华中小盘精选A",-51.9137],
    ["004814.OF","中欧红利优享A",-24.7544],
    ["377240.OF","摩根新兴动力A",-54.5992],
    ["457001.OF","国富亚洲机会A",-41.3271],
    ["700003.OF","平安策略先锋",-49.6284],
    ["001917.OF","招商量化精选A",-25.9001],
    ["002125.OF","广发新兴成长A",-48.7753],
    ["375010.OF","摩根中国优势A",-53.0773],
    ["005698.OF","华夏全球科技先锋A人民币",-46.4234],
    ["118001.OF","易方达亚洲精选",-36.6186],
]
perf = {str(r[0]): {"name": r[1], "maxdd": r[2]} for r in perf_rows}

# ---- 3. 筛选：近5年最大回撤 不低于 -30% （>= -30） ----
THRESHOLD = -30.0
kept = []
missing = []
for code, p in perf.items():
    if code not in step3:
        missing.append(code)
        continue
    if p["maxdd"] >= THRESHOLD:
        kept.append({
            "code": code,
            "name": step3[code]["name"],
            "manager": step3[code]["manager"],
            "tenure": step3[code]["tenure"],
            "maxdd": p["maxdd"],
        })
# 按最大回撤升序（回撤越小越稳排前面）
kept.sort(key=lambda x: x["maxdd"])

print(f"查询总数: {len(perf)}，数据缺失: {len(missing)}，保留: {len(kept)}")
for k in kept:
    print(k["code"], k["name"], k["manager"], k["tenure"], k["maxdd"])

# ---- 4. 新增 sheet 04_回撤30%以内（绿色高亮） ----
if "04_回撤30%以内" in wb.sheetnames:
    del wb["04_回撤30%以内"]
ws4 = wb.create_sheet("04_回撤30%以内")
headers = ["基金代码", "基金名称", "现任基金经理", "任职年限(年)", "近5年最大回撤(%)"]
header_fill = PatternFill(fill_type="solid", fgColor="00B050")  # 深绿
header_font = Font(color="FFFFFF", bold=True)
data_fill = PatternFill(fill_type="solid", fgColor="C6EFCE")     # 浅绿

ws4.append(headers)
for c in range(1, len(headers) + 1):
    cell = ws4.cell(row=1, column=c)
    cell.fill = header_fill
    cell.font = header_font
    cell.alignment = Alignment(horizontal="center")

for k in kept:
    ws4.append([k["code"], k["name"], k["manager"], k["tenure"], round(k["maxdd"], 4)])
for r in range(2, len(kept) + 2):
    for c in range(1, len(headers) + 1):
        cell = ws4.cell(row=r, column=c)
        cell.fill = data_fill
        if c in (1, 4, 5):
            cell.alignment = Alignment(horizontal="center")

# 列宽
widths = [12, 30, 18, 14, 18]
for i, w in enumerate(widths, start=1):
    ws4.column_dimensions[get_column_letter(i)].width = w

# 数据日期 / 来源 注记（绿色页也加）
note_row = len(kept) + 2
ws4.merge_cells(start_row=note_row, start_column=1, end_row=note_row, end_column=len(headers))
ncell = ws4.cell(row=note_row, column=1, value=f"数据日期：{DATA_DATE}；来源：{SOURCE}")
ncell.fill = PatternFill(fill_type="solid", fgColor="00B050")
ncell.font = Font(color="FFFFFF", bold=True)
ncell.alignment = Alignment(horizontal="center")

# ---- 5. 给所有已有 sheet (01/02/03) 末尾追加 数据日期+来源 注记 ----
note_text = f"数据日期：{DATA_DATE}；来源：{SOURCE}"
for shname in ["01_初始池", "02_主动管理型", "03_任职7年"]:
    sh = wb[shname]
    nr = sh.max_row + 2
    ncol = sh.max_column
    sh.merge_cells(start_row=nr, start_column=1, end_row=nr, end_column=ncol)
    nc = sh.cell(row=nr, column=1, value=note_text)
    nc.font = Font(italic=True, color="555555")
    nc.alignment = Alignment(horizontal="left")

wb.save(XLSX)
print("saved ->", XLSX)
