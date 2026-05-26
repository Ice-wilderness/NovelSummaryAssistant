import os
from typing import List, Tuple


def _distribute_chapters_sequentially(chapters, apis):
    """按顺序将连续的章节块分配给API。"""
    if not apis:
        return {}
    if not chapters:
        return {api['id']: [] for api in apis}

    api_ids = [api['id'] for api in apis]
    distribution = {api_id: [] for api_id in api_ids}

    num_chapters = len(chapters)
    num_apis = len(api_ids)

    base_chunk_size = num_chapters // num_apis
    remainder = num_chapters % num_apis

    start_index = 0
    for i in range(num_apis):
        chunk_size = base_chunk_size + (1 if i < remainder else 0)
        end_index = start_index + chunk_size

        api_id = api_ids[i]
        distribution[api_id] = chapters[start_index:end_index]

        start_index = end_index

    return distribution


def _distribute_batches_sequentially(batches, apis):
    """按顺序将连续的批次块分配给API。"""
    if not apis:
        return {}
    if not batches:
        return {api['id']: [] for api in apis}

    api_ids = [api['id'] for api in apis]
    distribution = {api_id: [] for api_id in api_ids}

    num_batches = len(batches)
    num_apis = len(api_ids)

    base_chunk_size = num_batches // num_apis
    remainder = num_batches % num_apis

    start_index = 0
    for i in range(num_apis):
        chunk_size = base_chunk_size + (1 if i < remainder else 0)
        end_index = start_index + chunk_size

        api_id = api_ids[i]
        distribution[api_id] = batches[start_index:end_index]

        start_index = end_index

    return distribution


def small_summary_batch_task_name(chapter_paths: List[str]) -> str:
    if not chapter_paths:
        return ""
    if len(chapter_paths) == 1:
        return os.path.basename(chapter_paths[0])
    first_name = os.path.splitext(os.path.basename(chapter_paths[0]))[0]
    last_name = os.path.splitext(os.path.basename(chapter_paths[-1]))[0]
    return f"small_batch_{first_name}_to_{last_name}.txt"


def build_small_summary_batches(chapter_paths: List[str], batch_size: int = 1) -> List[Tuple[str, List[str]]]:
    try:
        safe_batch_size = max(int(batch_size or 1), 1)
    except (TypeError, ValueError):
        safe_batch_size = 1
    batches = []
    for index in range(0, len(chapter_paths), safe_batch_size):
        batch_paths = chapter_paths[index:index + safe_batch_size]
        task_name = small_summary_batch_task_name(batch_paths)
        if task_name:
            batches.append((task_name, batch_paths))
    return batches
