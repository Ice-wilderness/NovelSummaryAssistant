import customtkinter as ctk

def build_novel_settings_panel(app, parent_frame):
    """Builds the settings panel for the novel summarization mode."""
    
    # 将字数配置移入弹窗，这里只留一个按钮
    word_count_button = ctk.CTkButton(
        parent_frame,
        text="配置各阶段字数",
        command=app.open_word_count_window
    )
    word_count_button.pack(pady=10, padx=10, fill="x")

    # 不需要自定义总结的控件，将其移除 