# python/gui/collapsible_frame.py

import customtkinter as ctk

class CollapsibleFrame(ctk.CTkFrame):
    """
    一个可以折叠和展开的自定义Tkinter框架。
    """
    def __init__(self, parent, title="", **kwargs):
        super().__init__(parent, **kwargs)

        self.columnconfigure(0, weight=1)
        self.title = title
        self.is_expanded = ctk.BooleanVar(value=False)

        # --- 标题和切换按钮 ---
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.grid(row=0, column=0, sticky="ew")

        self.toggle_button = ctk.CTkButton(
            self.header_frame,
            text=f"▶ {self.title}",
            command=self.toggle,
            fg_color="transparent",
            hover=False,
            text_color=("black", "white"),
            anchor="w"
        )
        self.toggle_button.pack(side="left", fill="x", expand=True)

        # --- 可折叠的内容区域 ---
        self.content_frame = ctk.CTkFrame(self, fg_color="transparent")
        # 初始状态下，内容框架不显示在grid中

    def toggle(self):
        """切换框架的展开/折叠状态。"""
        if self.is_expanded.get():
            self.content_frame.grid_forget()
            self.toggle_button.configure(text=f"▶ {self.title}")
            self.is_expanded.set(False)
        else:
            self.content_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 5))
            self.toggle_button.configure(text=f"▼ {self.title}")
            self.is_expanded.set(True)

    def get_content_frame(self):
        """返回内容框架，以便向其中添加小部件。"""
        return self.content_frame 
