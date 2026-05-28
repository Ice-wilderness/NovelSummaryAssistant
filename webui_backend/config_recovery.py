from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict


@dataclass
class LocalConfigWarning:
    domain: str
    message: str
    path: str
    backup_path: str = ""
    backup_failed: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "domain": self.domain,
            "message": self.message,
            "path": self.path,
            "backup_path": self.backup_path,
            "backup_failed": self.backup_failed,
        }


def _next_backup_path(path: Path) -> Path:
    base = path.with_name(f"{path.name}.bak")
    if not base.exists():
        return base
    index = 1
    while True:
        candidate = path.with_name(f"{path.name}.bak.{index}")
        if not candidate.exists():
            return candidate
        index += 1


def backup_corrupted_config(
    path: str | Path,
    *,
    domain: str,
    message: str,
) -> LocalConfigWarning:
    source = Path(path)
    backup_path = _next_backup_path(source)
    try:
        shutil.copy2(source, backup_path)
    except OSError:
        return LocalConfigWarning(
            domain=domain,
            message=f"{message}；损坏文件无法备份。",
            path=str(source),
            backup_path=str(backup_path),
            backup_failed=True,
        )
    return LocalConfigWarning(
        domain=domain,
        message=f"{message}；已备份损坏文件。",
        path=str(source),
        backup_path=str(backup_path),
        backup_failed=False,
    )
