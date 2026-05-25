from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def open_directory_with_os(
    directory: Path,
    *,
    platform: str | None = None,
    subprocess_module=subprocess,
) -> None:
    active_platform = platform if platform is not None else sys.platform
    if active_platform.startswith("win"):
        startupinfo = None
        if hasattr(subprocess_module, "STARTUPINFO"):
            startupinfo = subprocess_module.STARTUPINFO()
            startupinfo.dwFlags |= subprocess_module.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = 5
        kwargs = {"startupinfo": startupinfo} if startupinfo is not None else {}
        subprocess_module.Popen(["explorer.exe", str(directory)], **kwargs)
        return
    if active_platform == "darwin":
        subprocess_module.Popen(["open", str(directory)])
        return
    subprocess_module.Popen(["xdg-open", str(directory)])


def open_directory(
    path: str | Path,
    *,
    create: bool = False,
    opener=open_directory_with_os,
) -> None:
    directory = Path(path).expanduser().resolve(strict=False)
    if directory.exists() and not directory.is_dir():
        raise ValueError("路径不是目录")
    if create:
        directory.mkdir(parents=True, exist_ok=True)
    if not directory.exists():
        raise ValueError("目录不存在")
    opener(directory)
