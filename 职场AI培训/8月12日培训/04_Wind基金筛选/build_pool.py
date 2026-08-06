# -*- coding: utf-8 -*-
"""
从 WorkBuddy 会话记录 (jsonl) 中直接提取 Wind search_funds 的 4 次原始返回，
合并 -> 按基金代码去重 -> 原样写入 Excel，sheet 名「01_初始池」。

关键点：MCP 返回已由宿主实时落盘到 ~/.workbuddy/projects/<工作区>/<sessionId>.jsonl，
所以不需要人工转录数据，直接解析该文件，杜绝手抄出错。
"""
import json
import glob
import os
import pandas as pd

SESSION_DIR = os.path.expanduser(
    "~/.workbuddy/projects/Users-dielangli-Desktop-AI培训-职场AI培训-8月12日培训-04_Wind基金筛选"
)
OUT_DIR = "/Users/dielangli/Desktop/AI培训/职场AI培训/8月12日培训/04_Wind基金筛选"
OUT_XLSX = os.path.join(OUT_DIR, "基金初筛池.xlsx")
TOOL_KEY = "search_funds"


def load_events(path):
    events = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return events


def deep_find_tables(node, out):
    """递归查找所有含 columns + rows 的表结构，兼容返回层级变化。"""
    if isinstance(node, dict):
        if isinstance(node.get("columns"), list) and isinstance(node.get("rows"), list):
            out.append(node)
        for v in node.values():
            deep_find_tables(v, out)
    elif isinstance(node, list):
        for v in node:
            deep_find_tables(v, out)
    return out


def coerce_json(payload, _depth=0):
    """
    展开各种包装层级，拿到真正的 JSON 对象。
    实测 function_call_result.output 形如 {"type":"text","text":"<JSON字符串>"}，
    因此必须递归解开内层字符串，否则找不到 columns/rows。
    """
    if _depth > 6:
        return payload
    if isinstance(payload, str):
        try:
            return coerce_json(json.loads(payload), _depth + 1)
        except json.JSONDecodeError:
            return payload
    if isinstance(payload, dict):
        # {"type":"text","text":"..."} 这类单层文本包装
        if isinstance(payload.get("text"), str):
            inner = coerce_json(payload["text"], _depth + 1)
            if isinstance(inner, (dict, list)):
                return inner
        return payload
    if isinstance(payload, list):
        for item in payload:
            if isinstance(item, dict) and isinstance(item.get("text"), str):
                inner = coerce_json(item["text"], _depth + 1)
                if isinstance(inner, (dict, list)):
                    return inner
        return payload
    return payload


def main():
    # 1) 找出所有会话文件，收集 search_funds 的调用与结果（按 callId 配对）
    tables = []          # [(callId, question, columns, rows)]
    seen_callids = set()

    for path in sorted(glob.glob(os.path.join(SESSION_DIR, "*.jsonl")),
                       key=os.path.getmtime, reverse=True):
        events = load_events(path)

        # 先建立 callId -> question 的映射，且只保留 search_funds 的调用
        call_q = {}
        for ev in events:
            if ev.get("type") != "function_call":
                continue
            raw_args = ev.get("arguments")
            args = coerce_json(raw_args) if isinstance(raw_args, str) else raw_args
            blob = json.dumps({"n": ev.get("name"), "a": args}, ensure_ascii=False)
            if TOOL_KEY not in blob:
                continue
            q = ""
            if isinstance(args, dict):
                p = args.get("params") if isinstance(args.get("params"), dict) else args
                q = p.get("question", "") if isinstance(p, dict) else ""
            call_q[ev.get("callId")] = q

        # 再取对应的结果
        for ev in events:
            if ev.get("type") != "function_call_result":
                continue
            cid = ev.get("callId")
            if cid not in call_q or cid in seen_callids:
                continue
            data = coerce_json(ev.get("output"))
            found = deep_find_tables(data, [])
            if not found:
                continue
            seen_callids.add(cid)
            for t in found:
                tables.append((cid, call_q[cid], t["columns"], t["rows"]))

        if len(seen_callids) >= 4:
            break

    if not tables:
        raise SystemExit("未在会话记录中找到 search_funds 的返回结果")

    # 2) 校验列名一致（columns 与 rows 顺序一一对应）
    col_names = [c["name"] if isinstance(c, dict) else str(c) for c in tables[0][2]]
    for _, _, cols, _ in tables:
        names = [c["name"] if isinstance(c, dict) else str(c) for c in cols]
        assert names == col_names, f"列名不一致: {names} vs {col_names}"

    print(f"列名: {col_names}")
    print(f"命中 {len(tables)} 批返回")

    # 3) 合并
    frames = []
    total_raw = 0
    for cid, q, cols, rows in tables:
        df = pd.DataFrame(rows, columns=col_names)
        total_raw += len(df)
        label = q[:40] if q else cid
        print(f"  - [{label}] {len(df)} 条")
        frames.append(df)

    merged = pd.concat(frames, ignore_index=True)

    # 4) 按基金代码去重（保留首次出现）
    code_col = col_names[0]
    before = len(merged)
    merged = merged.drop_duplicates(subset=[code_col], keep="first").reset_index(drop=True)
    print(f"合并 {before} 条 -> 去重后 {len(merged)} 条（删除重复 {before - len(merged)} 条）")

    # 5) 原样写入 Excel
    with pd.ExcelWriter(OUT_XLSX, engine="openpyxl") as w:
        merged.to_excel(w, sheet_name="01_初始池", index=False)

    print(f"已写入: {OUT_XLSX}")
    return merged


if __name__ == "__main__":
    main()
