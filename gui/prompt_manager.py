# python/gui/prompt_manager.py

import customtkinter as ctk
from tkinter import messagebox
import os
from python.gui.prompt_utils import (
    load_prompt_from_file,
    save_prompt_to_file,
    delete_prompt_file
)
# 从 utils 导入新的全局路径函数
from python.logic.utils import get_global_prompt_cache_dir
# 从重构后的 process_logic 导入提示词的常量定义
try:
    from ..logic.prompts import (
        DEFAULT_PROMPTS
    )
except ImportError:
    # 定义一个存根，以便在极端情况下UI也能加载
    DEFAULT_PROMPTS = {k: {"filename": "", "default": f"错误：无法加载 {k}"} for k in [
        "general_prepend_prompt", "prompt_small_summary", "prompt_big_plot",
        "prompt_big_char", "prompt_super_plot_p1", "prompt_super_plot_p2",
        "prompt_super_char_p1", "prompt_super_char_p2",
        "prompt_ultimate_plot_p1", "prompt_ultimate_plot_p2",
        "prompt_ultimate_char_p1", "prompt_ultimate_char_p2",
        "prompt_article_section", "prompt_article_final"
    ]}


class PromptManagerMixin:
    """
    一个Mixin类，用于封装所有与提示词编辑器UI和逻辑相关的功能。
    """
    def __init__(self):
        # 使用从 process_logic 导入的常量来构建映射
        self.prompt_map = {
            "小说 - 1. 独立小总结 (章节总结)": DEFAULT_PROMPTS["prompt_small_summary"],
            "小说 - 2. 剧情大总结": DEFAULT_PROMPTS["prompt_big_plot"],
            "小说 - 3. 角色大总结": DEFAULT_PROMPTS["prompt_big_char"],
            "小说 - 4. 超级剧情总结 - P1": DEFAULT_PROMPTS["prompt_super_plot_p1"],
            "小说 - 5. 超级剧情总结 - P2": DEFAULT_PROMPTS["prompt_super_plot_p2"],
            "小说 - 6. 超级角色总结 - P1": DEFAULT_PROMPTS["prompt_super_char_p1"],
            "小说 - 7. 超级角色总结 - P2": DEFAULT_PROMPTS["prompt_super_char_p2"],
            "小说 - 8. 终极剧情总结 - P1": DEFAULT_PROMPTS["prompt_ultimate_plot_p1"],
            "小说 - 9. 终极剧情总结 - P2": DEFAULT_PROMPTS["prompt_ultimate_plot_p2"],
            "小说 - 10. 终极角色总结 - P1": DEFAULT_PROMPTS["prompt_ultimate_char_p1"],
            "小说 - 11. 终极角色总结 - P2": DEFAULT_PROMPTS["prompt_ultimate_char_p2"],
            # --- 文章总结分类 ---
            "文章 - 1. 段落总结": DEFAULT_PROMPTS["prompt_article_section"],
            "文章 - 2. 最终总结": DEFAULT_PROMPTS["prompt_article_final"],
        }
        self.prompt_is_dirty = False
        self.current_loaded_prompt_name = ""
        # 通用前缀提示词单独处理
        self.general_prompt_config = DEFAULT_PROMPTS["general_prepend_prompt"]


    def create_prompt_editor_tab(self, parent_tab):
        """在指定的父选项卡中创建提示词编辑器的所有UI组件。"""
        self.prompt_type_var = ctk.StringVar()
        
        parent_tab.grid_columnconfigure(0, weight=1)
        parent_tab.grid_rowconfigure(1, weight=1)

        control_frame = ctk.CTkFrame(parent_tab)
        control_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        control_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(control_frame, text="选择要编辑的提示词:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        
        prompt_choices = ["通用预设前缀提示词"] + list(self.prompt_map.keys())
        self.prompt_combobox = ctk.CTkComboBox(
            control_frame, 
            values=prompt_choices,
            variable=self.prompt_type_var,
            command=self.on_prompt_type_selected,
            state="readonly"
        )
        self.prompt_combobox.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        
        self.button_save_prompt = ctk.CTkButton(
            control_frame, 
            text="保存当前修改",
            command=self.save_current_prompt,
            state="disabled"
        )
        self.button_save_prompt.grid(row=0, column=2, padx=10, pady=5)

        self.button_reset_prompt = ctk.CTkButton(
            control_frame,
            text="恢复默认提示词",
            command=self.confirm_reset_prompts,
        )
        self.button_reset_prompt.grid(row=0, column=3, padx=(5, 10), pady=5)


        self.prompt_text_area = ctk.CTkTextbox(parent_tab, wrap="word", font=("", 14))
        self.prompt_text_area.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        self.bind_right_click_menu(self.prompt_text_area)
        self.prompt_text_area.bind("<Key>", self._mark_prompt_as_dirty)

    def _mark_prompt_as_dirty(self, event=None):
        self.prompt_is_dirty = True

    def on_prompt_type_selected(self, event=None):
        selected_prompt_name = self.prompt_type_var.get()

        if selected_prompt_name == self.current_loaded_prompt_name:
            return

        if self.prompt_is_dirty:
            response = messagebox.askyesnocancel(
                "未保存的更改",
                f"您对 '{self.current_loaded_prompt_name}' 的修改尚未保存。\n\n"
                "要保存您的更改吗？",
                parent=self.root
            )
            if response is True:
                self.save_current_prompt(suppress_message=True)
            elif response is None:
                self.prompt_type_var.set(self.current_loaded_prompt_name)
                return
        
        self.current_loaded_prompt_name = selected_prompt_name
        
        if not selected_prompt_name:
            self.prompt_text_area.delete("1.0", "end")
            self.button_save_prompt.configure(state="disabled")
            self.prompt_is_dirty = False
            return

        # 修改：不再检查小说文件夹路径，直接使用全局缓存
        cache_dir = get_global_prompt_cache_dir()
        
        content = ""
        if selected_prompt_name == "通用预设前缀提示词":
            filename = self.general_prompt_config["filename"]
            default_content = self.general_prompt_config["default"]
            content = load_prompt_from_file(cache_dir, filename, default_content)
        elif selected_prompt_name in self.prompt_map:
            config = self.prompt_map[selected_prompt_name]
            content = load_prompt_from_file(cache_dir, config["filename"], config["default"])
        else:
            content = "错误：未知的提示词类型。"
        
        self.prompt_text_area.delete("1.0", "end")
        self.prompt_text_area.insert("1.0", content)
        self.button_save_prompt.configure(state="normal")
        self.log_message_gui('global', f"已加载提示词 '{selected_prompt_name}' 以供编辑。")
        
        self.prompt_is_dirty = False

    def save_current_prompt(self, suppress_message=False):
        selected_prompt_name = self.current_loaded_prompt_name
        if not selected_prompt_name:
            messagebox.showerror("错误", "没有选择要保存的提示词类型。", parent=self.root)
            return

        content_to_save = self.prompt_text_area.get("1.0", "end-1c")
        
        # 修改：不再获取小说文件夹路径，直接使用全局缓存
        cache_dir = get_global_prompt_cache_dir()
        
        try:
            filename = ""
            if selected_prompt_name == "通用预设前缀提示词":
                filename = self.general_prompt_config["filename"]
            elif selected_prompt_name in self.prompt_map:
                filename = self.prompt_map[selected_prompt_name]["filename"]
            
            if not filename:
                raise ValueError("未知的提示词类型，无法找到文件名。")

            save_prompt_to_file(cache_dir, filename, content_to_save)
            
            self.log_message_gui('global', f"成功保存提示词 '{selected_prompt_name}'。")
            if not suppress_message:
                messagebox.showinfo("保存成功", f"提示词 '{selected_prompt_name}' 已成功保存。", parent=self.root)
            
            self.prompt_is_dirty = False
        
        except ValueError as e:
            self.log_message_gui('global', f"保存提示词时发生错误: {e}")
            messagebox.showerror("保存失败", f"保存提示词时发生错误: {e}", parent=self.root)

    def confirm_reset_prompts(self):
        # 修改：不再检查小说文件夹路径，直接使用全局缓存
        cache_dir = get_global_prompt_cache_dir()

        msg = ("确定要将【所有】提示词恢复为默认设置吗？\n\n"
               "这将会删除您对所有提示词的自定义修改。\n"
               "此操作会影响所有使用本工具的项目。\n\n"
               "此操作无法撤销。")

        if messagebox.askyesno("确认恢复默认提示词", msg, parent=self.root, icon='warning'):
            try:
                # 获取所有提示词文件名
                prompt_files_to_delete = [self.general_prompt_config["filename"]]
                for config in self.prompt_map.values():
                    prompt_files_to_delete.append(config["filename"])

                deleted_count = 0
                for filename in set(prompt_files_to_delete): # 使用 set 去重
                    if filename and delete_prompt_file(cache_dir, filename):
                        deleted_count += 1
                
                self.log_message_gui('global', f"已删除 {deleted_count} 个自定义提示词文件，将恢复为默认设置。")
                messagebox.showinfo("重置成功", "所有提示词已恢复为默认设置。", parent=self.root)
                
                self.prompt_is_dirty = False
                self.on_prompt_type_selected()

            except Exception as e:
                self.log_message_gui('global', f"恢复默认提示词时失败: {e}")
                messagebox.showerror("错误", f"恢复默认提示词时发生错误: {e}", parent=self.root)

    def write_all_default_prompts_to_cache(self):
        """
        将所有在 DEFAULT_PROMPTS 中定义的提示词的默认内容强制写入全局缓存。
        这个方法主要用于在重置缓存后恢复提示词文件。
        """
        cache_dir = get_global_prompt_cache_dir()
        try:
            # 确保缓存目录存在
            os.makedirs(cache_dir, exist_ok=True)
            
            all_prompts = list(self.prompt_map.values()) + [self.general_prompt_config]
            
            saved_count = 0
            for config in all_prompts:
                filename = config.get("filename")
                default_content = config.get("default")
                if filename and default_content:
                    save_prompt_to_file(cache_dir, filename, default_content)
                    saved_count += 1
            
            self.log_message_gui('global', f"已将 {saved_count} 个默认提示词写入缓存。")
            
        except Exception as e:
            self.log_message_gui('global', f"写入默认提示词到缓存时失败: {e}")
            messagebox.showerror("错误", f"写入默认提示词时发生错误: {e}", parent=self.root)
