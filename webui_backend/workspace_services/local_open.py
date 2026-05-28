from __future__ import annotations

import base64
import subprocess
import sys
from pathlib import Path


def _powershell_single_quoted(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _windows_foreground_explorer_command(directory: Path) -> list[str]:
    path_literal = _powershell_single_quoted(str(directory))
    script = f"""
$target = [System.IO.Path]::GetFullPath({path_literal})
function Normalize-ExplorerPath([string]$value) {{
    $full = [System.IO.Path]::GetFullPath($value)
    $root = [System.IO.Path]::GetPathRoot($full)
    if ($full.Length -gt $root.Length) {{
        return $full.TrimEnd([char]92)
    }}
    return $full
}}
$targetCompare = Normalize-ExplorerPath $target
$startInfo = New-Object System.Diagnostics.ProcessStartInfo
$startInfo.FileName = 'explorer.exe'
$startInfo.Arguments = '"' + $target + '"'
$startInfo.WindowStyle = [System.Diagnostics.ProcessWindowStyle]::Normal
[System.Diagnostics.Process]::Start($startInfo) | Out-Null
Start-Sleep -Milliseconds 350
Add-Type -Namespace NovelSummaryAssistant -Name WindowApi -MemberDefinition @'
[DllImport("user32.dll")]
public static extern bool ShowWindowAsync(System.IntPtr hWnd, int nCmdShow);
[DllImport("user32.dll")]
public static extern bool SetForegroundWindow(System.IntPtr hWnd);
[DllImport("user32.dll")]
public static extern bool BringWindowToTop(System.IntPtr hWnd);
[DllImport("user32.dll")]
public static extern bool SetWindowPos(System.IntPtr hWnd, System.IntPtr hWndInsertAfter, int X, int Y, int cx, int cy, uint uFlags);
[DllImport("user32.dll")]
public static extern System.IntPtr GetForegroundWindow();
[DllImport("user32.dll")]
public static extern uint GetWindowThreadProcessId(System.IntPtr hWnd, System.IntPtr lpdwProcessId);
[DllImport("kernel32.dll")]
public static extern uint GetCurrentThreadId();
[DllImport("user32.dll")]
public static extern bool AttachThreadInput(uint idAttach, uint idAttachTo, bool fAttach);
'@
$shell = New-Object -ComObject Shell.Application
$windowHandle = [System.IntPtr]::Zero
$deadline = [DateTime]::UtcNow.AddSeconds(3)
while ([DateTime]::UtcNow -lt $deadline -and $windowHandle -eq [System.IntPtr]::Zero) {{
    foreach ($window in @($shell.Windows())) {{
        try {{
            if (-not $window.LocationURL) {{
                continue
            }}
            $localPath = [System.Uri]::UnescapeDataString(([System.Uri]$window.LocationURL).LocalPath)
            if ([System.String]::Equals((Normalize-ExplorerPath $localPath), $targetCompare, [System.StringComparison]::OrdinalIgnoreCase)) {{
                $windowHandle = [System.IntPtr]$window.HWND
                break
            }}
        }} catch {{
        }}
    }}
    if ($windowHandle -eq [System.IntPtr]::Zero) {{
        Start-Sleep -Milliseconds 100
    }}
}}
if ($windowHandle -ne [System.IntPtr]::Zero) {{
    $foreground = [NovelSummaryAssistant.WindowApi]::GetForegroundWindow()
    $currentThread = [NovelSummaryAssistant.WindowApi]::GetCurrentThreadId()
    $foregroundThread = [NovelSummaryAssistant.WindowApi]::GetWindowThreadProcessId($foreground, [System.IntPtr]::Zero)
    $attached = $false
    if ($foregroundThread -ne 0 -and $foregroundThread -ne $currentThread) {{
        $attached = [NovelSummaryAssistant.WindowApi]::AttachThreadInput($currentThread, $foregroundThread, $true)
    }}
    try {{
        [NovelSummaryAssistant.WindowApi]::ShowWindowAsync($windowHandle, 9) | Out-Null
        [NovelSummaryAssistant.WindowApi]::BringWindowToTop($windowHandle) | Out-Null
        [NovelSummaryAssistant.WindowApi]::SetForegroundWindow($windowHandle) | Out-Null
        $flags = 0x0001 -bor 0x0002 -bor 0x0040
        [NovelSummaryAssistant.WindowApi]::SetWindowPos($windowHandle, [System.IntPtr](-1), 0, 0, 0, 0, $flags) | Out-Null
        [NovelSummaryAssistant.WindowApi]::SetWindowPos($windowHandle, [System.IntPtr](-2), 0, 0, 0, 0, $flags) | Out-Null
    }} finally {{
        if ($attached) {{
            [NovelSummaryAssistant.WindowApi]::AttachThreadInput($currentThread, $foregroundThread, $false) | Out-Null
        }}
    }}
}}
""".strip()
    encoded = base64.b64encode(script.encode("utf-16-le")).decode("ascii")
    return [
        "powershell.exe",
        "-NoProfile",
        "-STA",
        "-ExecutionPolicy",
        "Bypass",
        "-EncodedCommand",
        encoded,
    ]


def _hidden_windows_startup_kwargs(subprocess_module) -> dict:
    kwargs = {}
    if hasattr(subprocess_module, "STARTUPINFO"):
        startupinfo = subprocess_module.STARTUPINFO()
        startupinfo.dwFlags |= subprocess_module.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = 0
        kwargs["startupinfo"] = startupinfo
    if hasattr(subprocess_module, "CREATE_NO_WINDOW"):
        kwargs["creationflags"] = subprocess_module.CREATE_NO_WINDOW
    return kwargs


def open_directory_with_os(
    directory: Path,
    *,
    platform: str | None = None,
    subprocess_module=subprocess,
) -> None:
    active_platform = platform if platform is not None else sys.platform
    if active_platform.startswith("win"):
        try:
            subprocess_module.Popen(
                _windows_foreground_explorer_command(directory),
                **_hidden_windows_startup_kwargs(subprocess_module),
            )
        except OSError:
            subprocess_module.Popen(["explorer.exe", str(directory)])
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
    try:
        opener(directory)
    except OSError as exc:
        raise ValueError("无法打开输出目录，请确认当前环境支持本地文件管理器") from exc
