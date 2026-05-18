# python/gui/article_tab_ui.py

import customtkinter as ctk

def create_article_summary_panel(parent_frame, app_instance):
    """
    Creates and populates the panel with UI widgets for the article summary mode.
    
    Args:
        parent_frame: The ctk.CTkFrame to build the UI widgets in.
        app_instance: The main NovelSummarizerGUI instance to access its variables.
    """
    # Clear any existing widgets in the frame
    for widget in parent_frame.winfo_children():
        widget.destroy()

    parent_frame.grid_columnconfigure(0, weight=1)

    # --- Word Count Settings ---
    ctk.CTkLabel(parent_frame, text="文章总结字数设置", font=ctk.CTkFont(weight="bold")).pack(pady=(10, 5))

    # Helper function to create a row with a label and an entry
    def _create_wc_entry_row(parent, label_text, var):
        row_frame = ctk.CTkFrame(parent, fg_color="transparent")
        row_frame.pack(fill="x", expand=True, padx=20, pady=4)
        
        label = ctk.CTkLabel(row_frame, text=label_text, width=200, anchor="e")
        label.pack(side="left", padx=(0, 10))
        
        entry = ctk.CTkEntry(row_frame, textvariable=var)
        entry.pack(side="left", fill="x", expand=True)
        app_instance.bind_right_click_menu(entry)

    # Use a dictionary on the app_instance to store these new vars
    if not hasattr(app_instance, 'article_word_count_vars'):
        app_instance.article_word_count_vars = {
            "section": ctk.StringVar(value="3000-4000"),
            "final": ctk.StringVar(value="8000-10000"),
        }

    _create_wc_entry_row(parent_frame, "段落总结 (section):", app_instance.article_word_count_vars["section"])
    _create_wc_entry_row(parent_frame, "最终总结 (final):", app_instance.article_word_count_vars["final"]) 
