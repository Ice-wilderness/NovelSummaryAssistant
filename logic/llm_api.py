"""
This module handles all direct interactions with the Large Language Model (LLM) APIs.
"""
import time
import httpx
import asyncio
import traceback
import json
import re
from typing import Dict, Callable
from logic.utils import log_message, check_pause_async, log_api_task_to_file

# --- 自定义异常 ---
class PromptFormattingError(KeyError):
    """当提示词模板中的变量缺失时引发的自定义异常。"""
    pass

class APIPermanentError(Exception):
    """当API调用在所有重试后都失败时引发的自定义异常。"""
    pass

# --- Constants ---
API_PERMANENT_FAILURE_PREFIX = "ERROR_API_CALL_FAILED: "

HTTP_STATUS_DESCRIPTIONS = {
    400: "Bad Request",
    401: "Unauthorized",
    403: "Forbidden",
    404: "Not Found",
    429: "Too Many Requests",
    500: "Internal Server Error",
    502: "Bad Gateway",
    503: "Service Unavailable",
    504: "Gateway Timeout",
}


async def fetch_available_models(api_url_base, api_key, api_id_for_log="FETCH_MODELS", log_callback=None):
    """
    获取指定API可用的模型列表。
    """
    def _log(message, status=None):
        if log_callback:
            log_callback(message, status=status)
        else:
            print(f"[{api_id_for_log}] [{status or 'INFO'}] {message}")

    api_url = f"{api_url_base.rstrip('/')}/models"
    headers = {"Authorization": f"Bearer {api_key}"}
    try:
        _log(f"正在从 {api_url} 获取模型列表...", status='START')
        async with httpx.AsyncClient() as client:
            response = await client.get(api_url, headers=headers, timeout=20)
        response.raise_for_status()
        models_data = response.json()
        
        raw_model_ids = [model.get('id') for model in models_data.get('data', [])]
        string_model_ids = [mid for mid in raw_model_ids if isinstance(mid, str)]
        model_ids = sorted(
            string_model_ids, 
            key=lambda x: (
                'pro' not in x.lower(), 
                '4' not in x and '2.5' not in x,
                x
            )
        )
        
        _log(f"成功找到 {len(model_ids)} 个模型。", status='SUCCESS')
        return model_ids, None
    except Exception as e:
        error_message = f"获取模型列表失败: {e}"
        _log(error_message, status='FAIL')
        return None, error_message

