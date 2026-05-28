from __future__ import annotations

from typing import Sequence

FileTypeSpec = tuple[str, str]


def _create_hidden_root():
    try:
        import tkinter as tk
    except ImportError as exc:
        raise RuntimeError("当前 Python 环境不可用 tkinter，无法打开系统文件选择窗口") from exc

    try:
        root = tk.Tk()
    except tk.TclError as exc:
        raise RuntimeError("当前运行环境无法打开系统文件选择窗口，请手动输入路径") from exc
    root.withdraw()
    try:
        root.attributes("-topmost", True)
    except tk.TclError:
        pass
    return root


def pick_directory(title: str = "选择文件夹") -> str:
    from tkinter import filedialog

    root = _create_hidden_root()
    try:
        return str(filedialog.askdirectory(title=title, mustexist=True) or "")
    finally:
        root.destroy()


def pick_file(
    title: str = "选择文件",
    filetypes: Sequence[FileTypeSpec] | None = None,
) -> str:
    from tkinter import filedialog

    root = _create_hidden_root()
    try:
        return str(
            filedialog.askopenfilename(
                title=title,
                filetypes=tuple(filetypes or (("文本文件", "*.txt"), ("所有文件", "*.*"))),
            )
            or ""
        )
    finally:
        root.destroy()
