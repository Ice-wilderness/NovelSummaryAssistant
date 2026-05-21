# logic/state_manager.py

import os
import json
import time
from typing import Dict, Any, Callable, List, Optional, Tuple
import uuid

from config import TASK_ID_FILENAME
from . import utils
from logic.prompts import (
    USER_FACING_BIG_CHAR_SUBDIR,
    USER_FACING_BIG_PLOT_SUBDIR,
    USER_FACING_SMALL_CHAR_SUBDIR,
    USER_FACING_SMALL_PLOT_SUBDIR,
)
from logic.utils import (
    find_and_sort_chapter_files,
    get_summarizer_cache_dir,
    natural_sort_key
)


class StateManager:
    """
    管理单个总结任务的状态，包括跟踪每个章节的进度。
    """

    def __init__(self, novel_folder_path: str):
        self.novel_folder_path = novel_folder_path
        self.cache_dir = get_summarizer_cache_dir(self.novel_folder_path)
        os.makedirs(self.cache_dir, exist_ok=True)

        self.task_id = self._get_or_create_task_id()
        self.state_filepath = os.path.join(self.cache_dir, f"state_{self.task_id}.json")
        
        self.chapters, self.initialization_log = self._initialize_chapters()
        
        self.state = self._load_state()

    def _get_or_create_task_id(self):
        task_id_filepath = os.path.join(self.cache_dir, TASK_ID_FILENAME)
        try:
            if os.path.exists(task_id_filepath):
                with open(task_id_filepath, 'r', encoding='utf-8') as f:
                    task_id = f.read().strip()
                    if task_id:
                        return task_id
            
            task_id = str(uuid.uuid4())
            with open(task_id_filepath, 'w', encoding='utf-8') as f:
                f.write(task_id)
            return task_id
        except Exception as e:
            print(f"在 _get_or_create_task_id 中发生错误: {e}")
            return str(uuid.uuid4())

    def _initialize_chapters(self):
        log_messages = []
        def temp_log_callback(msg, level="INFO"):
            log_messages.append(f"[{level}] {msg}")

        chapters = find_and_sort_chapter_files(self.novel_folder_path, temp_log_callback)
        log_output = "\n".join(log_messages)
        return chapters, log_output
        
    def get_initialization_log(self):
        return self.initialization_log

    def _load_state(self):
        if not os.path.exists(self.state_filepath):
            return {}
        try:
            with open(self.state_filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {}

    def _small_summary_outputs_exist(self, task_name: str) -> bool:
        plot_path = os.path.join(self.cache_dir, USER_FACING_SMALL_PLOT_SUBDIR, task_name)
        char_path = os.path.join(self.cache_dir, USER_FACING_SMALL_CHAR_SUBDIR, task_name)
        return os.path.isfile(plot_path) and os.path.isfile(char_path)

    def _big_summary_output_exists(self, task_name: str, sub_stage_name: str) -> bool:
        subdir = USER_FACING_BIG_PLOT_SUBDIR if sub_stage_name == 'plot' else USER_FACING_BIG_CHAR_SUBDIR
        output_dir = os.path.join(self.cache_dir, subdir)
        if not os.path.isdir(output_dir):
            return False
        prefix = f"{task_name}_"
        return any(
            filename.startswith(prefix) and filename.endswith(".txt")
            for filename in os.listdir(output_dir)
        )

    def _save_state(self):
        temp_filepath = self.state_filepath + ".tmp"
        try:
            with open(temp_filepath, 'w', encoding='utf-8') as f:
                json.dump(self.state, f, ensure_ascii=False, indent=4)
            
            if os.path.exists(self.state_filepath):
                os.remove(self.state_filepath)
            os.rename(temp_filepath, self.state_filepath)
        except Exception as e:
            print(f"保存状态文件失败: {e}")


    def get_pending_small_summary_chapters(
        self,
        chapter_paths: List[str],
        batch_size: int = 1,
    ) -> List[str]:
        pending_chapters = []
        for task_name, batch_paths in utils.build_small_summary_batches(chapter_paths, batch_size):
            if not self.is_task_complete(task_name, 'small_summary'):
                pending_chapters.extend(batch_paths)
        return pending_chapters

    def get_pending_tasks(self, stage_name: str, sub_stage_name: Optional[str] = None, batch_size: Optional[int] = None, api_id: Optional[str] = None) -> List[Any]:
        effective_batch_size = batch_size if batch_size is not None else (1 if stage_name == 'small_summary' else 5)
        if stage_name == 'small_summary':
            return self.get_pending_small_summary_chapters(
                self.chapters,
                batch_size=effective_batch_size,
            )
            
        elif stage_name == 'big_summary':
            if not api_id:
                raise ValueError("big_summary stage requires an api_id to be specified.")

            # 获取所有已完成的小结任务的 *文件名*
            all_completed_small_summaries = self.get_all_completed_tasks('small_summary')
            
            #  根据 api_id 筛选出专属的已完成小结
            assignments = self.state.get('small_summary_assignment', {})
            api_specific_summaries = [
                task_name for task_name in all_completed_small_summaries
                if assignments.get(task_name) == api_id
            ]

            pending_batches = []
            if not sub_stage_name:
                raise ValueError("big_summary stage requires a sub_stage_name ('plot' or 'char').")

            # 按数字和文本的自然顺序对文件名进行排序
            sorted_summaries = sorted(api_specific_summaries, key=natural_sort_key)

            for i in range(0, len(sorted_summaries), effective_batch_size):
                batch_filenames = sorted_summaries[i:i+effective_batch_size]
                
                # 创建一个更具描述性的批处理名称
                if not batch_filenames: continue
                first_name = os.path.splitext(batch_filenames[0])[0]
                last_name = os.path.splitext(batch_filenames[-1])[0]
                batch_name = f"big_batch_{first_name}_to_{last_name}"

                if not self.is_task_complete(batch_name, 'big_summary', sub_stage_name):
                    # 从正确的缓存子目录构建小结文件的完整路径
                    source_subdir = USER_FACING_SMALL_PLOT_SUBDIR if sub_stage_name == 'plot' else USER_FACING_SMALL_CHAR_SUBDIR
                    source_dir_path = os.path.join(self.cache_dir, source_subdir)
                    
                    batch_fullpaths = [
                        os.path.join(source_dir_path, fname) for fname in batch_filenames
                    ]
                    pending_batches.append((batch_name, batch_fullpaths))
            return pending_batches

        elif stage_name == 'super_summary':
            # 为超级总结实现类似的逻辑
            completed_big_plot = self.get_all_completed_tasks('big_summary', 'plot')
            completed_big_char = self.get_all_completed_tasks('big_summary', 'char')
            
            # 只有当剧情和角色大总结的数量相同时，才认为这些批次是"完整"的
            completed_big_batches = list(set(completed_big_plot) & set(completed_big_char))
            sorted_batches = sorted(completed_big_batches, key=natural_sort_key)

            pending_super_batches = []
            if not sub_stage_name:
                raise ValueError("super_summary stage requires a sub_stage_name ('plot' or 'char').")

            for i in range(0, len(sorted_batches), effective_batch_size):
                batch_names = sorted_batches[i:i+effective_batch_size]
                if not batch_names: continue
                
                first_name = batch_names[0]
                last_name = batch_names[-1]
                super_batch_name = f"super_batch_{first_name}_to_{last_name}"

                if not self.is_task_complete(super_batch_name, 'super_summary', sub_stage_name):
                     # 对于超级总结，输入是之前阶段的产出批次名
                    pending_super_batches.append((super_batch_name, batch_names))
            return pending_super_batches

        elif stage_name == 'ultimate_summary':
            # 检查是否所有超级总结都已完成
            # 只需要检查 plot 或 char 中的一个
            all_super_batches = self.get_all_completed_tasks('super_summary', 'plot')
            if not all_super_batches:
                return [] # 还没有任何超级总结完成

            # 检查是否有待处理的超级总结任务
            if self.get_pending_tasks('super_summary', 'plot', effective_batch_size):
                return [] # 还有未完成的超级总结

            # 检查终极总结是否已经完成
            if self.is_task_complete('ultimate_summary_task', 'ultimate_summary'):
                return []

            # 所有条件满足，创建终极总结任务
            # 内容是所有已完成的超级总结批次的名称
            return [('ultimate_summary_task', all_super_batches)]
        
        return []

    def is_task_complete(self, task_name: str, stage_name: str, sub_stage_name: Optional[str] = None) -> bool:
        task_key = task_name
        if sub_stage_name:
            task_key = f"{task_name}_{sub_stage_name}"

        if not self.state.get(stage_name, {}).get(task_key, False):
            return False
        if stage_name == 'small_summary' and not sub_stage_name:
            return self._small_summary_outputs_exist(task_name)
        if stage_name == 'big_summary' and sub_stage_name:
            return self._big_summary_output_exists(task_name, sub_stage_name)
        return True

    def mark_task_complete(self, task_name: str, stage_name: str, sub_stage_name: Optional[str] = None, api_id: Optional[str] = None):
        if stage_name not in self.state:
            self.state[stage_name] = {}
            
        task_key = task_name
        if sub_stage_name:
            task_key = f"{task_name}_{sub_stage_name}"

        self.state[stage_name][task_key] = True

        # 如果是小结任务，则记录是哪个API完成的
        if stage_name == 'small_summary' and api_id:
            if 'small_summary_assignment' not in self.state:
                self.state['small_summary_assignment'] = {}
            self.state['small_summary_assignment'][task_name] = api_id
        
        self._save_state()

    def reset_state(self):
        if os.path.exists(self.state_filepath):
            try:
                os.remove(self.state_filepath)
                self.state = {}
                # 确保在重置时也清空分配状态
                if 'small_summary_assignment' in self.state:
                    del self.state['small_summary_assignment']
                return True
            except OSError as e:
                print(f"Error resetting state file: {e}")
                return False
        return True

    def get_all_completed_tasks(self, stage_name: str, sub_stage_name: Optional[str] = None) -> List[str]:
        if stage_name not in self.state:
            return []
        
        completed_tasks = []
        for task_key, is_complete in self.state[stage_name].items():
            if is_complete:
                if sub_stage_name:
                    if task_key.endswith(f"_{sub_stage_name}"):
                        task_name = task_key.replace(f"_{sub_stage_name}", "")
                        if self.is_task_complete(task_name, stage_name, sub_stage_name):
                            completed_tasks.append(task_name)
                else:
                    if self.is_task_complete(task_key, stage_name):
                        completed_tasks.append(task_key)

        return completed_tasks 

    def get_completed_big_summary_batches_for_api(
        self,
        api_id: str,
        sub_stage_name: str,
        batch_size: int,
    ) -> List[str]:
        assignments = self.state.get('small_summary_assignment', {})
        completed_small_summaries = self.get_all_completed_tasks('small_summary')
        api_specific_summaries = [
            task_name for task_name in completed_small_summaries
            if assignments.get(task_name) == api_id
        ]
        sorted_summaries = sorted(api_specific_summaries, key=natural_sort_key)
        completed_batches = []

        for index in range(0, len(sorted_summaries), batch_size):
            batch_filenames = sorted_summaries[index:index + batch_size]
            if not batch_filenames:
                continue
            first_name = os.path.splitext(batch_filenames[0])[0]
            last_name = os.path.splitext(batch_filenames[-1])[0]
            batch_name = f"big_batch_{first_name}_to_{last_name}"
            if self.is_task_complete(batch_name, 'big_summary', sub_stage_name):
                completed_batches.append(batch_name)

        return completed_batches

    def is_ultimate_summary_stage_complete(self) -> bool:
        """检查终极总结的所有部分是否都已完成。"""
        tasks_to_check = [
            "ultimate_summary_plot_p1",
            "ultimate_summary_plot_p2",
            "ultimate_summary_char_p1",
            "ultimate_summary_char_p2"
        ]

        all_done = all(self.is_task_complete(task, 'ultimate_summary') for task in tasks_to_check)
        return all_done 