async def call_llm_api(
    final_prompt_text, 
    api_config_dict, 
    log_callback, 
    pause_event=None,
    task_info=None # 【修改】使用一个字典来传递任务元数据
):
    """
    一个健壮的函数，用于调用LLM API，包含完整的日志、错误处理和重试逻辑。
    - task_info (dict): (可选) 包含用于文件日志记录的元数据。
        - novel_folder_path: 必需，用于定位日志文件
        - stage: e.g., 'small_summary'
        - source_file / source_files: e.g., '/path/to/chapter.txt'
    """
    # 【修复】优先使用 'api_key_name' (例如 'api1'), 其次是 'display_name', 最后是 'id'
    api_display_name = api_config_dict.get('api_key_name') or api_config_dict.get('display_name') or 'UnknownAPI'
    api_id_for_task_log = api_config_dict.get('id', 'UnknownAPI_ID') # 任务日志文件仍使用 UUID 保证唯一性
    
    api_url = f"{api_config_dict['url'].rstrip('/')}/chat/completions"
    headers = {"Authorization": f"Bearer {api_config_dict['key']}"}
    model = api_config_dict.get('model', 'gpt-4')
    
    # --- 【增强】健壮地读取超时和重试配置 ---
    try:
        timeout = int(api_config_dict.get('timeout', 300))
    except (ValueError, TypeError):
        timeout = 300 # 如果配置值无效，使用默认值
        
    try:
        max_retries = int(api_config_dict.get('max_retries', 3))
    except (ValueError, TypeError):
        max_retries = 3 # 如果配置值无效，使用默认值

    GENERAL_RETRY_DELAYS = [5, 15, 30, 60, 120]
    RATE_LIMIT_RETRY_DELAYS = [10, 30, 60, 120, 300]

    # 【修复】将HTML校验正则的编译提前，避免在循环中重复编译
    # 【增强】更通用的HTML/XML开始标签检测，能捕获如 <!-- 或 <div> 开头的内容
    html_check_pattern = re.compile(r'^\s*<', re.IGNORECASE)

    # 【新增】定义需要过滤的特定错误短语列表，这些短语会无视响应时间，直接触发重试
    specific_error_phrases = [
        "所有API密钥均请求失败",
        "似乎发生了一些问题导致本次返回的内容为空",
        "本条消息不消耗次数哦", # 来自小忆API的另一个常见提示
        "This key is associated with a deactivated account", # 来自OpenRouter的特定错误
        "空响应次数达到上限",
        "请修改输入提示词",
        "暂无返回"
    ]

    prompt_char_count = len(final_prompt_text)
    
    use_stream = api_config_dict.get('stream', False)
    json_payload = {
        "model": model,
        "messages": [{"role": "user", "content": final_prompt_text}],
        "temperature": api_config_dict.get('temperature', 0.7),
        "stream": use_stream,
        "max_tokens": api_config_dict.get('max_tokens', 4096)
    }

    # 【新增】如果提供了 task_info，则创建日志记录任务的快捷方式
    async def _log_task_to_file(status, details=None):
        if task_info and task_info.get('novel_folder_path'):
            log_data = task_info.copy()
            log_data.update({
                'timestamp': time.time(),
                'status': status,
                'api_id': api_id_for_task_log, # 文件日志使用UUID
                'api_display_name': api_display_name, # GUI日志使用友好名称
                'model_used': model
            })
            if details:
                log_data.update(details)
            await log_api_task_to_file(task_info['novel_folder_path'], api_id_for_task_log, log_data)

    def _log(message, status=None, is_progress=False, progress_override=None, tb_info=None):
        # 从 task_info 中获取 progress_text
        progress_text = task_info.get('progress_text') if task_info else None
        effective_progress_text = progress_override if progress_override is not None else progress_text
        # 【修复】现在总是使用 api_display_name 作为日志记录的主要标识符
        log_message(log_callback, message, api_display_name, is_progress, effective_progress_text, api_display_name, traceback_info=tb_info, status=status)

    # 【修复】日志记录优先使用传入的源文件字数，如果未提供，再用提示词字数
    display_char_count = task_info.get('source_char_count', len(final_prompt_text)) if task_info else len(final_prompt_text)
    _log(f"发送请求到模型: {model} (源字数: {display_char_count})", status='START', is_progress=True)

    # --- 内部辅助函数，封装了实际的API请求逻辑 ---
    async def _execute_request():
        start_time = time.time()
        summary = "" # 在外部作用域初始化summary

        async with httpx.AsyncClient(timeout=timeout) as client:
            if use_stream:
                async with client.stream("POST", api_url, headers=headers, json=json_payload) as response:
                    response.raise_for_status()
                    
                    full_content = []
                    async for line in response.aiter_lines():
                        await check_pause_async(pause_event)
                        if line.startswith('data: '):
                            json_str = line[len('data: '):].strip()
                            if json_str == '[DONE]':
                                break
                            try:
                                chunk = json.loads(json_str)
                                delta = chunk.get('choices', [{}])[0].get('delta', {})
                                content_piece = delta.get('content')
                                if content_piece:
                                    full_content.append(content_piece)
                            except json.JSONDecodeError:
                                _log(f"无法解析流中的JSON数据块: {json_str}", status='WARN')
                                continue
                    summary = "".join(full_content).strip()
            else:
                response = await client.post(api_url, headers=headers, json=json_payload)
                response.raise_for_status()
                
                json_data = response.json()
                # --- 【修复】优先检查并处理顶层的error对象 ---
                if 'error' in json_data and json_data['error']:
                    error_obj = json_data['error']
                    # 提取错误信息，兼容不同API的返回格式
                    error_message = error_obj.get('message', str(error_obj))
                    # 抛出异常，以便外部的重试循环可以捕获到具体的错误原因
                    raise ValueError(f"API返回错误: {error_message}")

                choice = json_data.get("choices", [{}])[0]
                finish_reason = choice.get("finish_reason", "")
                if "content_filter" in finish_reason.lower():
                    raise ValueError(f"内容被API的安全策略阻止 (reason: {finish_reason})")
                if not choice.get("message"):
                    raise ValueError("API响应中缺少'message'字段")
                summary = choice["message"].get("content", "").strip()

        # --- 【增强】统一的、多层次的验证与成功返回逻辑 ---
        
        # 1. 检查是否为空
        if not summary:
            raise ValueError("API返回了空内容，将进行重试")

        # 2. 检查是否为HTML/XML内容
        if html_check_pattern.match(summary):
            error_detail = f"API返回了HTML/XML格式内容，可能为错误页面。内容预览: {summary[:150].strip()}"
            raise ValueError(error_detail)

        # 3. 检查是否包含已知的特定错误短语 (无论响应时间长短)
        for phrase in specific_error_phrases:
            if phrase in summary:
                error_detail = f"API返回了已知的错误消息: '{phrase[:30]}...'。将进行重试"
                raise ValueError(error_detail)
        
        duration = time.time() - start_time
        
        # 4. 对快速返回的响应进行额外的通用关键词检查
        if duration < 5.0: # 如果耗时低于5秒
            # 定义常见的错误指示词
            error_keywords = ['error', 'fail', 'upstream', 'timeout', 'invalid', 'exception', 'traceback', '服务', '错误', '失败', '超时']
            summary_lower = summary.lower()
            if any(keyword in summary_lower for keyword in error_keywords):
                error_detail = f"API在 {duration:.1f}s 内快速返回，且内容疑似错误。内容预览: {summary[:150].strip()}"
                # 同样抛出ValueError，以便触发重试
                raise ValueError(error_detail)

        # 5. 如果所有验证通过，则计算耗时并返回成功结果
        summary_char_count = len(summary)
        _log(f"处理完成 (耗时: {duration:.1f}s, 生成: {summary_char_count}字)", status='SUCCESS', is_progress=True, progress_override="处理完成")
        return (summary, duration, summary_char_count), None

    # --- 重试循环 ---
    for attempt in range(max_retries):
        await check_pause_async(pause_event)
        
        try:
            # 直接 await 请求，不再需要竞速逻辑
            # 如果任务被外部取消，CancelledError 会在这里被引发
            result, error = await _execute_request()
            
            # 如果成功，记录日志并返回
            if not error:
                 await _log_task_to_file("success", {
                    'duration_seconds': result[1],
                    'output_char_count': result[2]
                })
                 return result, None
        
        except asyncio.CancelledError:
            # 如果任务被取消，记录日志并重新引发，以终止整个流程
            _log("API 调用被用户取消。", status='WARN')
            raise # Re-raise CancelledError

        except Exception as e:
            # 处理其他类型的错误（网络问题，API返回错误等）
            tb_info = traceback.format_exc()
            error_message = f"API 调用失败 (尝试 {attempt + 1}/{max_retries}): {e}"
            _log(error_message, status='WARN', tb_info=tb_info)

            # 记录失败日志到文件
            await _log_task_to_file("fail", {'error_message': str(e)})

            # 判断是否是速率限制错误
            is_rate_limit = isinstance(e, httpx.HTTPStatusError) and e.response.status_code == 429
            delays = RATE_LIMIT_RETRY_DELAYS if is_rate_limit else GENERAL_RETRY_DELAYS

            if attempt < max_retries - 1:
                delay = delays[min(attempt, len(delays) - 1)]
                _log(f"将在 {delay} 秒后重试...", status='INFO')
                await asyncio.sleep(delay)
            else:
                # 所有重试都失败后，返回一个永久性错误
                final_error_message = f"{API_PERMANENT_FAILURE_PREFIX}API call to {api_display_name} failed after {max_retries} attempts."
                _log(final_error_message, status='FAIL')
                return None, APIPermanentError(final_error_message)

