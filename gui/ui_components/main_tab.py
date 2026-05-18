# gui/ui_components/main_tab.py

import customtkinter as ctk
from gui.article_tab_ui import create_article_summary_panel
from gui.ui_components.novel_settings_panel import build_novel_settings_panel

def create_main_tab_content(app, parent_tab):
    """Creates the content for the main summarization task tab."""
    parent_tab.grid_columnconfigure(0, weight=1)
    
    # --- 响应式布局策略 ---
    # 行0 (设置区) 占据所有可用的额外垂直空间
    parent_tab.grid_rowconfigure(0, weight=1) 
    # 行1 (API日志区) 不会主动扩展，但保证有最小高度
    parent_tab.grid_rowconfigure(1, weight=0) 

    app.settings_container = ctk.CTkScrollableFrame(parent_tab, label_text="模式设置")
    app.settings_container.grid(row=0, column=0, sticky="nsew", padx=5, pady=(5,0))
    app.settings_container.grid_columnconfigure(0, weight=1)
    
    on_summary_mode_changed(app)

    api_log_frame = ctk.CTkFrame(parent_tab, fg_color="transparent")
    api_log_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=(5, 5))
    # 保证API日志区所在的行有最小高度
    parent_tab.grid_rowconfigure(1, minsize=250)

    # 让内部的Tabview填满这个框架
    api_log_frame.grid_rowconfigure(0, weight=1)
    api_log_frame.grid_columnconfigure(0, weight=1)

    app.api_log_notebook = ctk.CTkTabview(api_log_frame)
    app.api_log_notebook.grid(row=0, column=0, sticky="nsew")

    # --- 创建一个初始的占位符选项卡来显示提示信息 ---
    # 错误的做法是直接将Label放入Tabview中，这会破坏其内部布局。
    # 正确的做法是添加一个临时的选项卡，并将Label放入其中。
    # 这个临时选项卡会在第一个真实API日志到来时被 main_app 中的逻辑自动移除。
    tab_placeholder = app.api_log_notebook.add("API 进程")
    tab_placeholder.grid_rowconfigure(0, weight=1)
    tab_placeholder.grid_columnconfigure(0, weight=1)

    # 将占位符标签放在新创建的选项卡页面中央
    app.api_log_placeholder = ctk.CTkLabel(tab_placeholder, text="API 日志将在此处显示...", text_color="gray")
    app.api_log_placeholder.grid(row=0, column=0, sticky="nsew")

def on_summary_mode_changed(app):
    """Switches the settings panel in the main task tab based on the summary mode."""
    mode = app.summary_mode_var.get()
    
    for widget in app.settings_container.winfo_children():
        widget.destroy()

    if mode == "novel":
        build_novel_settings_panel(app, app.settings_container)
    else: # mode == "article"
        create_article_summary_panel(app.settings_container, app) 
