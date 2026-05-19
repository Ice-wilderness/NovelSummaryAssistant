from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional
import uuid

from .env_loader import merged_environment


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
    role: str = "user"
    content: str = ""

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PromptMessage":
        message_id = str(data.get("id") or f"message_{uuid.uuid4().hex}")
        role = str(data.get("role") or "user").strip().lower()
        if role not in PROMPT_MESSAGE_ROLES:
            raise ValueError("prompt message role must be one of: system, user, assistant")
        return cls(
            id=message_id,
            role=role,
            content=str(data.get("content", "")),
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

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PromptModule":
        module_id = str(data.get("id") or f"module_{uuid.uuid4().hex}")
        name = str(data.get("name") or module_id).strip()
        if not name:
            raise ValueError("prompt module name is required")
        content = str(data.get("content", ""))
        return cls(
            id=module_id,
            name=name,
            description=str(data.get("description", "")),
            content=content,
            default_content=str(data.get("default_content", content)),
        )

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["is_dirty"] = self.content != self.default_content
        return data


@dataclass
class PromptNode:
    id: str
    prompt_key: str
    filename: str
    title: str
    description: str = ""
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
    big_summary_batch_size: int = 5
    super_summary_threshold: int = 5
    ultimate_api_id: str = ""
    use_fine_grained_flow: bool = False
    word_counts: NovelWordCounts = field(default_factory=NovelWordCounts)

    def validate(self) -> None:
        if not self.source_folder_path:
            raise ValueError("source_folder_path is required")
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
    chapters_per_file: int = 1
    custom_pattern: str = ""
    title_list: List[str] = field(default_factory=list)
    handle_volumes: bool = True

    def validate(self) -> None:
        if not self.source_txt_file_path:
            raise ValueError("source_txt_file_path is required")
        if not self.output_directory_path:
            raise ValueError("output_directory_path is required")
        if self.mode not in {"default", "regex", "title_list"}:
            raise ValueError("mode must be one of: default, regex, title_list")
        self.chapters_per_file = _require_positive_int(
            self.chapters_per_file, "chapters_per_file"
        )
