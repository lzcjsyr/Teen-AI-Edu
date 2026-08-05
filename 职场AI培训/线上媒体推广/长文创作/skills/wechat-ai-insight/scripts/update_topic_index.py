#!/usr/bin/env python3
"""
导出文章后，自动刷新工作区下的 AI 选题索引。
索引刷新失败时不应阻塞正文导出。
"""

from __future__ import annotations

import json
from pathlib import Path

from find_existing_topics import build_entry, project_candidates, render_markdown


def refresh_topic_index(project_dir: Path) -> tuple[Path, Path, int]:
    workspace_root = project_dir.resolve().parent
    entries = [build_entry(path) for path in project_candidates(workspace_root)]

    md_path = workspace_root / "AI选题索引.md"
    json_path = workspace_root / "AI选题索引.json"

    md_path.write_text(render_markdown(entries, workspace_root), encoding="utf-8")
    json_path.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")
    return md_path, json_path, len(entries)
