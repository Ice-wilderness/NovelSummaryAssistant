# run_gui.py

import sys
import os
import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
import traceback
import yaml

# 关键步骤: 设置Python的搜索路径
# 这段代码会获取项目根目录（'python'文件夹的上一级），并将其添加到Python的搜索路径中。
# 这是为了让Python解释器能正确地将 'python' 文件夹识别为一个可导入的包。
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# --- 导入主应用 ---
# 在设置好路径后，就可以安全地从 python.gui_app 模块导入主窗口类了。
try:
    from python.gui.main_app import NovelSummarizerGUI
except ImportError as e:
    # 如果导入失败，说明文件结构有问题或之前的修复未完成，给出明确提示。
    print(f"CRITICAL: Failed to import the main application module 'NovelSummarizerGUI'.\nError: {e}")
    traceback.print_exc()
    root_tk = tk.Tk()
    root_tk.withdraw() # 隐藏主窗口
    messagebox.showerror("启动错误", f"无法加载核心模块 'python.gui.main_app'。\n\n{e}\n\n请确保项目文件结构完整。")
    sys.exit(1)


# --- 主程序执行块 ---
if __name__ == "__main__":
    """
    这是程序的总入口。
    """
    try:
        # --- 环境设置 ---
        # 在Windows上设置DPI感知，让界面在高分屏上显示更清晰
        if sys.platform == "win32":
            from ctypes import windll
            try:
                windll.shcore.SetProcessDpiAwareness(2)
            except Exception:
                # 在没有GUI环境的系统上可能会失败，忽略即可
                pass
        
        # 设置CustomTkinter的外观和主题
        ctk.set_appearance_mode("System")  # 跟随系统（暗色/亮色）
        ctk.set_default_color_theme("blue") # 默认主题颜色

        # --- 启动应用 ---
        # 1. 创建一个主窗口
        root = ctk.CTk()
        
        # --- 设置窗口图标 (兼容Nuitka 和 PyInstaller打包) ---
        # 这段代码会以更通用的方式寻找图标，确保在各种环境下都能正确加载
        try:
            # 在开发模式下，__file__ 指向 .../python/run_gui.py
            # 在 Nuitka/PyInstaller 打包后, __file__ 也指向解压后的临时目录中的 .../python/run_gui.py
            # 因此，向上两级目录 (..) 就是项目根目录或解压后的临时根目录。
            base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            icon_path = os.path.join(base_path, 'my_icon.ico')

            if os.path.exists(icon_path):
                root.iconbitmap(icon_path)
            # 后备方案：如果上述方法失败，并且是 PyInstaller 环境，则尝试其特有的 _MEIPASS 变量
            elif getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
                base_path = sys._MEIPASS
                icon_path = os.path.join(base_path, 'my_icon.ico')
                if os.path.exists(icon_path):
                    root.iconbitmap(icon_path)
        except Exception as e:
            # 如果设置图标失败，打印日志但不要让程序崩溃
            print(f"Info: Could not set window icon. Error: {e}")
        
        # 优先从配置文件加载窗口位置
        window_geometry = None
        # 使用基于脚本位置的绝对路径
        # 这确保无论从哪里运行脚本，都能找到配置文件
        script_dir = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(script_dir, 'config.yaml')
        try:
            with open(config_path, 'r', encoding='utf-8-sig') as f:
                config = yaml.safe_load(f)
                if config and 'window_geometry' in config:
                    window_geometry = config['window_geometry']
        except (FileNotFoundError, IOError, yaml.YAMLError) as e:
            # 如果文件不存在、读取失败或解析失败，则忽略，并打印一个安静的日志
            print(f"Info: Could not load window geometry from config.yaml. File might not exist yet. Error: {e}")
            pass

        if window_geometry:
            root.geometry(window_geometry)
        else:
            # 回退：窗口居中逻辑
            app_width = 1200
            app_height = 900
            screen_width = root.winfo_screenwidth()
            screen_height = root.winfo_screenheight()
            
            x = (screen_width / 2) - (app_width / 2)
            y = (screen_height / 2) - (app_height / 2)
            
            root.geometry(f'{app_width}x{app_height}+{int(x)}+{int(y)}')
        
        # 2. 将主窗口交给应用主类来构建界面
        app = NovelSummarizerGUI(root)
        # 3. 进入主事件循环，显示窗口并等待用户操作
        root.mainloop()

    except Exception as e:
        #异常捕获，捕获在应用启动过程中可能发生的任何未预料到的错误，并以弹窗形式报告。
        print("应用程序启动期间发生致命错误:")
        traceback.print_exc()
        if sys.platform == "win32":
            try:
                root_tk = tk.Tk()
                root_tk.withdraw()
                messagebox.showerror("致命错误", f"应用程序无法启动。\n\n错误信息: {e}\n\n详细信息已打印到控制台。")
            except Exception:
                pass
