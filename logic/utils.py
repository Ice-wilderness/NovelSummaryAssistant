# logic/utils.py

"""
This module contains various utility functions used by the logic modules.
"""
from logic.api_logging import (
    _get_api_log_lock,
    _redact_log_value,
    cleanup_api_failure_logs,
    get_api_failure_log_dir,
    get_api_log_filepath,
    log_api_failure_to_file,
    log_api_task_to_file,
)
from logic.batching import (
    _distribute_batches_sequentially,
    _distribute_chapters_sequentially,
    build_small_summary_batches,
    small_summary_batch_task_name,
)
from logic.chapter_naming import (
    chinese_to_arabic,
    clean_filename_for_splitting,
    extract_numbers_from_filename,
    get_big_summary_sort_key,
    get_chapter_range_from_filename,
    get_super_ultimate_summary_sort_key,
    natural_sort_key,
    sanitize_api_name,
    sanitize_filename,
)
from logic.chapter_writing import (
    _match_group,
    find_and_sort_chapter_files,
    get_final_summary_path,
    process_chapters_with_regex,
    write_chapters_to_file_numeric,
)
from logic.summary_outputs import (
    find_existing_summary_output_file,
    is_summary_output_filename,
    normalize_summary_output_format,
    summary_output_filename,
    summary_output_path,
    summary_output_peer_exists,
)
from logic.file_io import (
    _get_token_count,
    read_file_content_robustly,
    read_file_content_robustly_async,
    read_files_and_join,
)
from logic.progress_events import (
    StageProgressTracker,
    check_pause_async,
    emit_stage_progress,
    log_message,
)
from logic.prompt_runtime import (
    get_global_prompt_cache_dir,
    get_summarizer_cache_dir,
    load_all_prompts_for_run as _load_all_prompts_for_run,
)
from logic.text_extraction import (
    extract_character_content,
    extract_character_info_from_summary,
    extract_summary_content,
    extract_tag_content,
)

# --- Logging and Thread Control ---

def load_all_prompts_for_run():
    return _load_all_prompts_for_run(cache_dir=get_global_prompt_cache_dir())



