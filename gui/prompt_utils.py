# gui/prompt_utils.py

import os

def get_prompt_path(cache_dir, filename):
    """Constructs the full path for a prompt file inside the cache."""
    return os.path.join(cache_dir, filename)

def load_prompt_from_file(cache_dir, filename, default_content):
    """
    Loads a specific prompt from the cache directory.
    If the file doesn't exist, it returns the default content.
    """
    filepath = get_prompt_path(cache_dir, filename)
    if not os.path.exists(filepath):
        return default_content
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except IOError:
        return default_content

def save_prompt_to_file(cache_dir, filename, content):
    """
    Saves content to a specific prompt file in the cache directory.
    """
    os.makedirs(cache_dir, exist_ok=True)
    filepath = get_prompt_path(cache_dir, filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

def delete_prompt_file(cache_dir, filename):
    """
    Deletes a specific prompt file from the cache directory if it exists.
    """
    filepath = get_prompt_path(cache_dir, filename)
    if os.path.exists(filepath):
        os.remove(filepath)
        return True
    return False 
