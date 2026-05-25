from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, Optional

from logic.prompts import (
    USER_FACING_BIG_CHAR_SUBDIR,
    USER_FACING_BIG_PLOT_SUBDIR,
    USER_FACING_SMALL_CHAR_SUBDIR,
    USER_FACING_SMALL_PLOT_SUBDIR,
    USER_FACING_SUPER_CHAR_P1_SUBDIR,
    USER_FACING_SUPER_CHAR_P2_SUBDIR,
    USER_FACING_SUPER_PLOT_P1_SUBDIR,
    USER_FACING_SUPER_PLOT_P2_SUBDIR,
    USER_FACING_ULTIMATE_CHAR_P1_SUBDIR,
    USER_FACING_ULTIMATE_CHAR_P2_SUBDIR,
    USER_FACING_ULTIMATE_PLOT_P1_SUBDIR,
    USER_FACING_ULTIMATE_PLOT_P2_SUBDIR,
)
from logic.trigger_scan.reporting import (
    REPORT_INDEX_FILENAME,
    REPORTS_DIR,
    TRIGGER_SCAN_DIR,
)
from logic.utils import get_chapter_range_from_filename

from .low_state import (
    count_summary_files,
    count_text_files,
    read_json_file,
    summary_file_stems,
)


ARTICLE_STATE_FILENAME = "article_summary_state.json"


def small_summary_chapter_coverage(filename: str) -> int:
    match = re.match(r"^small_batch_(.+)_to_(.+)(?:\.(?:txt|md))?$", filename)
    if not match:
        return 1
    start, _ = get_chapter_range_from_filename(match.group(1))
    end, _ = get_chapter_range_from_filename(match.group(2))
    if start == 99999 or end == 99999 or end < start:
        return 1
    return end - start + 1


def count_small_summary_covered_chapters(cache_dir: Path) -> int:
    plot_stems = summary_file_stems(cache_dir / USER_FACING_SMALL_PLOT_SUBDIR)
    char_stems = summary_file_stems(cache_dir / USER_FACING_SMALL_CHAR_SUBDIR)
    return sum(small_summary_chapter_coverage(stem) for stem in plot_stems & char_stems)


def granularity_migration_disabled_info(summary_batch_size: int = 10) -> Dict[str, Any]:
    return {
        "requires_migration": False,
        "inferred_summary_batch_size": summary_batch_size or 10,
        "grouped_file_count": 0,
        "grouped_files": [],
    }


def count_paragraph_index_files(root: Path) -> int:
    paragraph_dir = root / ".summarizer_cache" / "paragraph_index"
    if not paragraph_dir.exists() or not paragraph_dir.is_dir():
        return 0
    return len([item for item in paragraph_dir.glob("*.json") if item.is_file()])


def scan_trigger_scan_artifacts(root: Path) -> Dict[str, int]:
    scan_dir = root / TRIGGER_SCAN_DIR
    reports_dir = scan_dir / REPORTS_DIR
    report_count = 0
    if reports_dir.exists() and reports_dir.is_dir():
        report_count = len(
            [
                item
                for item in reports_dir.glob("*.json")
                if item.is_file() and item.name != REPORT_INDEX_FILENAME
            ]
        )
        index = read_json_file(reports_dir / REPORT_INDEX_FILENAME)
        if report_count == 0 and isinstance(index.get("items"), list):
            report_count = len(index["items"])

    return {
        "report_count": report_count,
        "paragraph_index_count": count_paragraph_index_files(root),
    }


def project_progress_empty(workflow_type: str) -> Dict[str, Any]:
    return {
        "workflow_type": workflow_type,
        "summary": "暂无进度",
        "percent": 0,
        "stages": [],
    }


def status_from_progress(progress: Dict[str, Any]) -> str:
    percent = int(progress.get("percent") or 0)
    if percent >= 100:
        return "success"
    if percent > 0:
        return "partial"
    return ""


def find_legacy_cache_dir(source_dir: Path, workflow_type: str) -> Optional[Path]:
    direct_cache = source_dir / ".summarizer_cache"
    if direct_cache.exists() and direct_cache.is_dir():
        return direct_cache
    if workflow_type == "article_summary":
        for state_path in source_dir.glob(f"*/.summarizer_cache/{ARTICLE_STATE_FILENAME}"):
            return state_path.parent
    return None


