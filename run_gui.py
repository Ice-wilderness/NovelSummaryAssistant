from __future__ import annotations

import argparse
import os
import sys
import threading
import time
import webbrowser
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _open_browser_later(url: str) -> None:
    def open_browser() -> None:
        time.sleep(1.0)
        webbrowser.open(url)

    threading.Thread(target=open_browser, daemon=True).start()


def run_webui(host: str, port: int, open_browser: bool) -> None:
    import uvicorn

    url = f"http://{host}:{port}"
    print(f"NovelSummaryAssistant WebUI: {url}")
    print("构建模式：先运行 `cd frontend && npm run build` 后可由后端托管页面。")
    print("开发模式：另开终端运行 `cd frontend && npm run dev` 使用 Vite 热更新。")
    if open_browser:
        _open_browser_later(url)
    uvicorn.run("webui_backend.api_app:app", host=host, port=port)


def run_legacy_gui() -> None:
    import customtkinter as ctk
    import yaml

    from gui.main_app import NovelSummarizerGUI

    if sys.platform == "win32":
        try:
            from ctypes import windll

            windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            pass

    ctk.set_appearance_mode("System")
    ctk.set_default_color_theme("blue")

    root = ctk.CTk()
    config_path = PROJECT_ROOT / "config.yaml"
    try:
        with config_path.open("r", encoding="utf-8-sig") as f:
            config = yaml.safe_load(f) or {}
        if config.get("window_geometry"):
            root.geometry(config["window_geometry"])
        else:
            root.geometry("1200x900")
    except (FileNotFoundError, OSError, yaml.YAMLError):
        root.geometry("1200x900")

    try:
        icon_path = PROJECT_ROOT / "my_icon.ico"
        if icon_path.exists():
            root.iconbitmap(str(icon_path))
    except Exception:
        pass

    NovelSummarizerGUI(root)
    root.mainloop()


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="NovelSummaryAssistant launcher")
    parser.add_argument("--host", default=os.environ.get("NSA_WEBUI_HOST", "127.0.0.1"))
    parser.add_argument("--port", default=int(os.environ.get("NSA_WEBUI_PORT", "8000")), type=int)
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--legacy-gui", action="store_true", help="启动旧 CustomTkinter GUI")
    args = parser.parse_args(argv)

    if args.legacy_gui:
        run_legacy_gui()
        return

    run_webui(args.host, args.port, open_browser=not args.no_browser)


if __name__ == "__main__":
    main()
