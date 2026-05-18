# python/gui/ui_helpers.py

import customtkinter as ctk
from python.gui.help_tooltip import HelpTooltip

_active_tooltip = None

def create_help_button(parent, help_text, size=18):
    """
    创建一个小巧的圆形问号按钮，点击时会显示一个帮助提示框。

    Args:
        parent: 将要放置此按钮的父控件 (ctk.CTkFrame)。
        help_text (str): 点击按钮时要显示的帮助文本。
        size (int): 按钮的尺寸（宽度和高度）。

    Returns:
        ctk.CTkButton: 创建好的帮助按钮实例。
    """
    global _active_tooltip
    
    def _show_tooltip():
        """
        命令函数，用于显示或隐藏提示框。
        实现了健壮的开关（toggle）和切换（switch）逻辑。
        """
        global _active_tooltip
        
        # 预先保存当前活动的工具提示，以便进行比较
        tooltip_to_close = _active_tooltip
        
        # 定义一个当任何提示框关闭时都会被调用的回调函数
        def _on_tooltip_close():
            global _active_tooltip
            _active_tooltip = None

        # 如果当前有活动的提示框，则销毁它
        if tooltip_to_close is not None:
            tooltip_to_close.destroy()

        # 核心逻辑：如果刚才关闭的提示框是属于当前点击的这个按钮的，
        # 那么只想关闭它，就在此处停止执行。
        if tooltip_to_close and tooltip_to_close.anchor_widget == help_button:
            return
        
        # 如果代码执行到这里，说明：
        # 1. 之前没有提示框是打开的。
        # 2. 或者，刚刚关闭了另一个按钮的提示框。
        # 无论哪种情况，现在都需要为当前按钮打开一个新的提示框。
        _active_tooltip = HelpTooltip(
            anchor_widget=help_button, 
            text=help_text,
            on_close_callback=_on_tooltip_close
        )

    help_button = ctk.CTkButton(
        parent,
        text="?",
        width=size,
        height=size,
        corner_radius=size // 2,  # 设置圆角半径为尺寸的一半，使其成为圆形
        command=_show_tooltip,
    )
    return help_button 
