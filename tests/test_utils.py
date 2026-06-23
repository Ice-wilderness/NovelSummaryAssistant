from logic.utils import (
    StageProgressTracker,
    extract_character_info_from_summary,
    extract_summary_content,
)


def test_extract_summary_content_returns_inner_text_without_tags():
    text = "<summary_content>剧情内容</summary_content><character_content>角色内容</character_content>"

    assert extract_summary_content(text) == "剧情内容"


def test_extract_summary_content_without_closing_tag_stops_before_character_tag():
    text = "<summary_content>剧情内容\n<character_content>角色内容</character_content>"

    assert extract_summary_content(text) == "剧情内容"


def test_extract_character_info_supports_legacy_asymmetric_tags():
    text = "前言<character_info_block_start>旧角色内容</character_info_block_end>尾声"

    assert extract_character_info_from_summary(text) == "旧角色内容"


def test_stage_progress_tracker_ignores_unknown_stage_ids():
    tracker = StageProgressTracker()
    tracker.init_stages(
        [
            {"id": "small_and_big_summary", "label": "小总结+大总结", "total": 3},
            {"id": "super_summary", "label": "自动超级总结", "total": None},
            {"id": "ultimate_summary", "label": "终极总结", "total": 4},
        ]
    )

    tracker.advance_stage("missing_stage")

    assert [stage["status"] for stage in tracker.stages] == ["running", "pending", "pending"]


def test_stage_progress_tracker_aggregates_fine_flow_small_and_big_updates():
    tracker = StageProgressTracker()
    tracker.init_stages(
        [
            {"id": "small_and_big_summary", "label": "小总结+大总结", "total": 3},
            {"id": "super_summary", "label": "自动超级总结", "total": None},
            {"id": "ultimate_summary", "label": "终极总结", "total": 4},
        ]
    )

    tracker.increment("small_summary")
    tracker.increment("big_summary_plot")
    tracker.increment("big_summary_char")

    assert tracker.stages[0]["completed"] == 3


def test_stage_progress_tracker_keeps_incomplete_previous_stage_running():
    tracker = StageProgressTracker()
    tracker.init_stages(
        [
            {"id": "big_summary_char", "label": "大总结-角色", "completed": 6, "total": 8},
            {"id": "super_summary_plot_p1", "label": "超级剧情总结P1", "completed": 0, "total": 2},
        ]
    )

    tracker.advance_stage("super_summary_plot_p1")

    assert tracker.stages[0]["status"] == "running"
    assert tracker.stages[0]["completed"] == 6


def test_stage_progress_tracker_preserves_initial_completed_count():
    tracker = StageProgressTracker()
    tracker.init_stages(
        [
            {"id": "small_summary", "label": "小总结", "completed": 1, "total": 2},
        ]
    )

    assert tracker.stages[0]["completed"] == 1