async def get_llm_summary_with_config(
    api_config: Dict,
    prompt_config: Dict,
    format_args: Dict,
    log_callback: Callable,
    **kwargs
):
    """
    一个高层封装，用于格式化提示词并调用LLM API。
    - format_args: 用于格式化提示词模板的核心变量。
    - **kwargs: 其他用于格式化提示词的动态变量，如各种字数限制。
    """
    prompt_text = prompt_config.get('text', '')
    
    try:
        # 合并所有可用于格式化的参数
        all_format_args = {**format_args, **kwargs}
        # 使用 .format() 来填充提示词
        final_prompt = prompt_text.format(**all_format_args)
    except KeyError as e:
        # 抛出自定义异常，包含更详细的上下文
        raise PromptFormattingError(
            f"格式化提示词 '{prompt_config.get('filename', 'N/A')}' 时出错。"
            f"模板需要变量 '{e.args[0]}', 但该变量未在参数中提供。"
            f"提供的所有参数: {list(all_format_args.keys())}"
        ) from e

    # 调用核心API函数
    result, error = await call_llm_api(final_prompt, api_config, log_callback)

    if error:
        # 将错误信息包装在自定义异常中并重新引发
        raise APIPermanentError(f"API调用最终失败: {error}")
        
    summary, _, _ = result
    return summary 
