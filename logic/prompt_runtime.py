import json
import os
from typing import Optional

from logic.prompts import DEFAULT_PROMPTS


WORKFLOW_PROMPT_CONFIG_FILENAME = "prompt_workflows.json"


def get_global_prompt_cache_dir():
    """
    获取全局提示词缓存目录的绝对路径。
    """
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(project_root, "prompt_cache")


def get_summarizer_cache_dir(novel_folder_path):
    """
    获取并确保存在用于存放所有总结缓存的根目录。
    """
    cache_dir = os.path.join(novel_folder_path, ".summarizer_cache")
    os.makedirs(cache_dir, exist_ok=True)
    return cache_dir


def load_all_prompts_for_run(cache_dir: Optional[str] = None):
    """
    从缓存目录加载所有提示词，如果文件不存在则使用默认值。
    返回一个包含所有提示词文本的字典。
    """
    cache_dir = get_global_prompt_cache_dir() if cache_dir is None else cache_dir
    loaded_prompts = {}

    def _load(config):
        filename = config['filename']
        default_text = config['default']
        filepath = os.path.join(cache_dir, filename)

        try:
            if os.path.exists(filepath):
                with open(filepath, 'r', encoding='utf-8') as f:
                    return f.read()
        except Exception as e:
            print(f"无法从文件 {filepath} 加载提示词, 将使用默认值。错误: {e}")
        return default_text

    for key, config in DEFAULT_PROMPTS.items():
        loaded_prompts[key] = {'text': _load(config), **config}

    structured_path = os.path.join(cache_dir, WORKFLOW_PROMPT_CONFIG_FILENAME)
    try:
        if os.path.exists(structured_path):
            with open(structured_path, 'r', encoding='utf-8') as f:
                structured_config = json.load(f)
            modules = structured_config.get('modules', [])
            if isinstance(modules, list):
                for module in modules:
                    if isinstance(module, dict) and module.get('id'):
                        loaded_prompts[str(module['id'])] = {
                            'text': str(module.get('content', '')),
                            'filename': str(module.get('id')),
                            'default': str(module.get('default_content', module.get('content', ''))),
                        }
            for workflow in structured_config.get('workflows', []):
                if not isinstance(workflow, dict):
                    continue
                for node in workflow.get('nodes', []):
                    if not isinstance(node, dict):
                        continue
                    prompt_key = str(node.get('prompt_key') or node.get('id') or '')
                    if not prompt_key:
                        continue
                    messages = [
                        {
                            'kind': str(message.get('kind', 'message')),
                            'role': str(message.get('role', 'user')),
                            'content': str(message.get('content', '')),
                            'module_id': str(message.get('module_id', '')),
                        }
                        for message in node.get('messages', [])
                        if isinstance(message, dict)
                    ]
                    if not messages:
                        continue
                    default_messages = [
                        {
                            'kind': str(message.get('kind', 'message')),
                            'role': str(message.get('role', 'user')),
                            'content': str(message.get('content', '')),
                            'module_id': str(message.get('module_id', '')),
                        }
                        for message in node.get('default_messages', [])
                        if isinstance(message, dict)
                    ]
                    loaded_prompts[prompt_key] = {
                        'text': '\n\n'.join(message['content'] for message in messages),
                        'messages': messages,
                        'modules': modules,
                        'filename': str(node.get('filename') or loaded_prompts.get(prompt_key, {}).get('filename', '')),
                        'default': '\n\n'.join(
                            message['content'] for message in default_messages or messages
                        ),
                        'prompt_key': prompt_key,
                        'title': str(node.get('title') or prompt_key),
                    }
    except Exception as e:
        print(f"无法加载结构化提示词配置 {structured_path}, 将使用旧版提示词。错误: {e}")

    return loaded_prompts
