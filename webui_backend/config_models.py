from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional
import uuid

from logic.utils import normalize_summary_output_format

from .env_loader import merged_environment
from .trigger_models import TriggerScanConfig


def _coerce_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _coerce_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _mask_secret(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 4:
        return "****"
    return f"{'*' * 8}{value[-4:]}"


@dataclass
class ApiConfig:
    id: str
    display_name: str = ""
    url: str = ""
    key: str = ""
    model: str = ""
    max_tokens: int = 4096
    temperature: float = 0.7
    stream: bool = True
    timeout: int = 180
    max_retries: int = 3
    is_active: bool = True
    key_env_var: str = ""

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ApiConfig":
        api_id = str(data.get("id") or f"api_{uuid.uuid4().hex}")
        display_name = (
            str(
                data.get("display_name")
                or data.get("api_key_name")
                or data.get("name")
                or api_id
            )
            .strip()
        )
        return cls(
            id=api_id,
            display_name=display_name,
            url=str(data.get("url", "")).strip(),
            key=str(data.get("key", "")),
            model=str(data.get("model", "")).strip(),
            max_tokens=_coerce_int(data.get("max_tokens"), 4096),
            temperature=_coerce_float(data.get("temperature"), 0.7),
            stream=bool(data.get("stream", True)),
            timeout=_coerce_int(data.get("timeout"), 180),
            max_retries=_coerce_int(data.get("max_retries"), 3),
            is_active=bool(data.get("is_active", True)),
            key_env_var=str(data.get("key_env_var") or data.get("env_key") or "").strip(),
        )

    def validate(self) -> None:
        if not self.display_name.strip():
            raise ValueError("display_name is required")
        if self.max_tokens < 0:
            raise ValueError("max_tokens must be greater than or equal to 0")
        if self.timeout <= 0:
            raise ValueError("timeout must be a positive integer")
        if self.max_retries <= 0:
            raise ValueError("max_retries must be a positive integer")

    def effective_key(self, environ: Optional[Dict[str, str]] = None) -> str:
        env = merged_environment() if environ is None else environ
        if self.key_env_var and env.get(self.key_env_var):
            return env[self.key_env_var]
        return self.key

    def to_storage_dict(self) -> Dict[str, Any]:
        self.validate()
        return asdict(self)

    def to_public_dict(self) -> Dict[str, Any]:
        data = self.to_storage_dict()
        data["key"] = _mask_secret(self.key)
        data["has_key"] = bool(self.key)
        data["has_env_key"] = bool(self.key_env_var)
        return data


@dataclass
class UserSettings:
    default_export_directory: str = ""
    minimum_output_characters: int = 0

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UserSettings":
        return cls(
            default_export_directory=str(data.get("default_export_directory", "")).strip(),
            minimum_output_characters=_coerce_int(data.get("minimum_output_characters"), 0),
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PromptTemplate:
    key: str
    filename: str
    text: str
    default_text: str = ""

    def to_dict(self) -> Dict[str, str]:
        return {
            "key": self.key,
            "filename": self.filename,
            "text": self.text,
            "default_text": self.default_text,
        }


PROMPT_MESSAGE_ROLES = {"system", "user", "assistant"}


@dataclass
class PromptMessage:
    id: str
    kind: str = "message"
    role: str = "user"
    content: str = ""
    module_id: str = ""

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PromptMessage":
        message_id = str(data.get("id") or f"message_{uuid.uuid4().hex}")
        module_id = str(data.get("module_id") or "").strip()
        kind = str(data.get("kind") or ("module" if module_id else "message")).strip().lower()
        if kind not in {"message", "module"}:
            raise ValueError("prompt message kind must be one of: message, module")
        if kind == "module" and not module_id:
            raise ValueError("prompt module message requires module_id")
        role = str(data.get("role") or "user").strip().lower()
        if role not in PROMPT_MESSAGE_ROLES:
            raise ValueError("prompt message role must be one of: system, user, assistant")
        return cls(
            id=message_id,
            kind=kind,
            role=role,
            content=str(data.get("content", "")),
            module_id=module_id,
        )

    def to_dict(self) -> Dict[str, str]:
        if self.role not in PROMPT_MESSAGE_ROLES:
            raise ValueError("prompt message role must be one of: system, user, assistant")
        return asdict(self)


@dataclass
class PromptModule:
    id: str
    name: str
    description: str = ""
    content: str = ""
    default_content: str = ""
    messages: List[PromptMessage] = field(default_factory=list)
    default_messages: List[PromptMessage] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PromptModule":
        module_id = str(data.get("id") or f"module_{uuid.uuid4().hex}")
        name = str(data.get("name") or module_id).strip()
        if not name:
            raise ValueError("prompt module name is required")
        content = str(data.get("content", ""))
        default_content = str(data.get("default_content", content))
        messages = [PromptMessage.from_dict(item) for item in data.get("messages", [])]
        default_messages = [
            PromptMessage.from_dict(item) for item in data.get("default_messages", [])
        ]
        if not messages:
            messages = [
                PromptMessage(
                    id=f"{module_id}_message_1",
                    role="user",
                    content=content,
                )
            ]
        if not default_messages:
            default_messages = [
                PromptMessage(
                    id=f"{module_id}_message_1",
                    role="user",
                    content=default_content,
                )
            ]
        return cls(
            id=module_id,
            name=name,
            description=str(data.get("description", "")),
            content=content,
            default_content=default_content,
            messages=messages,
            default_messages=default_messages,
        )

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["content"] = "\n\n".join(message.content for message in self.messages)
        data["default_content"] = "\n\n".join(
            message.content for message in self.default_messages
        )
        data["is_dirty"] = data["messages"] != data["default_messages"]
        return data


@dataclass
class PromptNode:
    id: str
    prompt_key: str
    filename: str
    title: str
    description: str = ""
    runtime_status: str = "llm_prompt"
    runtime_note: str = ""
    variables: List[str] = field(default_factory=list)
    messages: List[PromptMessage] = field(default_factory=list)
    default_messages: List[PromptMessage] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PromptNode":
        node_id = str(data.get("id") or data.get("prompt_key") or f"node_{uuid.uuid4().hex}")
        prompt_key = str(data.get("prompt_key") or node_id)
        messages = [PromptMessage.from_dict(item) for item in data.get("messages", [])]
        default_messages = [
            PromptMessage.from_dict(item) for item in data.get("default_messages", [])
        ]
        if not messages:
            messages = [PromptMessage(id=f"{node_id}_message_1")]
        if not default_messages:
            default_messages = [PromptMessage.from_dict(message.to_dict()) for message in messages]
        return cls(
            id=node_id,
            prompt_key=prompt_key,
            filename=str(data.get("filename", "")),
            title=str(data.get("title") or prompt_key),
            description=str(data.get("description", "")),
            runtime_status=str(data.get("runtime_status", "")).strip(),
            runtime_note=str(data.get("runtime_note", "")),
            variables=[str(item) for item in data.get("variables", [])],
            messages=messages,
            default_messages=default_messages,
        )

    def to_dict(self) -> Dict[str, Any]:
        messages = [message.to_dict() for message in self.messages]
        default_messages = [message.to_dict() for message in self.default_messages]
        return {
            "id": self.id,
            "prompt_key": self.prompt_key,
            "filename": self.filename,
            "title": self.title,
            "description": self.description,
            "runtime_status": self.runtime_status or "llm_prompt",
            "runtime_note": self.runtime_note,
            "variables": self.variables,
            "messages": messages,
            "default_messages": default_messages,
            "is_dirty": messages != default_messages,
        }


@dataclass
class PromptWorkflow:
    id: str
    title: str
    description: str = ""
    empty_message: str = ""
    nodes: List[PromptNode] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PromptWorkflow":
        workflow_id = str(data.get("id") or f"workflow_{uuid.uuid4().hex}")
        return cls(
            id=workflow_id,
            title=str(data.get("title") or workflow_id),
            description=str(data.get("description", "")),
            empty_message=str(data.get("empty_message", "")),
            nodes=[PromptNode.from_dict(item) for item in data.get("nodes", [])],
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "empty_message": self.empty_message,
            "nodes": [node.to_dict() for node in self.nodes],
        }


@dataclass
class WorkflowPromptConfig:
    version: int = 1
    source: str = "defaults"
    workflows: List[PromptWorkflow] = field(default_factory=list)
    modules: List[PromptModule] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkflowPromptConfig":
        return cls(
            version=_coerce_int(data.get("version"), 1),
            source=str(data.get("source") or "structured"),
            workflows=[PromptWorkflow.from_dict(item) for item in data.get("workflows", [])],
            modules=[PromptModule.from_dict(item) for item in data.get("modules", [])],
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": self.version,
            "source": self.source,
            "workflows": [workflow.to_dict() for workflow in self.workflows],
            "modules": [module.to_dict() for module in self.modules],
        }


@dataclass
class NovelWordCounts:
    small_summary_word_count: str = "10000-12000"
    small_plot_word_count: str = "10000-12000"
    small_char_word_count: str = "10000-12000"
    big_plot_word_count: str = "10000-12000"
    big_char_word_count: str = "10000-12000"
    super_plot_p1_word_count: str = "20000-25000"
    super_plot_p2_word_count: str = "20000-30000"
    super_char_p1_word_count: str = "25000"
    super_char_p2_word_count: str = "15000-20000"
    ultimate_plot_p1_word_count: str = "20000-25000"
    ultimate_plot_p2_word_count: str = "20000-30000"
    ultimate_char_p1_word_count: str = "25000"
    ultimate_char_p2_word_count: str = "15000-20000"

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "NovelWordCounts":
        defaults = cls()
        values = asdict(defaults)
        values.update({key: str(value) for key, value in data.items() if key in values})
        return cls(**values)

    def to_dict(self) -> Dict[str, str]:
        return asdict(self)


@dataclass
class ArticleWordCounts:
    section: str = "3000-4000"
    final: str = "8000-10000"

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ArticleWordCounts":
        defaults = cls()
        return cls(
            section=str(data.get("section", defaults.section)),
            final=str(data.get("final", defaults.final)),
        )

    def to_dict(self) -> Dict[str, str]:
        return asdict(self)


def _require_positive_int(value: Any, field_name: str) -> int:
    parsed = _coerce_int(value, 0)
    if parsed <= 0:
        raise ValueError(f"{field_name} must be a positive integer")
    return parsed


@dataclass
class NovelSummaryRequest:
    source_folder_path: str
    active_api_ids: List[str] = field(default_factory=list)
    summary_batch_size: int = 10
    summary_output_format: str = "md"
    big_summary_batch_size: int = 5
    super_summary_threshold: int = 10
    ultimate_api_id: str = ""
    use_fine_grained_flow: bool = False
    stop_after_small_summary: bool = False
    word_counts: NovelWordCounts = field(default_factory=NovelWordCounts)
    project_name: str = ""
    project_slug: str = ""
    uploaded_file_ids: List[str] = field(default_factory=list)
    custom_output_directory_path: str = ""
    managed_output_directory_path: str = ""

    def validate(self) -> None:
        if not self.source_folder_path:
            raise ValueError("source_folder_path is required")
        self.summary_batch_size = _require_positive_int(
            self.summary_batch_size, "summary_batch_size"
        )
        self.summary_output_format = normalize_summary_output_format(
            self.summary_output_format
        )
        self.big_summary_batch_size = _require_positive_int(
            self.big_summary_batch_size, "big_summary_batch_size"
        )
        self.super_summary_threshold = _require_positive_int(
            self.super_summary_threshold, "super_summary_threshold"
        )


@dataclass
class ArticleSummaryRequest:
    source_folder_path: str
    selected_files: List[str] = field(default_factory=list)
    output_subfolder: str = ""
    word_counts: ArticleWordCounts = field(default_factory=ArticleWordCounts)
    project_name: str = ""
    project_slug: str = ""
    uploaded_file_ids: List[str] = field(default_factory=list)
    custom_output_directory_path: str = ""
    managed_output_directory_path: str = ""

    def validate(self) -> None:
        if not self.source_folder_path:
            raise ValueError("source_folder_path is required")
        if not self.selected_files:
            raise ValueError("selected_files is required")


@dataclass
class CustomSummaryRequest:
    selected_file_paths: List[str]
    user_prompt: str
    api_id: str
    project_name: str = ""
    project_slug: str = ""
    uploaded_file_ids: List[str] = field(default_factory=list)
    custom_output_directory_path: str = ""
    managed_output_directory_path: str = ""

    def validate(self) -> None:
        if not self.selected_file_paths:
            raise ValueError("selected_file_paths is required")
        if not self.user_prompt.strip():
            raise ValueError("user_prompt is required")
        if not self.api_id:
            raise ValueError("api_id is required")


@dataclass
class SplitterRequest:
    source_txt_file_path: str
    output_directory_path: str
    mode: str = "default"
    custom_pattern: str = ""
    title_list: List[str] = field(default_factory=list)
    handle_volumes: bool = True
    context: str = "chapter_split"
    pattern_config_id: str = ""
    project_name: str = ""
    project_slug: str = ""
    uploaded_file_ids: List[str] = field(default_factory=list)
    custom_output_directory_path: str = ""
    managed_output_directory_path: str = ""

    def validate(self) -> None:
        if not self.source_txt_file_path:
            raise ValueError("source_txt_file_path is required")
        if not self.output_directory_path:
            raise ValueError("output_directory_path is required")
        if self.mode not in {"default", "regex", "title_list"}:
            raise ValueError("mode must be one of: default, regex, title_list")


@dataclass
class TriggerScanRequest:
    project_slug: str
    source_folder_path: str
    project_output_directory_path: str
    profile_id: str
    scan_config: TriggerScanConfig = field(default_factory=TriggerScanConfig)
    project_name: str = ""
    custom_output_directory_path: str = ""
    managed_output_directory_path: str = ""
    resume_from_report_id: str = ""

    def validate(self) -> None:
        if not self.project_slug:
            raise ValueError("project_slug is required")
        if not self.source_folder_path:
            raise ValueError("source_folder_path is required")
        if not self.project_output_directory_path:
            raise ValueError("project_output_directory_path is required")
        if not self.profile_id:
            raise ValueError("profile_id is required")
        self.scan_config.validate()
        if not self.scan_config.scan_api_ids:
            raise ValueError("scan_api_ids is required")


# ── 正则配置模块 ──────────────────────────────────────────────

PATTERN_REGEX_MODES = {"raw", "simple"}


def _coerce_pattern_regex_mode(value: str) -> str:
    normalized = str(value or "raw").strip().lower()
    return normalized if normalized in PATTERN_REGEX_MODES else "raw"


@dataclass
class PatternConfig:
    id: str
    name: str = ""
    regex_mode: str = "raw"
    pattern: str = ""
    description: str = ""
    is_preset: bool = False
    created_at: float = field(default_factory=lambda: time.time())
    updated_at: float = field(default_factory=lambda: time.time())

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PatternConfig":
        now = time.time()
        return cls(
            id=str(data.get("id") or f"pattern_{uuid.uuid4().hex}"),
            name=str(data.get("name", "")).strip(),
            regex_mode=_coerce_pattern_regex_mode(data.get("regex_mode", "raw")),
            pattern=str(data.get("pattern", "")),
            description=str(data.get("description", "")),
            is_preset=bool(data.get("is_preset", False)),
            created_at=float(data.get("created_at", now)),
            updated_at=float(data.get("updated_at", now)),
        )

    def validate(self) -> None:
        if not self.name.strip():
            raise ValueError("正则配置名称不能为空")
        if not self.pattern.strip():
            raise ValueError("正则表达式不能为空")
        if self.regex_mode not in PATTERN_REGEX_MODES:
            raise ValueError(f"regex_mode 必须为 {' 或 '.join(sorted(PATTERN_REGEX_MODES))}")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "regex_mode": self.regex_mode,
            "pattern": self.pattern,
            "description": self.description,
            "is_preset": self.is_preset,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    def to_export_dict(self) -> Dict[str, Any]:
        """导出时不包含内部 id 和时间戳，方便跨环境分享。"""
        return {
            "name": self.name,
            "regex_mode": self.regex_mode,
            "pattern": self.pattern,
            "description": self.description,
        }

    def touch(self) -> None:
        self.updated_at = time.time()


@dataclass
class PatternConfigListResponse:
    items: List[PatternConfig] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {"items": [item.to_dict() for item in self.items]}


@dataclass
class ChapterPreviewRequest:
    file_content: str = ""
    mode: str = "default"
    pattern_config_id: str = ""
    title_list: List[str] = field(default_factory=list)
    handle_volumes: bool = True

    def validate(self) -> None:
        if not self.file_content:
            raise ValueError("源文件内容不能为空")
        if self.mode not in {"default", "regex", "title_list"}:
            raise ValueError("mode 必须为 default、regex 或 title_list")
        if self.mode == "regex" and not self.pattern_config_id:
            raise ValueError("正则模式需要提供 pattern_config_id")


@dataclass
class ChapterPreviewItem:
    index: int = 0
    title: str = ""
    line_number: int = 0
    word_count: int = 0
    matched: bool | None = None

    def to_dict(self) -> Dict[str, Any]:
        data = {
            "index": self.index,
            "title": self.title,
            "line_number": self.line_number,
            "word_count": self.word_count,
        }
        if self.matched is not None:
            data["matched"] = self.matched
        return data


@dataclass
class SplitPreviewResult:
    chapter_count: int = 0
    chapters: List[ChapterPreviewItem] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chapter_count": self.chapter_count,
            "chapters": [item.to_dict() for item in self.chapters],
        }
