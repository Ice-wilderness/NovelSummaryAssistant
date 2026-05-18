# python/gui/custom_summary_manager.py

import customtkinter as ctk
from tkinter import messagebox, filedialog
import os
import threading
import tiktoken
from python.gui.collapsible_frame import CollapsibleFrame
from python.logic.custom_summary_logic import run_custom_summary_process
from python.gui.ui_helpers import create_help_button
from python.logic.utils import read_file_content_robustly

class CustomSummaryManagerMixin:
    """
    一个Mixin类，用于封装所有与"自定义总结"功能相关的UI和逻辑。
    """
    def __init__(self):
        self.custom_summary_thread = None
        self.custom_summary_stop_event = threading.Event()
        self.material_checkboxes = {} # 用于存储复选框变量
        self._selected_custom_files = []
        self.custom_summary_source_files = ctk.StringVar(value="未选择文件")
        self.custom_summary_output_filename = ctk.StringVar(value="自定义总结.txt")
        self.custom_summary_process_enabled_var = ctk.BooleanVar(value=True)

    def create_custom_summary_tab(self, parent_tab):
        """在指定的父选项卡中创建"自定义总结"的UI组件。"""
        parent_tab.grid_columnconfigure(0, weight=1, minsize=300)
        parent_tab.grid_columnconfigure(1, weight=2)
        parent_tab.grid_rowconfigure(0, weight=1)

        # --- 左侧栏: 素材选择区 ---
        left_frame = ctk.CTkFrame(parent_tab)
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(10, 5), pady=10)
        left_frame.grid_rowconfigure(2, weight=1)
        left_frame.grid_columnconfigure(0, weight=1)

        # --- 顶部框架，用于放置按钮 ---
        top_bar_frame = ctk.CTkFrame(left_frame, fg_color="transparent")
        top_bar_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(5,5))
        top_bar_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkButton(top_bar_frame, text="从主任务加载/刷新素材", command=self._load_materials).grid(
            row=0, column=0, sticky="ew"
        )
        
        custom_summary_help = """
**自定义总结功能介绍**

此功能允许您调用任意API，使用您自己的指令，对任意组合的文本材料（原始章节、各类总结等）进行再加工。

**使用流程:**

1.  **加载素材**:
    - **推荐**: 点击【从主任务加载/刷新素材】。程序会自动扫描主任务文件夹中的原始章节和已生成的各级总结缓存，并以可折叠列表的形式分类展示。
    - **手动**: 点击【从文件夹加载其他材料】，您可以选择任意文件夹，程序会加载其中的`.txt`文件作为素材。

2.  **选择素材**: 在左侧列表中，勾选一个或多个您想作为本次总结输入的文本文件。

3.  **编写指令**: 在右侧的【自定义指令】框中，输入您希望AI执行的操作。

4.  **选择API并执行**: 从下拉菜单中选择一个API，然后点击【开始生成】。

**提示:**
- 不同的加载方式会清空当前的素材列表。
- 程序会估算所需Token，如果超过模型上限会发出警告。
"""
        create_help_button(top_bar_frame, custom_summary_help).grid(
            row=0, column=1, padx=(5, 0))

        ctk.CTkLabel(left_frame, text="素材来源", font=ctk.CTkFont(weight="bold")).grid(row=1, column=0, padx=10, pady=(10, 0), sticky="w")
        
        self.material_scroll_frame = ctk.CTkScrollableFrame(left_frame, label_text="可选择的总结或章节")
        self.material_scroll_frame.grid(row=2, column=0, sticky="nsew", padx=10, pady=(0,10))
        ctk.CTkLabel(self.material_scroll_frame, text="请点击上方按钮加载素材。").pack(pady=20)
        
        folder_button = ctk.CTkButton(left_frame, text="从文件夹加载其他材料", command=self._load_materials_from_folder)
        folder_button.grid(row=3, column=0, padx=10, pady=10)

        # --- 中间栏: 指令与生成区 ---
        middle_frame = ctk.CTkFrame(parent_tab)
        middle_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 10), pady=10)
        middle_frame.grid_rowconfigure(1, weight=1)
        
        # 将UI构建逻辑委托给一个内部方法
        self._build_custom_summary_widgets(middle_frame)

    def _build_custom_summary_widgets(self, parent_frame):
        """在一个给定的父框架内构建自定义总结所需的核心UI控件"""
        parent_frame.grid_columnconfigure(0, weight=1)
        
        # --- Prompt 输入 ---
        prompt_frame = ctk.CTkFrame(parent_frame)
        prompt_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=10, pady=(10, 5))
        prompt_frame.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(prompt_frame, text="自定义指令:").grid(row=0, column=0, sticky="w")
        self.custom_prompt_textbox = ctk.CTkTextbox(prompt_frame, height=120, wrap="word")
        self.custom_prompt_textbox.grid(row=1, column=0, sticky="nsew")
        self.bind_right_click_menu(self.custom_prompt_textbox)

        # 控制区
        control_frame = ctk.CTkFrame(parent_frame)
        control_frame.grid(row=2, column=0, columnspan=2, sticky="ew", padx=10, pady=5)
        
        self.custom_summary_api_selector_var = ctk.StringVar()
        self.custom_summary_api_selector = ctk.CTkComboBox(
            control_frame,
            variable=self.custom_summary_api_selector_var,
            state="readonly"
        )
        self.custom_summary_api_selector.pack(side="left", padx=(0,10), pady=5)

        self.custom_summary_start_button = ctk.CTkButton(control_frame, text="开始生成自定义总结", command=self._start_custom_summary_thread)
        self.custom_summary_start_button.pack(side="left", padx=10, pady=10)

        self.custom_summary_stop_button = ctk.CTkButton(control_frame, text="停止", command=self._stop_custom_summary, state="disabled")
        self.custom_summary_stop_button.pack(side="left", padx=5, pady=5)

        # 结果展示区
        result_frame = ctk.CTkFrame(parent_frame)
        result_frame.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=10, pady=5)
        result_frame.grid_rowconfigure(0, weight=1)
        result_frame.grid_columnconfigure(0, weight=1)
        
        self.custom_summary_result_textbox = ctk.CTkTextbox(result_frame, wrap="word", state="disabled")
        self.custom_summary_result_textbox.grid(row=0, column=0, sticky="nsew")
        self.bind_right_click_menu(self.custom_summary_result_textbox)

    def _update_custom_api_selector(self):
        """根据主API配置更新此页面中的API选择器。"""
        if not hasattr(self, 'api_entries') or not hasattr(self, 'custom_summary_api_selector'):
            return
            
        api_display_names = [f"API-{entry['display_index']}" for entry in self.api_entries]
        if api_display_names:
            self.custom_summary_api_selector.configure(values=api_display_names)
            # 默认选择第一个
            self.custom_summary_api_selector.set(api_display_names[0])
        else:
            self.custom_summary_api_selector.configure(values=["无可用API"])
            self.custom_summary_api_selector.set("无可用API")

    def _load_materials_from_folder(self):
        """打开文件夹对话框，加载自定义总结的材料。"""
        folder_path = filedialog.askdirectory(title="选择包含总结文件的文件夹")
        if not folder_path:
            return

        # 清空现有的复选框
        for widget in self.material_scroll_frame.winfo_children():
            widget.destroy()
        self.material_checkboxes.clear()

        # 查找所有 .txt 文件
        found_files = False
        txt_files = sorted([f for f in os.listdir(folder_path) if f.endswith('.txt')])
        
        for filename in txt_files:
            found_files = True
            var = ctk.BooleanVar(value=False)
            cb = ctk.CTkCheckBox(self.material_scroll_frame, text=filename, variable=var)
            cb.pack(anchor="w", padx=10, pady=2)
            self.material_checkboxes[os.path.join(folder_path, filename)] = var

        if not found_files:
            ctk.CTkLabel(self.material_scroll_frame, text="该文件夹中未找到 .txt 文件。").pack(pady=20)

        # 立即更新API选择器
        if hasattr(self, '_update_custom_api_selector'):
            self._update_custom_api_selector()

    def _load_materials(self):
        """加载小说文件夹下的所有可用素材并填充到左侧选择区。"""
        # 检查 self 是否有 novel_folder_path 属性，没有则提示
        if not hasattr(self, 'novel_folder_path'):
            messagebox.showerror("错误", "无法访问主任务的文件夹路径。", parent=self.root)
            return

        novel_folder = self.novel_folder_path.get()
        if not novel_folder or not os.path.isdir(novel_folder):
            messagebox.showwarning("需要文件夹", "请先在'主总结任务'选项卡中选择一个有效的小说文件夹。", parent=self.root)
            return

        # 清空现有内容
        for widget in self.material_scroll_frame.winfo_children():
            widget.destroy()
        self.material_checkboxes.clear()

        self.log_message_gui("global", "正在扫描主任务素材文件...")
        
        # 定义需要扫描的素材目录
        material_dirs = {
            "原始章节": (novel_folder, "*章*.txt"),
            "小总结-剧情": (os.path.join(novel_folder, ".summarizer_cache", "1_小总结-剧情"), "*.txt"),
            "小总结-角色": (os.path.join(novel_folder, ".summarizer_cache", "1_小总结-角色"), "*.txt"),
            "大总结-剧情": (os.path.join(novel_folder, ".summarizer_cache", "2_大总结-剧情"), "*.txt"),
            "大总结-角色": (os.path.join(novel_folder, ".summarizer_cache", "2_大总结-角色"), "*.txt"),
            "超级总结": (os.path.join(novel_folder, ".summarizer_cache", "4_超级大总结"), "*.txt"),
            "终极总结": (os.path.join(novel_folder, ".summarizer_cache", "5_终极大总结"), "*.txt"),
        }

        has_materials = False
        for category, (dir_path, pattern) in material_dirs.items():
            if os.path.isdir(dir_path):
                import glob
                # 使用 os.path.basename 作为排序键
                files = sorted(glob.glob(os.path.join(dir_path, pattern)), key=lambda f: os.path.basename(f))
                if files:
                    has_materials = True
                    collapsible_frame = CollapsibleFrame(self.material_scroll_frame, title=category)
                    collapsible_frame.pack(fill="x", expand=True, pady=2, padx=2)
                    content_frame = collapsible_frame.get_content_frame()
                    
                    for f_path in files:
                        var = ctk.BooleanVar(value=False)
                        filename = os.path.basename(f_path)
                        cb = ctk.CTkCheckBox(content_frame, text=filename, variable=var)
                        cb.pack(anchor="w", padx=10, pady=2)
                        self.material_checkboxes[f_path] = var
        
        if not has_materials:
            ctk.CTkLabel(self.material_scroll_frame, text="未找到任何素材。\n请先运行'主总结任务'生成总结，\n或确保小说文件夹中有章节文件。").pack(padx=10, pady=10)
        
        self.log_message_gui("global", "素材扫描完成。")
        # 立即更新API选择器
        if hasattr(self, '_update_custom_api_selector'):
            self._update_custom_api_selector()

    def _get_token_count(self, text, model_name="gpt-4"):
        """使用tiktoken估算文本的token数。"""
        try:
            # 获取模型的编码器
            encoding = tiktoken.encoding_for_model(model_name)
        except KeyError:
            # 如果模型未知，则使用一个通用的编码器
            encoding = tiktoken.get_encoding("cl100k_base")
        
        return len(encoding.encode(text))

    def _start_custom_summary_thread(self):
        """验证输入并启动后台线程以执行自定义总结任务。"""
        if self.custom_summary_thread and self.custom_summary_thread.is_alive():
            messagebox.showwarning("任务运行中", "已有自定义总结任务在后台运行。", parent=self.root)
            return

        # 1. 收集选择的文件
        selected_files = [path for path, var in self.material_checkboxes.items() if var.get()]
        if not selected_files:
            messagebox.showerror("需要素材", "请至少选择一个素材文件。", parent=self.root)
            return
            
        # 2. 获取用户指令
        user_prompt = self.custom_prompt_textbox.get("1.0", "end-1c").strip()
        if not user_prompt:
            messagebox.showerror("需要指令", "请输入你的自定义指令。", parent=self.root)
            return

        # 3. 获取并验证API配置
        selected_api_name = self.custom_summary_api_selector.get()
        if not selected_api_name or "无可用" in selected_api_name:
            messagebox.showerror("需要API", "无可用API或未选择API。", parent=self.root)
            return
            
        try:
            display_index_to_find = int(selected_api_name.split('-')[1])
            api_config_entry = next((entry for entry in self.api_entries if entry.get("display_index") == display_index_to_find), None)
            if not api_config_entry: raise ValueError("找不到API配置")
            # 从UI控件中同步最新的API配置值
            api_config = self._get_single_api_config_from_ui(single_entry=api_config_entry)
            if not api_config: return # 同步失败会弹窗
        except (IndexError, ValueError) as e:
            messagebox.showerror("API错误", f"无法找到或解析API配置: {selected_api_name}, {e}", parent=self.root)
            return

        # 4. 新增：Token数量检查
        try:
            self.log_message_gui("global", "正在估算总 Token 数量...")
            model_name = api_config.get("model", "gpt-4")
            # 使用一个固定的10万token作为警告阈值
            CONTEXT_LIMIT = 100000

            total_tokens = self._get_token_count(user_prompt, model_name)
            
            # 读取文件内容并累加token
            for file_path in selected_files:
                content = read_file_content_robustly(file_path)
                total_tokens += self._get_token_count(content, model_name)
            
            self.log_message_gui("global", f"预估总 Token 数: {total_tokens}")

            if total_tokens > CONTEXT_LIMIT:
                msg = (f"警告：预估的总 Token 数 ({total_tokens}) 已超过 100,000。\n\n"
                       f"这可能超出部分模型的上下文限制，继续执行可能会导致API调用失败并产生费用。\n\n"
                       f"确定要继续吗？")
                if not messagebox.askyesno("上下文超限警告", msg, icon='warning', parent=self.root):
                    self.log_message_gui("global", "任务因上下文超限警告被用户取消。")
                    return # 用户选择取消
        
        except Exception as e:
            self.log_message_gui("global", f"估算Token数时出错: {e}, 任务将继续，但可能存在风险。")


        # 5. 重置状态并启动线程
        self.custom_summary_stop_event.clear()
        self.custom_summary_result_textbox.configure(state="normal")
        self.custom_summary_result_textbox.delete("1.0", "end")
        self.custom_summary_result_textbox.configure(state="disabled")
        
        self._set_custom_summary_ui_state("running")

        self.custom_summary_thread = threading.Thread(
            target=self._custom_summary_task,
            args=(selected_files, user_prompt, api_config),
            daemon=True
        )
        self.custom_summary_thread.start()

    def _custom_summary_task(self, selected_files, user_prompt, api_config):
        """在后台线程中运行的实际任务。"""
        try:
            # 运行核心逻辑
            result = run_custom_summary_process(
                selected_file_paths=selected_files,
                user_prompt=user_prompt,
                api_config=api_config,
                pause_event=self.pause_event,  # 使用主暂停事件
                stop_event=self.custom_summary_stop_event,
                log_callback=lambda msg: self.log_message_gui('custom', msg, is_progress_log=True, progress_text="自定义总结")
            )
            
            # 任务完成，通过主线程更新UI
            if self.root:
                self.root.after(0, self.on_custom_summary_complete, result)
        finally:
            # 确保无论任务成功、失败还是被取消，UI状态都会被重置
            if self.root:
                self.root.after(0, self._set_custom_summary_ui_state, 'idle')

    def on_custom_summary_complete(self, result):
        """在主GUI线程中调用的回调函数，用于处理任务结果。"""
        # self._set_custom_summary_ui_state('idle') # 已移动到_custom_summary_task的finally块中，确保执行

        self.custom_summary_thread = None # 任务结束，清空线程引用

        if result is None:
            self.log_message_gui('custom', "任务完成，但未返回任何结果。")
            return
        
        # 如果是中止或错误信息，则不更新结果框，仅记录日志
        if result == "任务已中止。" or (isinstance(result, str) and result.startswith("API_ERROR:")):
            # 日志消息已在逻辑层或任务线程中记录，此处无需重复记录
            return

        self.custom_summary_result_textbox.configure(state="normal")
        self.custom_summary_result_textbox.delete("1.0", "end")
        self.custom_summary_result_textbox.insert("1.0", result)
        self.custom_summary_result_textbox.configure(state="disabled")

    def _stop_custom_summary(self):
        """停止当前正在运行的自定义总结任务。"""
        if self.custom_summary_thread and self.custom_summary_thread.is_alive():
            self.custom_summary_stop_event.set()
            self.log_message_gui('custom', "正在发送停止信号...")
        else:
            self.log_message_gui('custom', "没有正在运行的自定义总结任务。")

    def _set_custom_summary_ui_state(self, state):
        """根据任务状态启用或禁用UI控件。"""
        if state == 'running':
            self.custom_summary_start_button.configure(state="disabled")
            self.custom_summary_stop_button.configure(state="normal", text="停止")
            # self.custom_prompt_textbox.configure(state="disabled") # 也许不禁用更好，允许复制
            self.custom_summary_api_selector.configure(state="disabled")
        else: # "idle"
            self.custom_summary_start_button.configure(state="normal")
            self.custom_summary_stop_button.configure(state="disabled", text="停止")
            # self.custom_prompt_textbox.configure(state="normal")
            self.custom_summary_api_selector.configure(state="readonly")

    def _get_single_api_config_from_ui(self, single_entry):
        """从单个API条目的UI控件中获取当前值。"""
        try:
            config = {
                "id": single_entry["id"],
                "url": single_entry["url"].get().strip(),
                "key": single_entry["key"].get().strip(),
                "model": single_entry["model_combobox"].get().strip(),
                "stream": single_entry["stream_var"].get(),
                "temperature": float(single_entry["temperature"].get().strip() or "1.0"),
                "max_tokens": int(single_entry["max_tokens"].get().strip() or "0"),
                "timeout": int(single_entry["timeout"].get().strip() or "180"),
                "max_retries": int(single_entry["max_retries"].get().strip() or "3"),
            }
            if not all([config["url"], config["key"], config["model"]]):
                messagebox.showerror("配置不完整", f"API-{single_entry['display_index']} 的配置不完整。", parent=self.root)
                return None
            return config
        except (ValueError, TypeError) as e:
            messagebox.showerror("输入错误", f"API-{single_entry['display_index']} 的参数无效: {e}", parent=self.root)
            return None 

    def _load_materials_from_folder(self):
        """打开文件夹对话框，加载自定义总结的材料。"""
        folder_path = filedialog.askdirectory(title="选择包含总结文件的文件夹")
        if not folder_path:
            return

        # 清空现有的复选框
        for widget in self.material_scroll_frame.winfo_children():
            widget.destroy()
        self.material_checkboxes.clear()

        # 查找所有 .txt 文件
        found_files = False
        txt_files = sorted([f for f in os.listdir(folder_path) if f.endswith('.txt')])
        
        for filename in txt_files:
            found_files = True
            var = ctk.BooleanVar(value=False)
            cb = ctk.CTkCheckBox(self.material_scroll_frame, text=filename, variable=var)
            cb.pack(anchor="w", padx=10, pady=2)
            self.material_checkboxes[os.path.join(folder_path, filename)] = var

        if not found_files:
            ctk.CTkLabel(self.material_scroll_frame, text="该文件夹中未找到 .txt 文件。").pack(pady=20)

        # 立即更新API选择器
        if hasattr(self, '_update_custom_api_selector'):
            self._update_custom_api_selector() 
