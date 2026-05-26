# logic/custom_summary_logic.py
import os
import traceback
import asyncio
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from logic import utils
from logic.llm_api import call_llm_api


@dataclass
class CustomSummaryResult:
    status: str
    result_summary: str
    output_text: str = ""
    warnings: List[str] = field(default_factory=list)
    failed_source_files: List[Dict[str, Any]] = field(default_factory=list)
    error: Optional[str] = None

    def __bool__(self) -> bool:
        return self.status != "failed"

    def __str__(self) -> str:
        return self.output_text or self.result_summary

    @property
    def data(self) -> Dict[str, Any]:
        return {
            "output_text": self.output_text,
            "failed_source_files": list(self.failed_source_files),
        }


def _custom_success(output_text: str) -> CustomSummaryResult:
    return CustomSummaryResult(
        status="success",
        result_summary=output_text[:200],
        output_text=output_text,
    )


def _custom_failed(message: str, failed_source_files: Optional[List[Dict[str, Any]]] = None) -> CustomSummaryResult:
    return CustomSummaryResult(
        status="failed",
        result_summary="failed",
        failed_source_files=list(failed_source_files or []),
        error=message,
    )


def _custom_partial(output_text: str, failed_source_files: List[Dict[str, Any]]) -> CustomSummaryResult:
    failed_names = [str(item.get("filename") or item.get("source_file") or "") for item in failed_source_files]
    warning = "部分参考材料读取失败，自定义总结仅基于成功读取的材料生成，结果可能不完整。"
    if failed_names:
        warning = f"{warning}失败文件：{', '.join(name for name in failed_names if name)}"
    return CustomSummaryResult(
        status="partial_failed",
        result_summary=output_text[:200],
        output_text=output_text,
        warnings=[warning],
        failed_source_files=list(failed_source_files),
        error=warning,
    )

async def run_custom_summary_process(selected_file_paths, user_prompt, api_config, pause_event, log_callback):
    """
    【重构】处理自定义总结生成的后端逻辑。
    这是一个可以直接被调度的异步协程。

    Args:
        selected_file_paths (list): 用户选择的素材文件的绝对路径列表。
        user_prompt (str): 用户输入的自定义指令。
        api_config (dict): 用于执行任务的API配置。
        pause_event (threading.Event): 用于暂停任务的事件。
        log_callback (function): 用于将日志消息发送回GUI的函数。
    """
    try:
        log_callback("自定义总结任务开始...")
        log_callback(f"选择了 {len(selected_file_paths)} 个素材文件。")

        # 1. 整合素材
        consolidated_content = ""
        failed_source_files = []
        for file_path in selected_file_paths:
            # 暂停检查仍然需要
            await utils.check_pause_async(pause_event)
            
            filename = os.path.basename(file_path)
            log_callback(f"正在读取: {filename}")
            try:
                # 使用异步读取
                content = await utils.read_file_content_robustly_async(file_path)
                consolidated_content += f"--- 素材来源: {filename} ---\n\n{content}\n\n"
            except Exception as e:
                failed_source_files.append(
                    {
                        "filename": filename,
                        "source_file": file_path,
                        "stage": "custom_material_read",
                        "error": str(e),
                    }
                )
                log_callback(f"读取文件失败: {filename}，错误: {e}")
        
        if not consolidated_content:
            message = "错误: 所有选择的文件都无法读取或内容为空，任务中止。"
            log_callback(message)
            return _custom_failed(message, failed_source_files)

        # 2. 构建最终提示词
        final_prompt = (
            "【重要指令：你是一个小说分析助手。请根据用户提供的【参考材料】，严格遵循【用户指令】的要求，生成一份新的分析或总结。不要在回答中包含与用户指令无关的内容或进行不必要的对话。】\n\n"
            "--------------------\n\n"
            f"【用户指令】\n{user_prompt}\n\n"
            "--------------------\n\n"
            f"【参考材料】\n{consolidated_content}"
        )
        
        log_callback("素材整合完毕，正在构建最终提示词并调用API...")
        
        # 3. 调用API
        result, error = await call_llm_api(
            final_prompt,
            api_config,
            log_callback,
            pause_event=pause_event,
            task_info={
                "novel_folder_path": os.path.dirname(selected_file_paths[0]) if selected_file_paths else ".",
                "stage": "custom_summary",
                "source_files": selected_file_paths,
                "source_char_count": len(consolidated_content),
                "progress_text": "自定义总结",
            },
        )

        if error or result is None:
            message = "API调用失败或被取消。"
            log_callback(message)
            return _custom_failed(message, failed_source_files)
        summary_data, duration, char_count = result
        
        success_message = f"自定义总结生成成功！耗时: {duration:.2f}秒，生成字数: {char_count}"
        log_callback(success_message)
        
        if failed_source_files:
            return _custom_partial(summary_data, failed_source_files)
        return _custom_success(summary_data)

    except asyncio.CancelledError:
        log_callback("自定义总结任务被用户取消。")
        raise
    except Exception as e:
        tb_str = traceback.format_exc()
        error_message = f"自定义总结过程中发生严重错误: {e}\n{tb_str}"
        log_callback(error_message)
        return _custom_failed(error_message)
