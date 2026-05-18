# python/gui/main_app.py

import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
import threading
import sys
import queue
import traceback
import os
from python.gui.ui_components.main_controls import create_main_controls
from python.gui.ui_components.main_tab import create_main_tab_content, on_summary_mode_changed
# 导入所有 Mixin 模块 (使用相对导入)
from python.gui.api_manager import ApiManagerMixin
from python.gui.event_handlers import EventHandlersMixin
from python.gui.prompt_manager import PromptManagerMixin
from python.gui.ui_state_manager import UiStateManagerMixin
# 导入自定义总结管理模块 
from python.gui.custom_summary_manager import CustomSummaryManagerMixin
# 导入新的UI构建器
from python.gui.splitter_tab_ui import create_splitter_tab
# 导入文章总结面板构建器
from python.gui.article_tab_ui import create_article_summary_panel
# 导入字数设置窗口
from python.gui.word_count_window import WordCountWindow
# 导入后端模块 (使用相对导入)
# 【已修复】移除对导入错误的静默处理，现在由 run_gui.py 在启动时进行检查
from python.logic.orchestrator import run_summarization_process
from python.logic.llm_api import fetch_available_models
from python.logic.chapter_splitter import split_novel_into_chapter_files
from python.logic.article_summary_logic import run_article_summary_process


