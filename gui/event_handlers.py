# gui/event_handlers.py

import customtkinter as ctk
from tkinter import filedialog, messagebox
import threading
import os
import shutil
import traceback
import uuid
import asyncio
import queue
from logic.prompts import DEFAULT_PROMPTS as PROMPT_CONFIGS
from logic.chapter_splitter import split_novel_into_chapter_files
from logic.article_summary_logic import run_article_summary_process
from logic.custom_summary_logic import run_custom_summary_process
from logic.state_manager import StateManager
from logic import orchestrator # 引入 orchestrator 以便访问


class EventHandlersMixin:
    """
    一个 Mixin 类，封装了GUI的主要事件处理函数，如按钮点击等。
    """
    def select_folder(self):
        """打开文件夹选择对话框，并设置小说文件夹路径。"""
        path = filedialog.askdirectory(title="选择源文件夹")
        if path:
            self.novel_folder_path.set(path)
            self.log_message_gui('global', f"已选择源文件夹: {path}")

    def select_source_txt_file(self):
        """为章节分割器选择源txt文件。"""
        path = filedialog.askopenfilename(title="选择小说源文件", filetypes=[("Text files", "*.txt"), ("All files", "*.*")])
        if path:
            self.source_txt_file_path_var.set(path)
            self.log_message_gui('global', f"已选择源文件: {path}")
            if not self.splitter_output_dir_path_var.get():
                output_dir = os.path.join(os.path.dirname(path), "splitted_chapters")
                self.splitter_output_dir_path_var.set(output_dir)
                self.log_message_gui('global', f"自动设置输出目录为: {output_dir}")

    def select_splitter_output_dir(self):
        """为章节分割器选择输出目录。"""
        path = filedialog.askdirectory(title="选择分割后章节的存放文件夹")
        if path:
            self.splitter_output_dir_path_var.set(path)
            self.log_message_gui('global', f"已设置分割输出目录: {path}")

    def pause_summarization(self):
        """暂停或恢复总结任务。"""
        if self.pause_event.is_set():
            self.pause_event.clear()
            self.log_message_gui('global', "任务已恢复。", is_progress_log=True)
            self.set_ui_state_running()
        else:
            self.pause_event.set()
            self.log_message_gui('global', "任务已暂停。等待用户操作...", is_progress_log=True)
            self.set_ui_state_paused()

    def stop_summarization(self):
        """【重构】请求立即停止后台总结任务。"""
        if self.backend_thread and self.backend_thread.is_alive() and self.backend_task:
            if messagebox.askyesno("确认停止", "确定要立即取消当前任务吗？", parent=self.root):
                self.log_message_gui('global', "正在发送取消信号...", is_progress_log=True)
                
                # 通过线程安全的调用来取消任务
                if self.backend_loop:
                    self.backend_loop.call_soon_threadsafe(self.backend_task.cancel)
                
                # 禁用按钮，防止重复点击
                self.button_stop.configure(state="disabled")
        else:
            self.log_message_gui('global', "没有正在运行的任务可以停止。", "INFO")
    
    def confirm_reset_cache(self):
        """确认并删除当前小说文件夹下的所有任务缓存。"""
        folder_path = self.novel_folder_path.get()
        if not folder_path or not os.path.isdir(folder_path):
            messagebox.showwarning("需要文件夹", "请先在主界面选择一个有效的小说文件夹。", parent=self.root)
            return

        cache_dir = os.path.join(folder_path, ".summarizer_cache")
        if not os.path.isdir(cache_dir):
            messagebox.showinfo("无需重置", "未找到任何任务缓存，无需操作。", parent=self.root)
            return

        msg = (f"这将重置位于以下文件夹中的任务进度：\n\n"
               f"{os.path.basename(folder_path)}\n\n"
               f"此操作会清空所有已生成的总结文件和任务进度状态，但【不会】影响您在'提示词编辑器'中保存的自定义提示词。\n\n"
               f"此操作无法撤销。确定要继续吗？")
        
        if messagebox.askyesno("警告：重置任务进度", msg, parent=self.root, icon='warning'):
            try:
                # 停止任何正在进行的后台任务
                if hasattr(self, 'backend_thread') and self.backend_thread and self.backend_thread.is_alive():
                    # 使用新的取消机制
                    if self.backend_loop and self.backend_task:
                        self.backend_loop.call_soon_threadsafe(self.backend_task.cancel)
                    self.log_message_gui('global', "正在等待后台任务停止...")
                
                # 【修复】更健壮的缓存清理逻辑
                items_in_cache = os.listdir(cache_dir)
                for item in items_in_cache:
                    # 保留用户的自定义提示词和状态文件（稍后会单独重置）
                    if item == 'prompt_cache' or item == 'state.json':
                        continue
                    
                    item_path = os.path.join(cache_dir, item)
                    try:
                        if os.path.isdir(item_path):
                            shutil.rmtree(item_path)
                            self.log_message_gui('global', f"已删除缓存目录: {item}")
                        else:
                            os.remove(item_path)
                            self.log_message_gui('global', f"已删除缓存文件: {item}")
                    except Exception as e:
                        self.log_message_gui('global', f"删除 {item} 时出错: {e}", "WARN")

                # 【修复】调用 StateManager 类的方法来重置状态
                try:
                    state_manager = StateManager(folder_path)
                    if state_manager.reset_state():
                        self.log_message_gui('global', "已成功重置任务状态文件。")
                    else:
                        self.log_message_gui('global', "任务状态文件重置失败或无需重置。", "WARN")
                except Exception as e:
                    self.log_message_gui('global', f"重置状态文件时发生严重错误: {e}", "ERROR")

                # 重新写入默认提示词
                self.write_all_default_prompts_to_cache()
                
                self.log_message_gui('global', "任务进度已成功重置。")
                messagebox.showinfo("重置成功", "任务进度已重置。", parent=self.root)

            except Exception as e:
                self.log_message_gui('global', f"重置缓存时失败: {e}\n{traceback.format_exc()}")
                messagebox.showerror("错误", f"重置缓存时发生错误: {e}", parent=self.root)
    
    def _validate_and_get_active_apis(self):
        """验证所有API条目并返回配置列表。"""
        if not self.api_entries:
            messagebox.showerror("错误", "请至少添加并配置一个API。", parent=self.root)
            return None

        active_api_configs = []
        for entry in self.api_entries:
            if not entry["active_var"].get():
                continue

            config = {
                "id": entry["id"],
                "display_index": entry.get("display_index"),
                "url": entry["url"].get().strip(),
                "key": entry["key"].get().strip(),
                "model": entry["model_combobox"].get().strip(),
                "stream": entry["stream_var"].get()
            }

            # 将API的界面索引（例如，1, 2, 3）格式化为 'api1', 'api2' 并添加到配置中
            # 这样下游的 llm_api 模块就可以用它来生成更友好的日志
            if config.get("display_index"):
                config["api_key_name"] = f"api{config['display_index']}"

            if not all([config["url"], config["key"], config["model"]]) or "点击" in config["model"] or "获取失败" in config["model"]:
                messagebox.showerror("配置不完整", f"API-{config.get('display_index', config['id'])} 的配置不完整 (URL, Key, Model都必须填写)。", parent=self.root)
                return None
            
            try:
                max_tokens_str = entry["max_tokens"].get().strip()
                config["max_tokens"] = int(max_tokens_str) if max_tokens_str else 0
                temp_str = entry["temperature"].get().strip()
                config["temperature"] = float(temp_str) if temp_str else 1.0
                timeout_str = entry["timeout"].get().strip()
                config["timeout"] = int(timeout_str) if timeout_str else 180
                retries_str = entry["max_retries"].get().strip()
                config["max_retries"] = int(retries_str) if retries_str else 3
            except (ValueError, TypeError):
                messagebox.showerror("参数错误", f"API-{config.get('display_index', config['id'])} 的 MaxTokens、Temperature、Timeout 或 Retries 必须是有效的数字。", parent=self.root)
                return None
            
            active_api_configs.append(config)
        
        # 使用 api_key_name (例如 'api1') 作为日志区域的唯一标识符
        for config in active_api_configs:
            api_key_name = config.get('api_key_name')
            if api_key_name and api_key_name not in self.api_log_areas:
                # 传递友好名称给 create_log_tab
                self.create_log_tab(api_key_name)
                
        return active_api_configs

    def start_summarization(self):
        """
        启动总结任务的调度器。
        根据 self.summary_mode_var 的值，决定启动小说总结还是文章总结。
        """
        # --- 核心修复：检查所有可能的后台线程 ---
        if (self.backend_thread and self.backend_thread.is_alive()) or \
           (hasattr(self, 'custom_summary_thread') and self.custom_summary_thread and self.custom_summary_thread.is_alive()):
            messagebox.showwarning("任务运行中", "已有总结任务在后台运行。", parent=self.root)
            return

        # --- 通用验证 ---
        folder_path = self.novel_folder_path.get()
        if not folder_path or not os.path.isdir(folder_path):
            messagebox.showerror("错误", "请先选择一个有效的源文件夹。", parent=self.root)
            return

        # 将日志清理操作提前到所有检查和确认之前
        self.clear_log_areas()

        active_apis = self._validate_and_get_active_apis()
        if not active_apis:
            # 如果没有有效的API，日志区已经被清空，这是期望的行为
            return

        if not messagebox.askyesno("确认开始", "即将开始总结任务。\n\n- 如果是新任务，将从头开始。\n- 如果检测到旧进度，将自动从上次中断的地方继续。\n\n确定要开始吗？", parent=self.root):
            return

        # --- 根据模式调用不同的启动器 ---
        mode = self.summary_mode_var.get()
        if mode == "novel":
            # 用新的 StateManager 来获取 task_id
            try:
                state_manager = StateManager(folder_path)
                task_id = state_manager.task_id
                if not task_id:
                    messagebox.showerror("错误", "无法获取或创建任务ID，任务中止。", parent=self.root)
                    return
            except Exception as e:
                messagebox.showerror("错误", f"获取任务ID时发生错误: {e}", parent=self.root)
                traceback.print_exc()
                return

            self._start_novel_summarization(folder_path, active_apis, task_id)
        elif mode == "article":
            self._start_article_summarization(folder_path, active_apis)
        else:
            messagebox.showerror("未知模式", f"未知的总结模式: {mode}", parent=self.root)

    def _start_novel_summarization(self, folder_path, active_apis, task_id):
        """处理启动小说总结的逻辑"""
        # 确保每次启动时，事件状态都是干净的
        self.pause_event.clear()
        
        try:
            batch_size = int(self.big_summary_batch_size_var.get())
            if batch_size <= 0: raise ValueError
        except (ValueError, TypeError):
            messagebox.showerror("错误", "请输入有效的大总结触发阈值 (必须是大于0的整数)。", parent=self.root)
            return
            
        try:
            super_summary_threshold = int(self.super_summary_threshold_var.get())
            if super_summary_threshold <= 0: raise ValueError
        except (ValueError, TypeError):
            messagebox.showerror("错误", "请输入有效的超级大总结阈值 (必须是大于0的整数)。", parent=self.root)
            return

        word_counts = {key: var.get().strip() for key, var in self.word_count_vars.items()}
        for key, value in word_counts.items():
            if not value:
                messagebox.showerror("错误", f"字数设置 '{key}' 不能为空。", parent=self.root)
                return

        ultimate_api_display_name = self.ultimate_api_selector_var.get()
        if not ultimate_api_display_name or ultimate_api_display_name == "无":
            messagebox.showerror("错误", "请在'小说设置'中为终极总结指定一个API。", parent=self.root)
            return

        # --- BUG修复: 将用户选择的显示名称转换为真实的API ID ---
        real_ultimate_api_id = None
        if ultimate_api_display_name == "默认 (第一个API)":
            # 如果是默认选项，使用第一个活动的API
            if active_apis:
                real_ultimate_api_id = active_apis[0].get("id")
        else:
            # 否则，根据显示名称 (例如 "API-1") 找到对应的API ID
            try:
                # 从 "API-1" 中提取出索引 1
                selected_index = int(ultimate_api_display_name.split('-')[1])
                # 在活动的API列表中查找具有相同 display_index 的API
                target_api = next((api for api in active_apis if api.get("display_index") == selected_index), None)
                if target_api:
                    real_ultimate_api_id = target_api.get("id")
            except (IndexError, ValueError):
                # 如果名称格式不正确或无法转换，则记录错误
                self.log_message_gui('global', f"无法解析终极总结执行者 '{ultimate_api_display_name}' 的格式。", "ERROR")

        if not real_ultimate_api_id:
            messagebox.showerror("错误", f"无法为终极总结找到有效的API配置 (选择: {ultimate_api_display_name})。请检查API设置。", parent=self.root)
            return
        # 读取精细控制流程的设置
        use_fine_grained_flow = self.use_fine_grained_flow_var.get()
        api_assignments = self.super_summary_api_assignments if use_fine_grained_flow else {}
        word_counts = self.get_current_word_counts()

        self.log_message_gui('global', "--- 开始小说总结任务 ---")
        self.set_ui_state_running()

        # 【重构】创建后台任务协程
        coro = orchestrator.run_summarization_process(
            novel_folder_path=folder_path,
            active_api_configs=active_apis,
            log_callback=self.log_message_gui,
            pause_event=self.pause_event,
            big_summary_batch_size=batch_size,
            super_summary_threshold=super_summary_threshold,
            ultimate_api_id=real_ultimate_api_id,
            word_counts=word_counts,
            task_id=task_id,
            use_fine_grained_flow=use_fine_grained_flow
        )

        # 【重构】使用新的辅助函数启动后台任务
        self._run_async_task_in_thread(coro, on_complete_callback=self.on_summarization_complete)

        # 【重构】从队列中获取 loop 和 task 对象，会阻塞直到后台线程准备好
        try:
            self.backend_loop, self.backend_task = self.task_queue.get(timeout=10)
        except queue.Empty:
            messagebox.showerror("启动失败", "后台任务在10秒内未能成功初始化，任务中止。", parent=self.root)
            self.set_ui_state_idle()
            return
            
    def _start_article_summarization(self, folder_path, active_apis):
        """处理启动文章总结的逻辑"""
        self.pause_event.clear()
        
        selected_files = self.article_files_list_var.get()
        if not selected_files:
            messagebox.showerror("错误", "请在'文章设置'中选择至少一个要总结的文件。", parent=self.root)
            return
        
        output_subfolder = self.article_output_subfolder_var.get().strip()
        if not output_subfolder:
            messagebox.showerror("错误", "请指定一个用于存放产出文件的子文件夹名称。", parent=self.root)
            return

        self.log_message_gui('global', "--- 开始文章总结任务 ---")
        self.set_ui_state_running()

        # 【重构】直接创建协程，而不是task
        coro = run_article_summary_process(
                source_folder_path=folder_path,
                active_api_configs=active_apis,
                gui_log_callback=self.log_message_gui,
                gui_pause_event=self.pause_event,
                gui_stop_event=self.custom_summary_stop_event, # 可以复用
                word_counts=self.get_current_word_counts()
            )
        
        # 【重构】使用统一的辅助函数启动后台任务
        self._run_async_task_in_thread(coro)
        
        # 从队列中获取任务对象
        try:
            self.backend_loop, self.backend_task = self.task_queue.get(timeout=10)
        except queue.Empty:
            messagebox.showerror("启动失败", "后台任务在10秒内未能成功初始化，任务中止。", parent=self.root)
            self.set_ui_state_idle()
            return

    def start_splitting_process(self):
        """启动章节分割进程。"""
        if self.splitter_thread and self.splitter_thread.is_alive():
            messagebox.showwarning("任务运行中", "已有分割任务在后台运行。", parent=self.root)
            return
            
        source_file = self.source_txt_file_path_var.get()
        output_dir = self.splitter_output_dir_path_var.get()
        mode = self.splitter_mode_var.get()

        if not source_file or not output_dir:
            messagebox.showerror("错误", "请同时选择源文件和输出目录。", parent=self.root)
            return
        
        self.pause_event.clear()
        
        regex_pattern = self.regex_pattern_var.get() if mode == 'regex' else ''
        title_list = self.title_list_textbox.get("1.0", "end-1c").splitlines() if mode == 'title_list' else []

        try:
            chapters_per_file = int(self.chapters_per_file_var.get()) if mode in ['default', 'regex'] else 1
        except (ValueError, TypeError):
            chapters_per_file = 1 # 如果转换失败，则使用安全的默认值
            
        handle_volumes = self.handle_volumes_var.get() if mode == 'regex' else True

        self.log_message_gui('global', "--- 章节分割任务已启动 ---", is_progress_log=True)
        self.set_ui_state_running()

        def task_in_thread():
            try:
                success, count = split_novel_into_chapter_files(
                    source_txt_file_path=self.source_txt_file_path_var.get(),
                    output_directory_path=output_dir,
                    mode=self.splitter_mode_var.get(),
                    chapters_per_file=chapters_per_file,
                    custom_pattern=regex_pattern,
                    title_list=title_list,
                    handle_volumes=self.handle_volumes_var.get(),
                    log_callback=lambda msg, level='INFO', **kwargs: self.log_message_gui('global', msg, status=level)
                )
                # 分割任务完成的回调也应该通过GUI队列
                self.gui_queue.put((self.on_splitter_complete, (success, count)))
            except Exception as e:
                tb_info = traceback.format_exc()
                error_message = f"分割文件时发生未知错误: {e}\n{tb_info}"
                self.log_message_gui('global', error_message, status='ERROR', traceback_info=tb_info)
                self.gui_queue.put((self.on_splitter_complete, (False, 0)))

        self.splitter_thread = threading.Thread(target=task_in_thread, daemon=True)
        self.splitter_thread.start()
        self.set_ui_state_running()

    def on_splitter_complete(self, result):
        """当章节分割任务完成时的回调。"""
        self.set_ui_state_idle() # 恢复UI
        success, count = result
        if success:
            messagebox.showinfo("分割完成", f"成功将源文件分割为 {count} 个文件。", parent=self.root)
        else:
            messagebox.showerror("分割失败", "章节分割任务失败，请检查日志获取详细信息。", parent=self.root)
        self.splitter_thread = None # 清理线程引用

    def select_custom_summary_file(self):
        """为自定义总结选择源文件。"""
        paths = filedialog.askopenfilenames(
            title="选择要总结的源文件(可多选)", filetypes=[("Text files", "*.txt"), ("All files", "*.*")])
        if paths:
            # 在UI上只显示第一个文件，但变量中存储完整列表
            self.custom_source_file_path_var.set(f"{paths[0]} (及其他 {len(paths)-1} 个文件)" if len(paths) > 1 else paths[0])
            self.custom_summary_full_path_list = list(paths) # 存储完整列表
            self.log_message_gui('global', f"已选择 {len(paths)} 个自定义总结文件。")

    def _start_custom_summary_process(self):
        """【重构】启动自定义总结任务，现在使用标准的后台任务管理。"""
        if self.backend_thread and self.backend_thread.is_alive():
            messagebox.showwarning("任务运行中", "已有总结任务在后台运行。", parent=self.root)
            return

        api_config = self._validate_and_get_active_apis()
        if not api_config: return # 如果没有活动的API，直接返回

        if len(api_config) > 1:
            self.log_message_gui('global', "检测到多个活动API，自定义总结将仅使用第一个。", "WARN")
        api_to_use = api_config[0]

        source_files = getattr(self, 'custom_summary_full_path_list', [])
        if not source_files:
            messagebox.showerror("错误", "请先选择至少一个源文件。", parent=self.root)
            return
            
        user_prompt = self.custom_prompt_textbox.get("1.0", "end-1c").strip()
        if not user_prompt:
            messagebox.showerror("错误", "自定义指令不能为空。", parent=self.root)
            return
            
        self.pause_event.clear()
        self.log_message_gui('global', "--- 开始自定义总结任务 ---")
        self.set_ui_state_running()

        # 创建后台任务协程
        coro = run_custom_summary_process(
            selected_file_paths=source_files,
            user_prompt=user_prompt,
            api_config=api_to_use,
            pause_event=self.pause_event,
            log_callback=lambda msg, status='INFO': self.log_message_gui('global', msg, status=status)
        )

        # 【重构】使用新的辅助函数启动后台任务，并传入完成回调
        self._run_async_task_in_thread(coro, on_complete_callback=self.on_custom_summary_complete)

        # 从队列中获取任务对象
        try:
            self.backend_loop, self.backend_task = self.task_queue.get(timeout=10)
        except queue.Empty:
            messagebox.showerror("启动失败", "后台任务在10秒内未能成功初始化，任务中止。", parent=self.root)
            self.set_ui_state_idle()
            return

    def on_custom_summary_complete(self, result):
        """自定义总结任务完成时的回调。"""
        self.backend_thread = None
        self.backend_task = None
        self.backend_loop = None
        self.set_ui_state_idle()
        
        if isinstance(result, str) and not result.startswith("ERROR:"):
             # 将结果显示在一个新的可滚动窗口中
            self.show_result_in_window(result)
            self.log_message_gui('global', "--- 自定义总结任务成功 ---")
        else:
            self.log_message_gui('global', "--- 自定义总结任务失败或被取消 ---")
            messagebox.showwarning("任务中断", f"任务失败或被取消。详情: {result}", parent=self.root)

    def show_result_in_window(self, text_content):
        """在一个新的顶层窗口中显示结果文本。"""
        window = ctk.CTkToplevel(self.root)
        window.title("自定义总结结果")
        window.geometry("800x600")

        window.grid_rowconfigure(0, weight=1)
        window.grid_columnconfigure(0, weight=1)
        
        textbox = ctk.CTkTextbox(window, wrap="word")
        textbox.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        textbox.insert("1.0", text_content)
        textbox.configure(state="disabled")
        
        self.bind_right_click_menu(textbox)

        close_button = ctk.CTkButton(window, text="关闭", command=window.destroy)
        close_button.grid(row=1, column=0, pady=(0, 10))
        
        window.transient(self.root)
        window.grab_set()
        self.root.wait_window(window)

    def get_current_prompts_as_dict(self):
        """
        收集所有提示词编辑框的当前内容，并返回一个字典。
        """
        prompts = {}
        for key in PROMPT_CONFIGS.keys():
            # 使用 self.prompts_cache 来获取最新的内容
            prompts[key] = self.prompts_cache.get(key, "")
        return prompts

    def get_current_word_counts(self):
        """
        【修复】从UI的StringVar中获取所有当前的字数设置。
        """
        word_counts = {}
        # 同时处理小说模式和文章模式的字数变量
        all_vars = {**getattr(self, 'word_count_vars', {}), **getattr(self, 'article_word_count_vars', {})}
        for key, var in all_vars.items():
            word_counts[key] = var.get()
        return word_counts

    def _run_async_task_in_thread(self, coro, on_complete_callback=None):
        """
        【重构】在后台线程中安全地运行一个协程的统一辅助方法。
        
        Args:
            coro: 要运行的协程。
            on_complete_callback: (可选) 任务完成时在主线程中调用的回调函数。
                                  它会接收任务的返回值作为参数。
        """
        def thread_target():
            # 为新线程创建并设置新的事件循环
            self.backend_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.backend_loop)

            self.backend_task = self.backend_loop.create_task(coro)
            
            # 将 loop 和 task 对象放回队列，通知主线程任务已创建
            self.task_queue.put((self.backend_loop, self.backend_task))

            try:
                result = self.backend_loop.run_until_complete(self.backend_task)
                
                # 如果任务正常完成，将结果和回调放入队列
                if on_complete_callback:
                    self.gui_queue.put((on_complete_callback, result))

            except asyncio.CancelledError:
                # 如果任务被取消，也放入队列
                if on_complete_callback:
                    self.gui_queue.put((on_complete_callback, "cancelled"))

            except Exception as e:
                # 【核心修复】捕获所有其他异常，确保UI总能被解锁
                # 打印异常信息到控制台，方便调试
                print(f"后台任务发生未捕获的异常: {e}")
                traceback.print_exc()
                # 将异常对象自身作为结果放入队列
                if on_complete_callback:
                    self.gui_queue.put((on_complete_callback, e))
            
            finally:
                # 确保事件循环和任务引用在线程结束时被清理
                self.backend_loop.close()
                self.backend_loop = None
                self.backend_task = None
        
        # 启动后台线程
        self.backend_thread = threading.Thread(target=thread_target, daemon=True)
        self.backend_thread.start()

    def on_summarization_complete(self, result):
        """
        后台总结任务完成时的回调。
        
        Args:
            result: 任务的返回值。如果任务正常完成，则为True；如果任务被取消，则为"cancelled"；如果任务因异常而终止，则为异常对象。
        """
        self.set_ui_state_idle() # < UI 在这里解锁
        
        if result is True:
            self.log_message_gui('global', "✅ 所有总结任务已成功完成！", "SUCCESS_FINAL")
            messagebox.showinfo("任务完成", "所有总结任务已成功完成！", parent=self.root)
        elif result == "cancelled":
            self.log_message_gui('global', "任务已被用户取消。", "INFO")
        else: # result is False or an Exception object
            if isinstance(result, Exception):
                # 【核心修复】如果结果是异常对象，显示更详细的错误信息
                error_message = f"任务因发生严重错误而终止: {type(result).__name__}: {result}"
                self.log_message_gui('global', f"❌ {error_message}", "FAIL_FINAL")
                # 不再使用messagebox，因为 orchestrator 已经记录了详细日志
            else:
                # 对于返回 False 的情况（通常是可预见的失败）
                self.log_message_gui('global', "❌ 任务失败或提前终止。请检查日志获取详细信息。", "FAIL_FINAL")

        self.backend_thread = None
