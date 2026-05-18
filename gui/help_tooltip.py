# gui/help_tooltip.py

import customtkinter as ctk

class HelpTooltip(ctk.CTkToplevel):
    """
    一个自定义的、无边框的顶层窗口，用于显示帮助提示。
    它会自动定位在关联控件的旁边，并在失去焦点或按下Esc键时自动关闭。
    """
    def __init__(self, anchor_widget, text, on_close_callback=None, **kwargs):
        super().__init__(**kwargs)
        self.anchor_widget = anchor_widget
        self.text = text
        self.on_close_callback = on_close_callback

        # --- 窗口配置 ---
        # 移除窗口标题栏和边框
        self.overrideredirect(True)
        # 确保窗口总在最上层
        self.attributes("-topmost", True)

        # --- 内容创建 ---
        # 使用 CTkLabel 来显示带有自动换行功能的文本
        self.label = ctk.CTkLabel(
            self,
            text=self.text,
            corner_radius=6,
            fg_color=("gray85", "gray15"), # 设置背景色
            text_color=("gray10", "gray90"), # 设置文本颜色
            wraplength=300,  # 超过300像素宽度自动换行
            justify="left",  # 文本左对齐
            padx=10,
            pady=10
        )
        self.label.pack(expand=True, fill="both")

        # --- 绑定事件 ---
        # 当窗口失去焦点时（例如，点击了其他地方），自动销毁
        self.bind("<FocusOut>", self._on_focus_out)
        # 当在窗口上按下Esc键时，自动销毁
        self.bind("<Escape>", self._on_focus_out)

        # 在创建后立即更新一次几何信息，以获取正确的窗口尺寸
        self.update_idletasks()
        
        # 定位窗口
        self._position_window()

        # 获取焦点，以便<FocusOut>事件能够生效
        # 增加一个短暂的延迟再设置焦点，以避免UI事件的竞态条件
        self.after(10, self.focus_set)

    def destroy(self):
        """重写destroy方法，在销毁前执行回调。"""
        if self.on_close_callback:
            self.on_close_callback()
        super().destroy()

    def _on_focus_out(self, event=None):
        """当窗口失去焦点时销毁窗口。"""
        self.destroy()

    def _position_window(self):
        """计算并设置窗口相对于锚点控件的位置。"""
        anchor_x = self.anchor_widget.winfo_rootx()
        anchor_y = self.anchor_widget.winfo_rooty()
        anchor_height = self.anchor_widget.winfo_height()
        
        # 获取自身的宽度和高度
        self_width = self.winfo_width()
        self_height = self.winfo_height()

        # 默认显示在锚点控件的右侧
        pos_x = anchor_x + self.anchor_widget.winfo_width() + 5
        pos_y = anchor_y + (anchor_height - self_height) // 2
        
        # 检查是否会超出屏幕右侧
        screen_width = self.winfo_screenwidth()
        if pos_x + self_width > screen_width:
            pos_x = anchor_x - self_width - 5 # 移动到左侧

        # 检查是否会超出屏幕顶部
        if pos_y < 0:
            pos_y = 0

        # 检查是否会超出屏幕底部
        screen_height = self.winfo_screenheight()
        if pos_y + self_height > screen_height:
            pos_y = screen_height - self_height

        self.geometry(f"+{pos_x}+{pos_y}") 