class NovelSummarizerGUI(ApiManagerMixin, EventHandlersMixin, PromptManagerMixin, UiStateManagerMixin, CustomSummaryManagerMixin):
    
    def __init__(self, root):
        self.root = root
        self.root.title("小说/文章总结辅助工具 v1.1")
        self.root.geometry("1200x900")
        
        # --- 设置窗口图标 ---
        # 注意：确保在项目根目录下有一个名为 'assets' 的文件夹，
        # 并且其中包含一个名为 'icon.ico' 的图标文件。
        try:
            # 使用 os.path.join 动态构建路径
            icon_path = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), 'assets', 'my_icon.ico')
            if not os.path.exists(icon_path):
                # 如果在打包后的路径找不到，尝试从开发环境的根目录找
                project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                icon_path = os.path.join(project_root, 'assets', 'my_icon.ico')

            if os.path.exists(icon_path):
                self.root.iconbitmap(icon_path)
            else:
                print(f"警告：找不到图标文件：{icon_path}")
        except Exception as e:
            print(f"设置图标时出错: {e}")

        # 路径管理中心
        base_path = self._get_app_base_path()
        self.config_path = os.path.join(base_path, 'config.yaml')
        self.api_config_path = os.path.join(base_path, 'api_configs.json')
        
        # 核心变量
        self.backend_thread = None
        self.splitter_thread = None
        self.pause_event = threading.Event()
        
        # 新的任务取消机制
        self.backend_task = None
        self.backend_loop = None
        self.task_queue = queue.Queue() # 用于在线程间安全地传递任务对象
        
        self.log_queue = queue.Queue()
        self.gui_queue = queue.Queue()
        self.is_closing = False # 添加一个关闭标志
        self.api_log_areas = {} # 为每个API的日志区创建一个字典
        self.word_count_window = None # 新增: 用于跟踪字数设置窗口

        # 总结模式变量
        self.summary_mode_var = ctk.StringVar(value="novel")
        self.summary_mode_var.trace_add("write", lambda *args: on_summary_mode_changed(self))

        # 大总结精细控制流程的状态变量
        self.use_fine_grained_flow_var = ctk.BooleanVar(value=False)
        self.super_summary_threshold_var = ctk.StringVar(value="5")

        # --- 小说模式: 为所有12个字数设置创建StringVar ---
        self.word_count_vars = {
            "small_summary_word_count": ctk.StringVar(value="10000-12000"),
            "small_plot_word_count": ctk.StringVar(value="10000-12000"),
            "small_char_word_count": ctk.StringVar(value="10000-12000"),
            "big_plot_word_count": ctk.StringVar(value="10000-12000"),
            "big_char_word_count": ctk.StringVar(value="10000-12000"),
            "super_plot_p1_word_count": ctk.StringVar(value="20000-25000"),
            "super_plot_p2_word_count": ctk.StringVar(value="20000-30000"),
            "super_char_p1_word_count": ctk.StringVar(value="25000"),
            "super_char_p2_word_count": ctk.StringVar(value="15000-20000"),
            "ultimate_plot_p1_word_count": ctk.StringVar(value="20000-25000"),
            "ultimate_plot_p2_word_count": ctk.StringVar(value="20000-30000"),
            "ultimate_char_p1_word_count": ctk.StringVar(value="25000"),
            "ultimate_char_p2_word_count": ctk.StringVar(value="15000-20000"),
        }

        # --- 初始化所有继承的 Mixin ---
        ApiManagerMixin.__init__(self)
        PromptManagerMixin.__init__(self)
        UiStateManagerMixin.__init__(self)
        CustomSummaryManagerMixin.__init__(self) # --- 新增: 初始化新模块 ---

        # --- 构建UI ---
        self.create_widgets()
        # 关联窗口关闭事件到我们的新函数
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.load_initial_ui_state()
        self.process_log_queue()

    def _get_app_base_path(self):
        """
        获取应用程序的根目录，确保在开发和打包后都能找到正确的路径。
        """
        # PyInstaller 会在 sys 中添加一个 'frozen' 属性。
        if getattr(sys, 'frozen', False):
            # 如果是打包后的程序 (.exe), sys.argv[0] 是指向 .exe 文件的可靠路径
            application_path = os.path.dirname(os.path.abspath(sys.argv[0]))
        else:
            # 如果是作为脚本运行，希望配置文件与 run_gui.py 在同一目录
            # __file__ 指向 main_app.py, 即 .../python/gui/main_app.py
            # 我们需要的是 .../python/
            application_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return application_path

    def clear_log_areas(self):
        """Clears all log text areas and removes API-specific tabs."""
        if hasattr(self, 'global_log_area'):
            self.global_log_area.configure(state="normal")
            self.global_log_area.delete("1.0", "end")
            self.global_log_area.configure(state="disabled")
        if hasattr(self, 'api_log_notebook') and hasattr(self, 'api_log_areas'):
            api_ids_to_remove = list(self.api_log_areas.keys())
            for api_id in api_ids_to_remove:
                display_name = self.get_api_display_name(api_id)
                try:
                    self.api_log_notebook.delete(display_name)
                except Exception as e:
                    # 以防万一标签因为一些原因不存在
                    print(f"Info: Could not delete tab '{display_name}', it might have been already removed. Error: {e}")
            
            self.api_log_areas.clear()

    def get_default_word_counts(self):
        """返回一个包含所有字数设置的硬编码默认值的字典。"""
        return {
            "small_summary_word_count": "10000-12000",
            "small_plot_word_count": "10000-12000",
            "small_char_word_count": "10000-12000",
            "big_plot_word_count": "10000-12000",
            "big_char_word_count": "10000-12000",
            "super_plot_p1_word_count": "20000-25000",
            "super_plot_p2_word_count": "20000-30000",
            "super_char_p1_word_count": "25000",
            "super_char_p2_word_count": "15000-20000",
            "ultimate_plot_p1_word_count": "20000-25000",
            "ultimate_plot_p2_word_count": "20000-30000",
            "ultimate_char_p1_word_count": "25000",
            "ultimate_char_p2_word_count": "15000-20000",
        }

    def create_widgets(self):
        """创建三段式布局: 顶部控制区, 中部主内容区, 底部常驻日志区"""
        self.root.grid_columnconfigure(0, weight=1)
        
        # --- 响应式布局策略 ---
        # 行0 (控制区) 高度固定
        self.root.grid_rowconfigure(0, weight=0)
        # 行1 (主内容区) 占据所有可用的额外垂直空间
        self.root.grid_rowconfigure(1, weight=1)
        # 行2 (全局日志) 不会主动扩展，但保证有最小高度
        self.root.grid_rowconfigure(2, weight=0)
        
        control_frame = ctk.CTkFrame(self.root)
        control_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))
        create_main_controls(self, control_frame)

        self.notebook = ctk.CTkTabview(self.root)
        self.notebook.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
        
        # --- 按照新的顺序创建选项卡 ---
        self.tab_main = self.notebook.add("主总结任务")
        self.tab_custom_summary = self.notebook.add("自定义总结")
        self.tab_splitter = self.notebook.add("章节分割工具")
        self.tab_prompts = self.notebook.add("提示词编辑器")
        self.tab_api_config = self.notebook.add("API 配置")
        self.notebook.set("主总结任务")

        # --- 为每个选项卡填充内容 ---
        create_main_tab_content(self, self.tab_main)
        self.create_custom_summary_tab(self.tab_custom_summary)
        self._create_splitter_tab_content(self.tab_splitter)
        self.create_prompt_editor_tab(self.tab_prompts)
        self.create_api_config_tab(self.tab_api_config)
        
        # --- 底部全局日志区 ---
        global_log_frame = ctk.CTkFrame(self.root, fg_color="transparent")
        global_log_frame.grid(row=2, column=0, sticky="nsew", padx=10, pady=(5, 10))
        # 保证日志区所在的行有最小高度
        self.root.grid_rowconfigure(2, minsize=200)

        # 让内部的Tabview填满这个框架
        global_log_frame.grid_rowconfigure(0, weight=1)
        global_log_frame.grid_columnconfigure(0, weight=1)

        # 全局日志现在只有一个选项卡
        self.global_log_notebook = ctk.CTkTabview(global_log_frame)
        self.global_log_notebook.grid(row=0, column=0, sticky="nsew")
        self.tab_global_log = self.global_log_notebook.add("全局日志")
        self.tab_global_log.grid_rowconfigure(0, weight=1)
        self.tab_global_log.grid_columnconfigure(0, weight=1)

        self.global_log_area = ctk.CTkTextbox(self.tab_global_log, wrap="word")
        self.global_log_area.grid(row=0, column=0, sticky="nsew")
        self.bind_right_click_menu(self.global_log_area)
        self.global_log_area.configure(state="disabled")

    def _handle_log_area_keypress(self, event: tk.Event):
        """处理日志区域的按键事件，只允许复制等无害操作。"""
        # 允许Control键组合，例如 Ctrl+C (复制) 和 Ctrl+A (全选)
        if event.state & 0x0004:  # 检查是否按下了Control键
            # 允许 'c', 'C', 'a', 'A' 键
            if event.keysym.lower() in ['c', 'a']:
                return  # 不中断事件，允许复制/全选

        # 允许通过键盘滚动 (上/下/PageUp/PageDown)
        if event.keysym in ['Up', 'Down', 'Prior', 'Next', 'Home', 'End']:
            return

        # 阻止所有其他按键的默认行为，防止编辑
        return "break"

    def open_word_count_window(self):
        """打开或激活字数配置窗口。"""
        if self.word_count_window is None or not self.word_count_window.winfo_exists():
            self.word_count_window = WordCountWindow(self.root, self.word_count_vars, self)
        else:
            self.word_count_window.lift()

    def _create_splitter_tab_content(self, parent_tab):
        """将章节分割选项卡的UI创建工作委托给专门的模块。"""
        # 这将创建所有必需的控件，并将它们分配给 self (app_instance)
        create_splitter_tab(parent_tab, self)

    def on_splitter_mode_changed(self, mode=None):
        """
        当分割器模式单选按钮更改时，处理UI更改。
        此方法由单选按钮的命令调用。
        """
        if not hasattr(self, 'splitter_dynamic_frame'):
            return

        # 清空动态框架中的所有旧小部件
        for widget in self.splitter_dynamic_frame.winfo_children():
            widget.destroy()

        # 如果没有传入模式，则从变量中获取
        if mode is None:
            mode = self.splitter_mode_var.get()

        if mode == 'regex':
            # 1. 创建用于存储正则表达式的StringVar
            self.regex_pattern_var = ctk.StringVar()
            # 2. 创建UI组件
            ctk.CTkLabel(self.splitter_dynamic_frame, text="自定义规律 (用'n'代表章节号):").grid(row=0, column=0, padx=5, pady=5, sticky="w")
            regex_entry = ctk.CTkEntry(self.splitter_dynamic_frame, textvariable=self.regex_pattern_var, width=300)
            regex_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
            self.bind_right_click_menu(regex_entry)
            
            # 启用通用选项
            self.splitter_options_frame.grid()

        elif mode == 'title_list':
            # 1. 创建UI组件
            ctk.CTkLabel(self.splitter_dynamic_frame, text="章节标题列表 (每行一个):").pack(side="top", anchor="w", padx=5)
            # 2. 创建文本框，它将直接通过 self.title_list_textbox 访问，无需StringVar
            self.title_list_textbox = ctk.CTkTextbox(self.splitter_dynamic_frame, height=150, wrap="word")
            self.title_list_textbox.pack(side="top", fill="x", expand=True, padx=5, pady=5)
            self.bind_right_click_menu(self.title_list_textbox)
            
            # 禁用通用选项
            self.splitter_options_frame.grid_remove()

        else: # default mode
            # 禁用/启用相应的通用选项
            self.splitter_options_frame.grid()

    def on_closing(self):
        """
        处理窗口关闭事件。
        如果后台任务正在运行，则取消它，并等待线程结束。
        """
        if self.is_closing:
            return  # 防止重复调用

        if self.backend_thread and self.backend_thread.is_alive():
            if messagebox.askyesno("任务运行中", "后台任务仍在运行中，退出将取消任务。确定要退出吗？", parent=self.root):
                self.is_closing = True
                
                # 使用新的取消机制
                if self.backend_loop and self.backend_task:
                    self.log_message_gui('global', "正在取消后台任务...")
                    self.backend_loop.call_soon_threadsafe(self.backend_task.cancel)
                
                # 在后台等待线程结束，避免UI卡死
                wait_thread = threading.Thread(target=self._wait_and_destroy)
                wait_thread.start()
            else:
                return # 用户选择不退出
        else:
            self._wait_and_destroy()

    def _wait_and_destroy(self):
        """等待后台线程结束后安全地销毁窗口。"""
        # 保存UI状态
        self.save_ui_state()

        if self.backend_thread and self.backend_thread.is_alive():
            self.backend_thread.join(timeout=5.0) # 等待最多5秒
        
        if self.splitter_thread and self.splitter_thread.is_alive():
            self.splitter_thread.join(timeout=5.0)
            
        self.root.destroy()

    def create_log_tab(self, api_key_name):
        """
        为给定的API密钥名创建一个新的日志选项卡和文本区域。
        """
        # 步骤 1: 检查此API的日志区域是否已存在于数据结构中，防止重复创建。
        if api_key_name in self.api_log_areas:
            return

        # 步骤 2: 如果这是第一个创建的API日志区，则移除初始的"API 进程"占位符选项卡。
        if not self.api_log_areas:
            try:
                self.api_log_notebook.delete("API 进程")
            except (tk.TclError, KeyError, ValueError):
                # 如果选项卡不存在（例如已被删除），则静默地忽略错误。
                pass

        # 步骤 3: 创建新的UI组件。
        display_name = self.get_api_display_name(api_key_name)
        
        new_tab = self.api_log_notebook.add(display_name)
        new_tab.grid_rowconfigure(0, weight=1)
        new_tab.grid_columnconfigure(0, weight=1)
        
        log_area = ctk.CTkTextbox(new_tab, wrap="word")
        log_area.grid(row=0, column=0, sticky="nsew")
        
        # 步骤 4 (核心修复): 将新创建的日志区域添加到字典中，以便后续可以找到它。
        self.api_log_areas[api_key_name] = log_area
        
        # 步骤 5: 绑定事件并设置焦点。
        self.bind_right_click_menu(log_area)
        log_area.bind("<KeyPress>", self._handle_log_area_keypress)
        self.api_log_notebook.set(display_name)

    def log_message_gui(self, source_id, message, is_progress_log=False, progress_text=None, api_id_for_log=None, traceback_info=None, status=None):
        """
        将所有日志参数打包成一个元组，并直接放入日志队列。
        """
        if api_id_for_log is None:
            api_id_for_log = source_id
        
        log_item = (source_id, message, is_progress_log, progress_text, api_id_for_log, traceback_info, status)
        self.log_queue.put(log_item)

    def process_log_queue(self):
        """
        定期处理日志队列和GUI事件队列中的消息并更新UI。
        """
        try:
            # 1. 处理日志消息
            while not self.log_queue.empty():
                log_item = self.log_queue.get_nowait()
                source_id, message, is_progress, progress_text, api_id_for_log, tb_info, status = log_item
                
                if is_progress:
                    self.update_main_progress(source_id, message, progress_text)
                
                self.log_to_specific_area(api_id_for_log, message, source_id, status, tb_info)
            
            # 2. 处理GUI回调事件
            while not self.gui_queue.empty():
                callback, result = self.gui_queue.get_nowait()
                if callback:
                    callback(result)

        except queue.Empty:
            pass  # 队列为空是正常情况，无需处理
        
        # 只要窗口不关闭，就继续调度此函数
        if not self.is_closing:
            self.root.after(100, self.process_log_queue)

    def log_to_specific_area(self, api_id_for_log, message, source_id, status=None, traceback_info=None):
        """
        将格式化后的日志消息插入到正确的GUI文本区域中。
        source_id: 'global' 或 API 的唯一标识符 (例如 'api1', 'api2')
        【重构】所有日志都会写入全局日志，API日志会额外写入其专属选项卡。
        """
        # 1. 准备要写入全局日志的消息
        # 如果来源不是全局，为其添加来源前缀，方便在全局日志中区分
        global_message = f"[{source_id}] {message}" if source_id != "global" else message

        # 2. 总是先写入全局日志区域
        if hasattr(self, 'global_log_area'):
            self.global_log_area.configure(state="normal")
            self.global_log_area.insert("end", f"{global_message}\n")
            self.global_log_area.see("end")
            self.global_log_area.configure(state="disabled")

        # 3. 如果是API专属日志，再额外写入其自己的选项卡
        if source_id != "global":
            display_name = source_id
            try:
                # 检查选项卡是否存在
                self.api_log_notebook.tab(display_name)
            except ValueError:
                # 不存在则创建
                self.create_log_tab(display_name)
            
            api_log_area = self.api_log_areas.get(display_name)
            if api_log_area:
                api_log_area.configure(state="normal")
                # 写入专属区域时，不需要再带 [api1] 这样的前缀
                api_log_area.insert("end", f"{message}\n")
                api_log_area.see("end")
                api_log_area.configure(state="disabled")

    def update_main_progress(self, source_id, message, progress_text):
        """【新增】在主界面的总进度条上显示最新状态。"""
        # --- 优先使用 progress_text ---
        if progress_text:
            self.main_progress_label.configure(text=progress_text)
        elif message and source_id == "global":
            # 如果没有专门的进度文本，则只在全局消息时更新
            self.main_progress_label.configure(text=message)
        
        # 更新特定API的状态标签
        if source_id != "global":
            entry = self._get_api_entry_by_id(source_id)
            if entry:
                label = entry.get("log_label")
                if label:
                    label.configure(text=f"状态: {message}")

    def on_backend_complete(self, success):
        """当后台小说总结任务完成时的回调（已废弃，由 on_summarization_complete 取代）。"""
        self.set_ui_state_idle()
        if success:
            messagebox.showinfo("任务完成", "小说总结任务已完成。", parent=self.root)
        else:
            messagebox.showerror("任务失败", "小说总结任务失败，请检查日志。", parent=self.root)
        self.backend_thread = None

    def on_splitter_complete(self, result):
        """当章节分割任务完成时的回调。"""
        self.set_ui_state_idle() # 恢复UI
        success, count = result
        if success:
            messagebox.showinfo("分割完成", f"成功将源文件分割为 {count} 个文件。", parent=self.root)
        else:
            messagebox.showerror("分割失败", "章节分割任务失败，请检查日志获取详细信息。", parent=self.root)
        self.splitter_thread = None # 清理线程引用

    def bind_right_click_menu(self, widget):
        # 为传入的控件绑定右键点击事件
        widget.bind("<Button-3>", lambda event: self.show_right_click_menu(event, widget))

    def show_right_click_menu(self, event, widget):
        """显示一个包含复制/剪切/粘贴/全选的右键菜单。"""
        menu = tk.Menu(widget, tearoff=0)

        # 尝试获取 customtkinter 的主题颜色
        try:
            appearance_mode = ctk.get_appearance_mode()
            
            # fg_color of the root window is the background of the window
            # It's a tuple: (light_mode_color, dark_mode_color)
            bg_colors = self.root.cget("fg_color")
            
            if appearance_mode == "Dark":
                menu_bg = bg_colors[1]  # Dark background
                menu_fg = "white"       # Light text
                active_bg = "gray30"
            else: # Light mode
                menu_bg = bg_colors[0]  # Light background
                menu_fg = "black"       # Dark text
                active_bg = "gray85"

            menu.configure(
                bg=menu_bg, 
                fg=menu_fg, 
                activebackground=active_bg, 
                activeforeground=menu_fg, # Keep text color the same on selection
                bd=0
            )
        except Exception as e:
            print(f"Error setting theme for right-click menu: {e}")
            # Fallback to default tkinter menu colors if theming fails
            pass

        is_textbox = isinstance(widget, ctk.CTkTextbox)
        is_entry = isinstance(widget, ctk.CTkEntry)

        # 【三次修复】不再显式检查state，而是让每个操作自行处理异常。
        # 这样可以确保即使用户界面状态复杂，可编辑的控件也能拥有完整的菜单。

        # 定义操作
        def copy_action():
            try:
                # 只有当有选中文本时才执行复制
                if widget.selection_get():
                    selected_text = widget.selection_get()
                    if selected_text:
                        self.root.clipboard_clear()
                        self.root.clipboard_append(selected_text)
            except tk.TclError:
                pass  # 如果没有选中文本或控件被禁用，则忽略错误

        def cut_action():
            try:
                # 只有当有选中文本时才执行
                if widget.selection_get():
                    selected_text = widget.selection_get()
                    self.root.clipboard_clear()
                    self.root.clipboard_append(selected_text)
                    # 尝试删除，如果控件被禁用，这里会抛出TclError
                    if is_textbox:
                        widget.delete("sel.first", "sel.last")
                    elif is_entry:
                        widget.delete(widget.index("sel.first"), widget.index("sel.last"))
            except tk.TclError:
                pass # 如果控件被禁用或无选中文本，则忽略

        def paste_action():
            try:
                # 尝试粘贴，如果控件被禁用，这里会抛出TclError
                pasted_text = self.root.clipboard_get()
                if pasted_text:
                    # 如果有选中的文本，先删除再粘贴
                    try:
                        if widget.selection_get():
                            if is_textbox:
                                widget.delete("sel.first", "sel.last")
                            elif is_entry:
                                widget.delete(widget.index("sel.first"), widget.index("sel.last"))
                    except tk.TclError:
                        # 没有选中文本，直接在光标处插入
                        pass
                    
                    if is_textbox:
                        widget.insert("insert", pasted_text)
                    elif is_entry:
                        widget.insert(widget.index("insert"), pasted_text)

            except tk.TclError:
                pass # 如果剪贴板为空或控件被禁用，则忽略错误
        
        def select_all_action():
            try:
                if is_textbox:
                    widget.tag_add("sel", "1.0", "end")
                elif is_entry:
                    widget.select_range(0, 'end')
                widget.focus_set()
            except tk.TclError:
                pass

        # 添加菜单项，现在总是显示所有选项
        menu.add_command(label="复制", command=copy_action, accelerator="Ctrl+C")
        menu.add_command(label="剪切", command=cut_action, accelerator="Ctrl+X")
        menu.add_command(label="粘贴", command=paste_action, accelerator="Ctrl+V")
        menu.add_separator()
        menu.add_command(label="全选", command=select_all_action, accelerator="Ctrl+A")
        
        # 显示菜单
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

# 主执行块
if __name__ == "__main__":
    try:
        if sys.platform == "win32":
            from ctypes import windll
            try:
                windll.shcore.SetProcessDpiAwareness(2)
            except:
                pass
        
        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")
        
        root = ctk.CTk()
        app = NovelSummarizerGUI(root)
        root.mainloop()
    except Exception as e:
        print("应用程序启动期间发生致命错误:")
        traceback.print_exc()
        if sys.platform == "win32":
            try:
                root_tk = tk.Tk()
                root_tk.withdraw()
                messagebox.showerror("致命错误", f"应用程序无法启动。\n\n错误信息: {e}\n\n详细信息已打印到控制台。")
            except Exception:
                pass
