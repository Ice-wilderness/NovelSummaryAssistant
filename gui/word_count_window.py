import customtkinter as ctk
from tkinter import messagebox

class WordCountWindow(ctk.CTkToplevel):
    def __init__(self, master, word_count_vars, app_instance):
        super().__init__(master)
        self.app = app_instance
        self.word_count_vars = word_count_vars

        self.title("配置各阶段字数")
        self.geometry("750x550")
        self.resizable(False, False)
        self.transient(master)
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.grab_set()

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        main_frame = ctk.CTkScrollableFrame(self, label_text="字数详细配置")
        main_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        main_frame.grid_columnconfigure((0, 2), weight=1)
        main_frame.grid_columnconfigure(1, weight=2)

        # 定义UI布局和对应的变量名
        layout = {
            "小总结": [("剧情", "small_plot_word_count"), ("角色", "small_char_word_count")],
            "大总结": [("剧情", "big_plot_word_count"), ("角色", "big_char_word_count")],
            "超级总结 (上)": [("剧情", "super_plot_p1_word_count"), ("角色", "super_char_p1_word_count")],
            "超级总结 (下)": [("剧情", "super_plot_p2_word_count"), ("角色", "super_char_p2_word_count")],
            "终极总结 (上)": [("剧情", "ultimate_plot_p1_word_count"), ("角色", "ultimate_char_p1_word_count")],
            "终极总结 (下)": [("剧情", "ultimate_plot_p2_word_count"), ("角色", "ultimate_char_p2_word_count")]
        }
        
        row = 0
        for section_title, items in layout.items():
            ctk.CTkLabel(main_frame, text=f"--- {section_title} ---", font=ctk.CTkFont(weight="bold")).grid(
                row=row, column=0, columnspan=3, pady=(10, 5), sticky="ew")
            row += 1
            for i, (label_text, var_key) in enumerate(items):
                col = 0
                ctk.CTkLabel(main_frame, text=f"{label_text}总结字数:").grid(row=row, column=col, padx=(10, 5), pady=5, sticky="e")
                col += 1
                entry = ctk.CTkEntry(main_frame, textvariable=self.word_count_vars[var_key])
                entry.grid(row=row, column=col, padx=5, pady=5, sticky="ew")
                self.app.bind_right_click_menu(entry)
                col += 1
                help_text = "推荐值: 10000-12000"
                if "super" in var_key: help_text = "推荐值: 15000-25000"
                if "ultimate" in var_key: help_text = "推荐值: 20000-30000"
                ctk.CTkLabel(main_frame, text=help_text, text_color="gray").grid(row=row, column=col, padx=5, pady=5, sticky="w")
                row += 1

        button_frame = ctk.CTkFrame(self)
        button_frame.grid(row=1, column=0, padx=10, pady=10, sticky="ew")
        button_frame.grid_columnconfigure((0, 1, 2), weight=1)

        save_button = ctk.CTkButton(button_frame, text="保存设置", command=self.save_settings)
        save_button.grid(row=0, column=0, padx=5, pady=5)

        restore_button = ctk.CTkButton(button_frame, text="恢复默认", command=self.restore_defaults)
        restore_button.grid(row=0, column=1, padx=5, pady=5)

        close_button = ctk.CTkButton(button_frame, text="关闭", command=self.on_close)
        close_button.grid(row=0, column=2, padx=5, pady=5)

    def save_settings(self):
        """保存当前设置到配置文件"""
        self.app.save_ui_state()
        messagebox.showinfo("已保存", "字数设置已成功保存。", parent=self)

    def restore_defaults(self):
        """恢复默认设置"""
        defaults = self.app.get_default_word_counts()
        for key, var in self.word_count_vars.items():
            if key in defaults:
                var.set(defaults[key])
        messagebox.showinfo("已恢复", "已恢复为默认字数设置。点击“保存设置”以持久化。", parent=self)

    def on_close(self):
        """处理窗口关闭事件"""
        self.app.word_count_window = None # 通知主应用窗口已关闭
        self.grab_release()
        self.destroy() 
