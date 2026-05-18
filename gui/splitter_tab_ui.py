# python/gui/splitter_tab_ui.py

import customtkinter as ctk
from python.gui.ui_helpers import create_help_button

def create_splitter_tab(parent_tab, app_instance):
    """
    Creates all UI components for the 'Chapter Splitter' tab.
    
    Args:
        parent_tab: The parent ctk.CTkFrame (the tab itself).
        app_instance: The main NovelSummarizerGUI instance to access its methods and variables.
    """
    parent_tab.grid_columnconfigure(1, weight=1)

    # --- Mode Selection ---
    mode_frame = ctk.CTkFrame(parent_tab, fg_color="transparent")
    mode_frame.grid(row=0, column=0, columnspan=3, sticky="w", padx=10, pady=(10, 5))
    ctk.CTkLabel(mode_frame, text="分割模式:").pack(side="left", padx=(0, 10))

    app_instance.splitter_mode_var = ctk.StringVar(value="default")
    
    radio_default = ctk.CTkRadioButton(mode_frame, text="默认模式", variable=app_instance.splitter_mode_var, value="default", command=app_instance.on_splitter_mode_changed)
    radio_default.pack(side="left", padx=5)
    
    radio_regex = ctk.CTkRadioButton(mode_frame, text="自定义规律", variable=app_instance.splitter_mode_var, value="regex", command=app_instance.on_splitter_mode_changed)
    radio_regex.pack(side="left", padx=5)
    
    radio_titles = ctk.CTkRadioButton(mode_frame, text="全定义标题", variable=app_instance.splitter_mode_var, value="title_list", command=app_instance.on_splitter_mode_changed)
    radio_titles.pack(side="left", padx=5)

    # --- 帮助按钮 ---
    mode_help = (
        "选择分割小说的不同策略：\n\n"
        "· 默认模式: 自动识别如 '第X章' 或 '第123章' 等\n  常见格式的标题。\n\n"
        "· 自定义规律: 用户提供一个包含 'n' 的模板来匹配\n  特殊的章节标题格式，例如 'Chapter-n:'。\n\n"
        "· 全定义标题: 用户提供一个完整的章节标题列表，\n  程序将严格按照列表中的标题进行精确分割。"
    )
    create_help_button(mode_frame, mode_help).pack(side="left", padx=(10, 0))

    # --- Dynamic Options Frame ---
    app_instance.splitter_dynamic_frame = ctk.CTkFrame(parent_tab, fg_color="transparent")
    app_instance.splitter_dynamic_frame.grid(row=1, column=0, columnspan=3, sticky="ew", padx=10, pady=5)
    app_instance.splitter_dynamic_frame.grid_columnconfigure(1, weight=1)

    # --- Static Controls (always visible) ---
    ctk.CTkLabel(parent_tab, text="小说源文件 (.txt):").grid(row=2, column=0, padx=5, pady=10, sticky="w")
    app_instance.source_txt_file_path_var = ctk.StringVar()
    source_entry = ctk.CTkEntry(parent_tab, textvariable=app_instance.source_txt_file_path_var)
    source_entry.grid(row=2, column=1, sticky="ew", padx=5, pady=10)
    app_instance.bind_right_click_menu(source_entry)
    ctk.CTkButton(parent_tab, text="选择文件", command=app_instance.select_source_txt_file).grid(row=2, column=2, padx=5, pady=10)
    
    ctk.CTkLabel(parent_tab, text="分割后章节存放文件夹:").grid(row=3, column=0, padx=5, pady=10, sticky="w")
    app_instance.splitter_output_dir_path_var = ctk.StringVar()
    output_entry = ctk.CTkEntry(parent_tab, textvariable=app_instance.splitter_output_dir_path_var)
    output_entry.grid(row=3, column=1, sticky="ew", padx=5, pady=10)
    app_instance.bind_right_click_menu(output_entry)
    ctk.CTkButton(parent_tab, text="选择文件夹", command=app_instance.select_splitter_output_dir).grid(row=3, column=2, padx=5, pady=10)
    
    # --- Options that can be disabled ---
    app_instance.splitter_options_frame = ctk.CTkFrame(parent_tab, fg_color="transparent")
    app_instance.splitter_options_frame.grid(row=4, column=0, columnspan=3, sticky="ew", padx=5, pady=5)
    
    ctk.CTkLabel(app_instance.splitter_options_frame, text="每文件包含章节数:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
    app_instance.chapters_per_file_var = ctk.StringVar(value="20")
    app_instance.chapters_per_file_entry = ctk.CTkEntry(app_instance.splitter_options_frame, textvariable=app_instance.chapters_per_file_var, width=80)
    app_instance.chapters_per_file_entry.grid(row=0, column=1, padx=5, pady=5, sticky="w")
    app_instance.bind_right_click_menu(app_instance.chapters_per_file_entry)
    
    app_instance.handle_volumes_var = ctk.BooleanVar(value=False)
    app_instance.handle_volumes_checkbox = ctk.CTkCheckBox(app_instance.splitter_options_frame, text="自动处理分卷 (默认/自定义模式有效)", variable=app_instance.handle_volumes_var)
    app_instance.handle_volumes_checkbox.grid(row=1, column=0, columnspan=2, padx=5, pady=5, sticky="w")
    
    # --- 帮助按钮 ---
    volumes_help = (
        "此功能仅在 默认模式 和 自定义规律 模式下生效。\n\n"
        "启用后，程序会尝试检测小说中的分卷。\n"
        "它通过监测章节号的突然减小 (例如从150章突然\n"
        "变回第1章) 来判断新分卷的开始。\n\n"
        "检测到新分卷时，程序会自动调整后续文件的\n"
        "章节号命名，以实现全局的连续编号。"
    )
    create_help_button(app_instance.splitter_options_frame, volumes_help).grid(row=1, column=2, padx=(0, 5), pady=5, sticky="w")

    ctk.CTkButton(parent_tab, text="开始分割", command=app_instance.start_splitting_process).grid(row=5, column=0, columnspan=3, padx=5, pady=20)

    app_instance.on_splitter_mode_changed() 
