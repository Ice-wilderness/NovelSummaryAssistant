# python/gui/api_manager.py

import customtkinter as ctk
from tkinter import messagebox
import json
import os
import threading
import time
import uuid
import traceback
import asyncio
from python.gui.ui_helpers import create_help_button

# 尝试导入后端逻辑，如果失败则使用存根函数 (使用相对导入)
try:
    from ..logic.llm_api import fetch_available_models
except ImportError:
    def fetch_available_models(*args, **kwargs):
        print("CRITICAL ERROR: process_logic.py not found. Cannot fetch models.")
        return []

class ApiManagerMixin:
    """
    一个Mixin类，用于封装所有与API配置和管理相关的UI和逻辑。
    """
    def __init__(self):
        """初始化API管理器相关的变量。"""
        self.api_entries = []
        self.api_id_counter = 0
        self.api_configs = []
        
    def create_api_config_tab(self, parent_tab):
        """在指定的父选项卡中创建API配置界面的所有UI组件。"""
        # --- UI 布局 ---
        parent_tab.grid_columnconfigure(0, weight=1)
        parent_tab.grid_rowconfigure(1, weight=1)

        # --- 顶部控制栏 ---
        top_frame = ctk.CTkFrame(parent_tab)
        top_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)

        ctk.CTkLabel(top_frame, text="大总结触发阈值 (文件数):").pack(side="left", padx=(15, 2))
        self.big_summary_batch_size_var = ctk.StringVar(value="5")
        self.batch_size_entry = ctk.CTkEntry(top_frame, width=50, textvariable=self.big_summary_batch_size_var)
        self.batch_size_entry.pack(side="left", padx=2)
        self.bind_right_click_menu(self.batch_size_entry)
        
        batch_size_help = (
            "此设置决定了系统在处理多少个'小总结'文件后，\n"
            "会自动将它们合并成一个'大总结'。\n\n"
            "例如，设置为5，则每处理完5个章节的独立总结，\n"
            "就会触发一次整合，生成一个包含这5章内容的\n"
            "剧情和角色大总结。"
        )
        create_help_button(top_frame, batch_size_help).pack(side="left", padx=(0, 5))
        
        ctk.CTkLabel(top_frame, text="   |   终极总结执行者:").pack(side="left", padx=(15, 2))
        self.ultimate_api_selector_var = ctk.StringVar(value="默认 (第一个API)")
        self.ultimate_api_selector = ctk.CTkComboBox(
            top_frame,
            variable=self.ultimate_api_selector_var,
            values=["默认 (第一个API)"],
            state="readonly"
        )
        self.ultimate_api_selector.pack(side="left", padx=2)
        
        ultimate_api_help = (
            "此设置用于指定哪个API配置专门负责执行最终的\n"
            '终极总结'任务。\n\n"
            "这些最终总结任务通常需要更长的上下文处理能力和\n"
            "更强的模型性能。建议选择您最强大的API配置。\n\n"
            "如果选择'默认'，则会使用列表中的第一个API。"
        )
        create_help_button(top_frame, ultimate_api_help).pack(side="left", padx=(0, 5))
        
        self.scrollable_api_frame = ctk.CTkScrollableFrame(parent_tab, label_text="API 配置列表")
        self.scrollable_api_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        self.scrollable_api_frame.grid_columnconfigure(0, weight=1)

        bottom_frame = ctk.CTkFrame(parent_tab)
        bottom_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=10)
        self.add_api_button = ctk.CTkButton(bottom_frame, text="添加一个API", command=self._add_new_api_entry_ui)
        self.add_api_button.pack(side="left", padx=5)
        self.save_api_button = ctk.CTkButton(bottom_frame, text="保存当前API配置", command=self._save_button_action)
        self.save_api_button.pack(side="left", padx=5)
        self.load_api_button = ctk.CTkButton(bottom_frame, text="加载上次保存的配置", command=self.load_api_configs_from_file)
        self.load_api_button.pack(side="left", padx=5)
        self.button_reset_api = ctk.CTkButton(bottom_frame, text="恢复默认配置", command=self.confirm_reset_api_configs)
        self.button_reset_api.pack(side="left", padx=(15, 5))

    def _populate_api_listbox(self):
        for widget in self.scrollable_api_frame.winfo_children():
            widget.destroy()
        self.api_entries.clear()

        for index, api_config in enumerate(self.api_configs):
            api_id = api_config.get("id")

            entry_frame = ctk.CTkFrame(self.scrollable_api_frame)
            entry_frame.grid(row=index, column=0, sticky="ew", pady=(0, 15), padx=5)
            entry_frame.grid_columnconfigure(1, weight=1)

            content_frame = ctk.CTkFrame(entry_frame, fg_color="transparent")
            content_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=5, pady=5)
            content_frame.grid_columnconfigure(0, weight=1)

            row_counter = 0

            display_index = index + 1
            id_label_text = f"API-{display_index}"
            ctk.CTkLabel(content_frame, text=id_label_text, anchor="w", font=ctk.CTkFont(weight="bold")).grid(
                row=row_counter, column=0, sticky="ew", pady=(0, 2)
            )
            row_counter += 1

            url_var = ctk.StringVar(value=api_config.get("url", ""))
            url_entry = ctk.CTkEntry(content_frame, textvariable=url_var, placeholder_text="API URL")
            url_entry.grid(row=row_counter, column=0, sticky="ew", pady=2)
            self.bind_right_click_menu(url_entry)
            row_counter += 1

            key_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
            key_frame.grid(row=row_counter, column=0, sticky="ew", pady=2)
            key_frame.grid_columnconfigure(0, weight=1)

            key_var = ctk.StringVar(value=api_config.get("key", ""))
            key_entry = ctk.CTkEntry(key_frame, textvariable=key_var, placeholder_text="API Key", show="*")
            key_entry.grid(row=0, column=0, sticky="ew")
            self.bind_right_click_menu(key_entry)

            show_hide_button = ctk.CTkButton(key_frame, text="显示", width=40, command=lambda k=key_entry: self._toggle_key_visibility(k))
            show_hide_button.grid(row=0, column=1, padx=(5, 0))
            row_counter += 1

            model_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
            model_frame.grid(row=row_counter, column=0, sticky="ew", pady=2)
            model_frame.grid_columnconfigure(0, weight=1)

            model = api_config.get("model", "")
            model_var = ctk.StringVar(value=model if model else "点击'获取模型'自动填充")
            model_combobox = ctk.CTkComboBox(model_frame, variable=model_var, values=[model] if model else [], state="normal")
            model_combobox.grid(row=0, column=0, sticky="ew", padx=(0, 5))
            
            ctk.CTkButton(model_frame, text="获取模型", width=80, command=lambda u=url_var, k=key_var, i=api_id: self.update_model_list(u, k, i)).grid(row=0, column=1)
            row_counter += 1

            params_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
            params_frame.grid(row=row_counter, column=0, sticky="w", pady=(5, 5))

            max_tokens_var = ctk.StringVar(value=str(api_config.get("max_tokens", "65535")))
            ctk.CTkLabel(params_frame, text="MaxTokens:").pack(side="left")
            max_tokens_entry = ctk.CTkEntry(params_frame, textvariable=max_tokens_var, width=60)
            max_tokens_entry.pack(side="left", padx=(2, 10))
            self.bind_right_click_menu(max_tokens_entry)

            temperature_var = ctk.StringVar(value=str(api_config.get("temperature", "1.0")))
            ctk.CTkLabel(params_frame, text="Temp:").pack(side="left")
            temp_entry = ctk.CTkEntry(params_frame, textvariable=temperature_var, width=40)
            temp_entry.pack(side="left", padx=(2, 10))
            self.bind_right_click_menu(temp_entry)
            
            row_counter += 1
            adv_params_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
            adv_params_frame.grid(row=row_counter, column=0, sticky="w", pady=(5, 5))
            
            timeout_var = ctk.StringVar(value=str(api_config.get("timeout", "180")))
            ctk.CTkLabel(adv_params_frame, text="Timeout(s):").pack(side="left")
            timeout_entry = ctk.CTkEntry(adv_params_frame, textvariable=timeout_var, width=50)
            timeout_entry.pack(side="left", padx=(2, 2))
            self.bind_right_click_menu(timeout_entry)
            
            timeout_help_text = "请求单个API调用的最大等待时间（秒）。"
            create_help_button(adv_params_frame, timeout_help_text).pack(side="left", padx=(0, 10))

            retries_var = ctk.StringVar(value=str(api_config.get("max_retries", "3")))
            ctk.CTkLabel(adv_params_frame, text="Retries:").pack(side="left")
            retries_entry = ctk.CTkEntry(adv_params_frame, textvariable=retries_var, width=40)
            retries_entry.pack(side="left", padx=(2, 2))
            self.bind_right_click_menu(retries_entry)

            retries_help_text = "当API调用失败时自动重新尝试的次数。"
            create_help_button(adv_params_frame, retries_help_text).pack(side="left", padx=(0, 10))

            stream_var = ctk.BooleanVar(value=api_config.get("stream", True))
            ctk.CTkCheckBox(params_frame, text="流式", variable=stream_var).pack(side="left")
            row_counter += 1
            
            log_label = ctk.CTkLabel(content_frame, text="状态: 空闲", anchor="w", text_color="gray")
            log_label.grid(row=row_counter, column=0, sticky="ew", pady=(5, 0))
            row_counter += 1

            button_frame = ctk.CTkFrame(entry_frame, fg_color="transparent")
            button_frame.grid(row=0, column=2, sticky="ns", padx=5, pady=5)
            
            active_var = ctk.BooleanVar(value=api_config.get("is_active", True))
            active_checkbox = ctk.CTkCheckBox(button_frame, text="启用", variable=active_var, command=self._sync_ui_to_configs_and_save)
            active_checkbox.pack(pady=2)

            ctk.CTkButton(button_frame, text="删除", width=80, fg_color="#D32F2F", hover_color="#B71C1C", command=lambda current_id=api_id: self.remove_api_entry(current_id)).pack(pady=2)

            entry_data = {
                "id": api_id,"display_index": display_index, "frame": entry_frame, "url": url_var,
                "key": key_var, "model_combobox": model_combobox,
                "key_entry": key_entry,
                "max_tokens": max_tokens_var, "temperature": temperature_var,
                "stream_var": stream_var,
                "timeout": timeout_var, "max_retries": retries_var,
                "log_label": log_label,
                "active_var": active_var,
            }
            self.api_entries.append(entry_data)
            self.scrollable_api_frame._parent_canvas.yview_moveto(0.0)
            
        self._update_ultimate_api_selector()
        if hasattr(self, '_update_custom_api_selector'):
            self._update_custom_api_selector()
        
        if hasattr(self, '_redraw_super_summary_assignments_ui'):
            self._redraw_super_summary_assignments_ui()
    
    def _toggle_key_visibility(self, key_entry):
        """切换API Key输入框的可见性。"""
        if key_entry.cget("show") == "*":
            key_entry.configure(show="")
        else:
            key_entry.configure(show="*")

    def _sync_ui_to_configs_and_save(self):
        """当任何可能影响API列表或其状态的UI元素被更改时调用，例如切换'启用'复选框。"""
        self._sync_ui_to_configs()
        # 静默保存，不弹出"保存成功"的提示框
        self.save_api_configs_to_file(suppress_message=True)

    def get_api_display_name(self, api_id):
        for entry in self.api_entries:
            if entry.get("id") == api_id:
                return f"API-{entry['display_index']}"
        return api_id

    def update_api_log(self, api_id, message):
        """线程安全地更新指定API的日志区域。"""
        entry = self._get_api_entry_by_id(api_id)
        if entry and entry.get('log_label'):
            entry['log_label'].configure(text=f"状态: {message}")

    def _add_new_api_entry_ui(self, config_to_add=None):
        """向UI中添加一个新的API条目。"""
        self._sync_ui_to_configs()
        
        if config_to_add:
            new_config = config_to_add
        else:
            new_id = f"api_{int(time.time())}_{self.api_id_counter}"
            self.api_id_counter += 1
            new_config = {"id": new_id, "is_active": True, "stream": True}
        
        self.api_configs.append(new_config)
        self._populate_api_listbox()

    def remove_api_entry(self, api_id_to_remove):
        """根据API ID从UI和配置列表中移除一个条目。"""
        self._sync_ui_to_configs()
        self.api_configs = [c for c in self.api_configs if c.get("id") != api_id_to_remove]
        self._populate_api_listbox()

    def _sync_ui_to_configs(self):
        """
        核心函数：从UI控件读取当前值，并更新内部的self.api_configs列表。
        这确保了在保存或执行任何操作之前，数据模型都是最新的。
        """
        if not self.api_entries:
            self.api_configs = []
            return

        synced_configs = []
        for entry in self.api_entries:
            try:
                config = {
                    "id": entry["id"],
                    "url": entry["url"].get().strip(),
                    "key": entry["key"].get().strip(),
                    "model": entry["model_combobox"].get().strip(),
                    "is_active": entry["active_var"].get(),
                    "stream": entry["stream_var"].get(),
                }
                
                # 安全地转换数字参数，如果失败则回退到默认值或0
                try:
                    config["max_tokens"] = int(entry["max_tokens"].get().strip())
                except (ValueError, TypeError):
                    config["max_tokens"] = 65535 
                try:
                    config["temperature"] = float(entry["temperature"].get().strip())
                except (ValueError, TypeError):
                    config["temperature"] = 1.0
                try:
                    config["timeout"] = int(entry["timeout"].get().strip())
                except (ValueError, TypeError):
                    config["timeout"] = 180
                try:
                    config["max_retries"] = int(entry["max_retries"].get().strip())
                except (ValueError, TypeError):
                    config["max_retries"] = 3

                synced_configs.append(config)
            except Exception as e:
                # 记录在同步特定条目时发生的错误，但继续处理其余条目
                print(f"Error syncing API entry with ID {entry.get('id', 'N/A')}: {e}")

        self.api_configs = synced_configs

    def _save_button_action(self):
        """保存按钮的动作，不静默，会显示成功消息。"""
        self.save_api_configs_to_file(suppress_message=False)

    def save_api_configs_to_file(self, filepath=None, suppress_message=False):
        # 如果没有提供显式路径，则使用主程序中定义的标准路径
        if filepath is None:
            filepath = self.api_config_path
        
        # 确保目录存在
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        self._sync_ui_to_configs()
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.api_configs, f, indent=4)
        
        if not suppress_message:
            messagebox.showinfo("成功", f"API配置已保存到:\\n{filepath}", parent=self.root)

    def load_api_configs_from_file(self, filepath=None):
        """
        从文件加载API配置。如果文件不存在，则加载默认配置。
        """
        # 如果没有提供显式路径，则使用主程序中定义的标准路径
        if filepath is None:
            filepath = self.api_config_path

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                self.api_configs = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            self.log_message_gui("global", f"API配置文件 '{filepath}' 加载失败或不存在，将加载默认模板。错误: {e}", status="warning")
            self.api_configs = self.get_default_api_configs()
        
        self._ensure_api_ids()
        self._populate_api_listbox()

    def update_model_list(self, url_var, key_var, api_id):
        """为指定的API条目异步获取模型列表。"""
        url = url_var.get().strip()
        key = key_var.get().strip()
        if not url or not key:
            messagebox.showerror("需要信息", "请输入API URL和Key以获取模型列表。", parent=self.root)
            return
        
        entry = self._get_api_entry_by_id(api_id)
        if entry:
            entry['log_label'].configure(text="状态: 正在获取模型...")
        
        # 在一个单独的线程中运行异步任务
        thread = threading.Thread(target=self._fetch_models_thread, args=(url, key, api_id))
        thread.daemon = True
        thread.start()

    def _fetch_models_thread(self, url, key, api_id):
        """在一个独立的线程中运行异步的 `fetch_available_models` 函数。"""
        def log_to_gui(log_item):
            # 统一使用主日志队列
            # 调用正确的GUI日志接口，并解包字典参数
            self.log_message_gui(**log_item)

        async def run_fetch():
            """异步执行模型获取和UI更新。"""
            # 为回调函数提供更健壮的签名
            def backend_log_callback(message, status=None, api_id_override=None, is_progress_log=False, progress_text=None, traceback_info=None):
                """从后端逻辑调用的回调函数，用于更新GUI。"""
                # 构建一个与 log_message_gui 参数匹配的字典
                log_item = {
                    'source_id': api_id_override or api_id,
                    'message': message,
                    'is_progress_log': is_progress_log,
                    'progress_text': progress_text,
                    'api_id_for_log': api_id_override or api_id,
                    'traceback_info': traceback_info,
                    'status': status
                }
                # 使用 self.root.after 确保UI更新在主线程中执行
                self.root.after(0, log_to_gui, log_item)

            try:
                # 更新API条目的状态
                # 构建一个与 log_message_gui 参数匹配的字典
                log_item = {
                    'source_id': api_id,
                    'message': "正在获取模型列表...",
                    'is_progress_log': False,
                    'progress_text': None,
                    'api_id_for_log': api_id,
                    'traceback_info': None,
                    'status': "START"
                }
                self.root.after(0, self.on_update_api_log, log_item)
                
                # 调用后端逻辑
                models, error = await fetch_available_models(
                    url, key,
                    log_callback=backend_log_callback,
                    api_id_for_log=api_id
                )

                # 准备更新UI的数据
                update_data = {'api_id': api_id, 'models': models, 'error': error}
                # 在主线程中更新UI
                self.root.after(0, self.on_update_model_list, update_data)
                
            except Exception as e:
                # 捕获未知错误
                tb_info = traceback.format_exc()
                error_message = f"获取模型时发生意外错误: {e}"
                
                # 构建一个与 log_message_gui 参数匹配的字典
                log_item = {
                    'source_id': api_id,
                    'message': error_message,
                    'is_progress_log': False,
                    'progress_text': None,
                    'api_id_for_log': api_id,
                    'traceback_info': tb_info,
                    'status': "FAIL"
                }
                log_to_gui(log_item)

                # 确保即使在发生异常时也能更新UI以显示错误状态
                update_data = {'api_id': api_id, 'models': [], 'error': error_message}
                self.root.after(0, self.on_update_model_list, update_data)

        # 启动异步事件循环来运行 run_fetch
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        loop.run_until_complete(run_fetch())

    def on_update_api_log(self, log_item):
        """
        【已废弃】现在由 queue_log_message 和 process_log_queue 处理
        """
        pass

    def on_update_model_list(self, data):
        """
        在主GUI线程中安全地更新API条目的模型列表。
        """
        api_id = data.get("api_id")
        models = data.get("models")
        error = data.get("error")

        entry = self._get_api_entry_by_id(api_id)
        if not entry:
            return

        model_combobox = entry.get("model_combobox")
        log_label = entry.get("log_label")

        if not model_combobox:
            return
            
        current_model = model_combobox.get()

        if models is not None:
            # 更新状态标签
            if log_label:
                log_label.configure(text="状态: 成功")
            # 更新模型列表
            model_combobox.configure(values=models)
            # 如果当前模型不在新列表中，或者当前模型是默认提示文本，则选择第一个
            if current_model not in models or "点击" in current_model:
                model_combobox.set(models[0] if models else "")
            # 成功后弹出提示
            messagebox.showinfo("获取成功", f"为 API-{entry.get('display_index')} 获取模型列表已成功更新。", parent=self.root)
        else:
            # 更新状态标签
            if log_label:
                log_label.configure(text=f"状态: 失败")
            # 如果获取失败，显示错误信息
            fail_message = "获取失败"
            model_combobox.configure(values=[fail_message])
            model_combobox.set(fail_message)
            messagebox.showerror("获取失败", f"为 API-{entry.get('display_index')} 获取模型列表失败。\n\n错误: {error}\n\n详细信息请查看全局日志。", parent=self.root)

    def confirm_reset_api_configs(self, force=False):
        """
        显示一个确认对话框，如果用户同意，则将API配置恢复为默认设置。
        """
        if force or messagebox.askyesno("确认", "确定要将API配置恢复为默认设置吗？\n当前的所有API条目都将被替换。", parent=self.root):
            filepath = self.api_config_path
            if os.path.exists(filepath):
                try:
                    os.remove(filepath)
                except OSError as e:
                    messagebox.showerror("错误", f"无法删除旧的API配置文件: {e}", parent=self.root)
                    return
            self.api_configs = self.get_default_api_configs()
            self._populate_api_listbox()
            self.log_message_gui('global', "API配置已恢复为默认设置。")

    def _ensure_api_ids(self):
        """确保从文件加载的每个API配置都有一个唯一的ID。"""
        for config in self.api_configs:
            if "id" not in config or not config["id"]:
                config["id"] = f"api_{int(time.time())}_{self.api_id_counter}"
                self.api_id_counter += 1

    def get_default_api_configs(self):
        """返回一个包含默认API配置的列表。"""
        return [
            {
                "id": f"api_{int(time.time())}",
                "url": "https://api.example.com/v1",
                "key": "",
                "model": "gpt-4",
                "max_tokens": 4096,
                "temperature": 0.7,
                "stream": True,
                "timeout": 180,
                "max_retries": 3,
                "is_active": True
            }
        ]

    def _update_ultimate_api_selector(self):
        """更新终极总结执行者的下拉框选项。"""
        current_selection = self.ultimate_api_selector_var.get()
        
        active_api_display_names = [
            f"API-{entry['display_index']}" 
            for entry in self.api_entries 
            if entry['active_var'].get()
        ]
        
        new_values = ["默认 (第一个API)"] + active_api_display_names
        self.ultimate_api_selector.configure(values=new_values)
        
        # 尝试保持用户的选择
        if current_selection in new_values:
            self.ultimate_api_selector.set(current_selection)
        else:
            self.ultimate_api_selector.set(new_values[0])

    def _get_api_entry_by_id(self, api_id):
        """通过ID在self.api_entries中查找一个条目。"""
        return next((entry for entry in self.api_entries if entry.get("id") == api_id), None)
