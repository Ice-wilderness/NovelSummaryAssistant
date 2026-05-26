import asyncio
import os
from typing import List

import aiofiles
import tiktoken


def _get_token_count(text, model_name="gpt-4"):
    """使用tiktoken计算文本中的token数量。"""
    try:
        encoding = tiktoken.encoding_for_model(model_name)
    except KeyError:
        encoding = tiktoken.get_encoding("cl100k_base")
    return len(encoding.encode(text))


async def read_file_content_robustly_async(filepath):
    """
    【新增】read_file_content_robustly 的异步版本。
    尝试用多种常见中文编码异步读取文本文件。
    """
    try:
        async with aiofiles.open(filepath, 'r', encoding='utf-8') as f:
            return await f.read()
    except UnicodeDecodeError:
        # 如果UTF-8失败，则切换到二进制读取以进行编码检测
        pass
    except Exception as e:
        # 捕获其他可能的IO错误
        print(f"Initial async read with utf-8 failed: {e}")
        pass

    try:
        import chardet
        async with aiofiles.open(filepath, 'rb') as f:
            raw = await f.read()
        detected = chardet.detect(raw)
        enc = detected['encoding']
        if enc:
            try:
                return raw.decode(enc)
            except Exception:
                pass
    except Exception as e:
        print(f"Chardet detection failed: {e}")
        pass

    # 尝试其他常见编码
    for enc in ['gbk', 'gb18030']:
        try:
            async with aiofiles.open(filepath, 'r', encoding=enc) as f:
                return await f.read()
        except Exception:
            continue

    raise UnicodeDecodeError(f"无法使用所有备用编码异步读取文件: {filepath}")


def read_file_content_robustly(filepath):
    """
    尝试用多种常见中文编码读取文本文件，保证最大兼容性。
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except UnicodeDecodeError:
        pass
    try:
        import chardet
        with open(filepath, 'rb') as f:
            raw = f.read()
        detected = chardet.detect(raw)
        enc = detected['encoding']
        if enc:
            try:
                return raw.decode(enc)
            except Exception:
                pass
    except Exception:
        pass
    for enc in ['gbk', 'gb18030']:
        try:
            with open(filepath, 'r', encoding=enc) as f:
                return f.read()
        except Exception:
            continue
    raise UnicodeDecodeError(f"无法识别文件编码: {filepath}")


async def read_files_and_join(files: List[str]) -> str:
    """异步读取多个文件的内容并将它们用分隔符连接起来。"""
    async def _read_file(f):
        if os.path.exists(f):
            try:
                async with aiofiles.open(f, 'r', encoding='utf-8') as handle:
                    return await handle.read()
            except Exception as e:
                print(f"Warning: Could not read file {f}: {e}")
                return ""
        print(f"Warning: File not found and skipped: {f}")
        return ""

    tasks = [_read_file(f) for f in files]
    contents = await asyncio.gather(*tasks)
    return "\n\n---\n\n".join(c for c in contents if c)
