# gui/ui_components/main_controls.py

import customtkinter as ctk
from gui.ui_helpers import create_help_button
from gui.ui_components.main_tab import on_summary_mode_changed

def create_main_controls(app, parent_frame):
    """Creates the main control widgets (folder selection, mode, action buttons)."""
    parent_frame.grid_columnconfigure(1, weight=1)
    
    ctk.CTkLabel(parent_frame, text="源文件夹:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
    app.novel_folder_path = ctk.StringVar()
    folder_entry = ctk.CTkEntry(parent_frame, textvariable=app.novel_folder_path, width=400)
    folder_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
    app.bind_right_click_menu(folder_entry)
    
    ctk.CTkButton(parent_frame, text="选择文件夹", command=app.select_folder).grid(row=0, column=2, padx=5, pady=5)
    
    folder_help = """请选择包含所有待处理章节的根文件夹。

· 小说总结模式: 文件夹内应包含多个 .txt 文件，
  每个文件的文件名应包含章节号（如'第1章.txt'），
  以便程序正确排序。

· 文章总结模式: 文件夹内应包含多个 .txt 文件，
  每个文件代表一个独立的章节或部分，文件名将
  用于排序。"""
    create_help_button(parent_frame, folder_help).grid(row=0, column=3, padx=(0, 5), pady=5)

    # --- 创建一个容器来放置模式切换和高级设置 ---
    bottom_controls_frame = ctk.CTkFrame(parent_frame, fg_color="transparent")
    bottom_controls_frame.grid(row=1, column=0, columnspan=4, sticky="ew")

    mode_frame = ctk.CTkFrame(bottom_controls_frame, fg_color="transparent")
    mode_frame.pack(side="left", anchor="w", padx=5, pady=(0, 5))
    
    ctk.CTkLabel(mode_frame, text="当前任务模式:").pack(side="left", padx=(0, 10))
    
    novel_radio = ctk.CTkRadioButton(mode_frame, text="小说总结", variable=app.summary_mode_var, value="novel", command=lambda: on_summary_mode_changed(app))
    novel_radio.pack(side="left", padx=5)
    
    article_radio = ctk.CTkRadioButton(mode_frame, text="文章总结", variable=app.summary_mode_var, value="article", command=lambda: on_summary_mode_changed(app))
    article_radio.pack(side="left", padx=5)

    mode_help_text = """请根据您的文本类型选择合适的总结模式：

【小说总结模式】
这是一个复杂、多阶段的层级总结流程，专为长篇叙事作品设计。
流程包括：
1. 小总结：对每个章节文件生成初步的剧情和角色总结。
2. 大总结：将多个小总结融合成更全面的章节群总结。
3. 超级总结：整合所有大总结，形成对整部作品的核心概览。
4. 终极总结：对超级总结进行精炼和最终整理。
结果是高度结构化、深度提炼的完整小说摘要。

【文章总结模式】
这是一个相对简洁的两阶段流程，适用于非虚构类内容，如学术论文、技术文档、报告等。
流程包括：
1. 分区总结：对每个文件（代表一个章节或部分）进行独立总结。
2. 最终总结：将所有分区总结合成为一份连贯、完整的文档摘要。
此模式能快速、高效地提取非叙事文本的核心信息。"""
    create_help_button(mode_frame, mode_help_text).pack(side="left", padx=(0, 5))

    # --- 大总结流程高级设置 ---
    advanced_flow_frame = ctk.CTkFrame(bottom_controls_frame, fg_color="transparent")
    advanced_flow_frame.pack(side="left", anchor="w", padx=20, pady=(0, 5))

    def toggle_advanced_options():
        if app.use_fine_grained_flow_var.get():
            advanced_options_inner_frame.grid()
        else:
            advanced_options_inner_frame.grid_remove()

    checkbox = ctk.CTkCheckBox(
        advanced_flow_frame,
        text="启用大总结精细控制",
        variable=app.use_fine_grained_flow_var,
        command=toggle_advanced_options
    )
    checkbox.grid(row=0, column=0, sticky="w")
    
    advanced_help_text = """【大总结精细控制】

这是一个高级功能，用于处理需要大量总结的超长文本，避免超出LLM的字数限制。

【工作原理】
默认情况下，每个API会独立处理分配给它的所有章节，并将生成的"大总结"一次性合并，以生成"超级大总结"。当"大总结"数量过多时，合并后的文本可能会非常长。

启用此功能后，流程会变为：
1. **生成大总结**: 所有API首先并行完成"小总结"和"大总结"的生成。
2. **汇总与分批**: 程序会收集所有API生成的"大总结"，然后根据您设置的【超级大总结阈值】进行分批。
   例如：阈值为5，则每5个"大总结"会被分成一批。
3. **自动分发与处理**: 程序会将这些批次自动、平均地分配给所有已启用的API进行处理。每个批次都会生成一份独立的"超级总结"。

【适用场景】
当您发现"超级大总结"阶段因输入文本过长而频繁失败或返回结果质量不佳时，或者使用的api数量过少时，请使用此功能。"""
    create_help_button(advanced_flow_frame, advanced_help_text).grid(row=0, column=1, padx=(5, 0))

    # 创建一个内部框架来容纳选项，以便于隐藏/显示
    advanced_options_inner_frame = ctk.CTkFrame(advanced_flow_frame, fg_color="transparent")
    advanced_options_inner_frame.grid(row=1, column=0, columnspan=2, sticky="w", padx=(20, 0))

    # 阈值设置
    threshold_frame = ctk.CTkFrame(advanced_options_inner_frame, fg_color="transparent")
    threshold_frame.pack(fill="x", pady=(0, 5))
    ctk.CTkLabel(threshold_frame, text="超级大总结阈值:").pack(side="left", padx=(0, 5))
    threshold_entry = ctk.CTkEntry(threshold_frame, textvariable=app.super_summary_threshold_var, width=50)
    threshold_entry.pack(side="left")

    # 初始状态设置
    toggle_advanced_options()
    
    action_button_frame = ctk.CTkFrame(parent_frame)
    action_button_frame.grid(row=2, column=0,columnspan=4, padx=5, pady=5, sticky="ew")
    action_button_frame.grid_columnconfigure((0, 1, 2, 3, 4, 5, 6), weight=1)
                                             
    app.button_start = ctk.CTkButton(action_button_frame, text="开始/继续任务", command=app.start_summarization)
    app.button_start.grid(row=0, column=0, padx=5, pady=5)
    
    app.button_pause = ctk.CTkButton(action_button_frame, text="暂停", command=app.pause_summarization, state="disabled")
    app.button_pause.grid(row=0, column=1, padx=5, pady=5)

    pause_help_text = """【暂停任务】

1. 何时暂停: 暂停指令是即时生效的。当模型正在生成内容时，它会在收到下一个文本片段后立刻暂停。如果网络正在等待响应，它会在收到响应后暂停。

2. 能否修改配置: 暂停期间，您可以自由修改提示词、API配置或字数等设置。

3. 配置何时生效: 但是，当您点击"继续"时，您所做的任何更改都不会生效。任务将沿用开始时的旧配置继续运行。要想让新配置生效，您必须先"停止"任务，然后重新"开始"。

4. 如何继续: 点击"继续"后，任务会精确地从上次中断的地方无缝衔接，不会跳过或重复任何章节。"""
    create_help_button(action_button_frame, pause_help_text).grid(row=0, column=2, padx=(0, 15), pady=5)
                                             
    app.button_stop = ctk.CTkButton(action_button_frame, text="停止", command=app.stop_summarization, state="disabled")
    app.button_stop.grid(row=0, column=3, padx=5, pady=5)

    stop_help_text = """【停止任务】

1. 何时停止: 停止指令是立即生效的。无论任务进行到哪一步，包括正在进行的网络请求，都会在 0.1 秒内被中断。

2. 能否修改配置: 任务停止后，您可以随意修改任何设置。

3. 如何实现断点续接: 当您再次点击"开始/继续"时，程序将启动一个新任务。借助缓存机制，它会自动检测所有已完成的章节并跳过它们，从而有效地从上次停止的地方"断点续接"。您所做的一切新设置（如新提示词、新API等）都将在新任务中生效。程序不会从头开始，也不会重复或跳过章节。此特性在您关闭并重启程序后依然有效。"""
    create_help_button(action_button_frame, stop_help_text).grid(row=0, column=4, padx=(0, 15), pady=5)
                                             
    app.button_reset_cache = ctk.CTkButton(action_button_frame, text="重置任务缓存", command=app.confirm_reset_cache)
    app.button_reset_cache.grid(row=0, column=5, padx=5, pady=5)

    # --- 主进度标签 ---
    app.main_progress_label = ctk.CTkLabel(parent_frame, text="欢迎使用！请选择源文件夹并开始任务。", wraplength=1000, justify="left")
    app.main_progress_label.grid(row=3, column=0, columnspan=4, padx=10, pady=(5, 5), sticky="w")