def scan_project_progress(
    workflow_type: str,
    output_directory: str | Path,
    latest_task_status: str = "",
) -> Dict[str, Any]:
    root = Path(output_directory)
    if workflow_type == "novel_summary":
        return scan_novel_progress(root)
    if workflow_type == "article_summary":
        return scan_article_progress(root)
    if workflow_type == "chapter_split":
        return scan_splitter_progress(root)
    if latest_task_status:
        return {
            "workflow_type": workflow_type,
            "summary": f"最近任务：{latest_task_status}",
            "percent": 100 if latest_task_status == "success" else 0,
            "stages": [
                {
                    "label": "最近任务",
                    "completed": 1 if latest_task_status == "success" else 0,
                    "total": 1,
                    "status": latest_task_status,
                }
            ],
        }
    return project_progress_empty(workflow_type)


def scan_novel_progress(root: Path) -> Dict[str, Any]:
    total_chapters = count_text_files(root)
    cache_dir = root / ".summarizer_cache"
    small_completed = min(count_small_summary_covered_chapters(cache_dir), total_chapters)
    big_plot = count_summary_files(cache_dir / USER_FACING_BIG_PLOT_SUBDIR)
    big_char = count_summary_files(cache_dir / USER_FACING_BIG_CHAR_SUBDIR)
    super_completed = sum(
        count_summary_files(cache_dir / subdir)
        for subdir in [
            USER_FACING_SUPER_PLOT_P1_SUBDIR,
            USER_FACING_SUPER_PLOT_P2_SUBDIR,
            USER_FACING_SUPER_CHAR_P1_SUBDIR,
            USER_FACING_SUPER_CHAR_P2_SUBDIR,
        ]
    )
    ultimate_completed = min(
        4,
        sum(
            count_summary_files(cache_dir / subdir)
            for subdir in [
                USER_FACING_ULTIMATE_PLOT_P1_SUBDIR,
                USER_FACING_ULTIMATE_PLOT_P2_SUBDIR,
                USER_FACING_ULTIMATE_CHAR_P1_SUBDIR,
                USER_FACING_ULTIMATE_CHAR_P2_SUBDIR,
            ]
        ),
    )
    trigger_artifacts = scan_trigger_scan_artifacts(root)
    stages = [
        {"label": "小总结", "completed": small_completed, "total": total_chapters},
        {"label": "大总结-剧情", "completed": big_plot, "total": None},
        {"label": "大总结-角色", "completed": big_char, "total": None},
        {"label": "超级总结", "completed": super_completed, "total": None},
        {"label": "终极总结", "completed": ultimate_completed, "total": 4},
        {"label": "雷点报告", "completed": trigger_artifacts["report_count"], "total": None},
        {"label": "段落缓存", "completed": trigger_artifacts["paragraph_index_count"], "total": None},
    ]
    percent = 0
    if total_chapters > 0:
        percent = min(95, int((small_completed / total_chapters) * 35))
    if trigger_artifacts["report_count"] and percent == 0:
        percent = 10
    if ultimate_completed >= 4:
        percent = 100
    elif ultimate_completed:
        percent = max(percent, 85)
    elif super_completed:
        percent = max(percent, 70)
    elif big_plot or big_char:
        percent = max(percent, 50)
    summary = f"小总结 {small_completed}/{total_chapters}"
    if ultimate_completed >= 4:
        summary = "终极总结已完成"
    elif super_completed:
        summary = f"超级总结已完成 {super_completed} 项"
    elif big_plot or big_char:
        summary = f"大总结已完成 剧情 {big_plot} / 角色 {big_char}"
    elif trigger_artifacts["report_count"]:
        summary = f"雷点报告 {trigger_artifacts['report_count']} 份"
    return {
        "workflow_type": "novel_summary",
        "summary": summary,
        "percent": percent,
        "stages": stages,
    }


def scan_article_progress(root: Path) -> Dict[str, Any]:
    total_files = count_text_files(root)
    state = read_json_file(root / ".summarizer_cache" / ARTICLE_STATE_FILENAME)
    processed_sections = state.get("processed_sections", [])
    section_completed = len(processed_sections) if isinstance(processed_sections, list) else 0
    final_completed = bool(state.get("final_summary_complete"))
    percent = 0
    if total_files > 0:
        percent = min(70, int((section_completed / total_files) * 70))
    if final_completed:
        percent = 100
    return {
        "workflow_type": "article_summary",
        "summary": "最终总结已完成" if final_completed else f"段落总结 {section_completed}/{total_files}",
        "percent": percent,
        "stages": [
            {"label": "段落总结", "completed": section_completed, "total": total_files},
            {"label": "最终总结", "completed": 1 if final_completed else 0, "total": 1},
        ],
    }


def scan_splitter_progress(root: Path) -> Dict[str, Any]:
    generated_count = count_text_files(root)
    return {
        "workflow_type": "chapter_split",
        "summary": f"已生成 {generated_count} 个 TXT 文件" if generated_count else "暂无生成文件",
        "percent": 100 if generated_count else 0,
        "stages": [
            {"label": "生成文件", "completed": generated_count, "total": None},
        ],
    }
