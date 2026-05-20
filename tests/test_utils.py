from logic.utils import (
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
