from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional
import uuid


MATCHING_POLICIES = {"explicit_only", "explicit_or_strongly_implied", "any_hint"}
SCAN_MODES = {"precise"}
LEGACY_REPORT_SCAN_MODES = {"hybrid", "precise"}
REPORT_STATUSES = {"pending", "running", "completed", "failed", "cancelled"}
REVIEW_STATUSES = {"unreviewed", "confirmed", "false_positive"}

DEFAULT_SCAN_MODE = "precise"
DEFAULT_MIN_CONFIDENCE = 0.65
DEFAULT_KEEP_LOW_CONFIDENCE = True
DEFAULT_MINIMUM_OUTPUT_CHARACTERS = 0
DEFAULT_PRECISE_CHAPTER_BATCH_SIZE = 5
DEFAULT_VERIFICATION_CHAPTER_BATCH_SIZE = 5
DEFAULT_MAX_QUOTE_CHARS = 80
DEFAULT_GENERATE_SKIP_ADVICE = True


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


def _string_list(value: Any) -> List[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def _require_non_empty(value: str, field_name: str) -> None:
    if not value.strip():
        raise ValueError(f"{field_name} is required")


def _validate_confidence(value: float, field_name: str = "confidence") -> None:
    if value < 0 or value > 1:
        raise ValueError(f"{field_name} must be between 0 and 1")


def _validate_severity(value: int, field_name: str = "severity") -> None:
    if value < 1 or value > 5:
        raise ValueError(f"{field_name} must be an integer from 1 through 5")


def _normalize_matching_policy(value: Any) -> str:
    policy = str(value or "explicit_or_strongly_implied").strip()
    if policy not in MATCHING_POLICIES:
        raise ValueError(
            "matching_policy must be one of: explicit_only, "
            "explicit_or_strongly_implied, any_hint"
        )
    return policy


@dataclass
class TriggerRuleGroup:
    id: str
    name: str
    rules: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TriggerRuleGroup":
        group_id = str(data.get("id") or f"group_{uuid.uuid4().hex}")
        return cls(
            id=group_id,
            name=str(data.get("name") or group_id).strip(),
            rules=_string_list(data.get("rules", [])),
        )

    def validate(self) -> None:
        _require_non_empty(self.id, "group id")
        _require_non_empty(self.name, "group name")

    def to_dict(self) -> Dict[str, Any]:
        self.validate()
        return asdict(self)


@dataclass
class TriggerRule:
    id: str
    name: str
    group_id: str
    description: str = ""
    matching_policy: str = "explicit_or_strongly_implied"
    severity_threshold: int = 2
    enabled: bool = True
    examples: List[str] = field(default_factory=list)
    negative_examples: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TriggerRule":
        rule_id = str(data.get("id") or f"rule_{uuid.uuid4().hex}")
        return cls(
            id=rule_id,
            name=str(data.get("name") or rule_id).strip(),
            group_id=str(data.get("group_id") or "").strip(),
            description=str(data.get("description", "")),
            matching_policy=_normalize_matching_policy(data.get("matching_policy")),
            severity_threshold=_coerce_int(data.get("severity_threshold"), 2),
            enabled=bool(data.get("enabled", True)),
            examples=_string_list(data.get("examples", [])),
            negative_examples=_string_list(data.get("negative_examples", [])),
        )

    def validate(self) -> None:
        _require_non_empty(self.id, "rule id")
        _require_non_empty(self.name, "rule name")
        _require_non_empty(self.group_id, "rule group_id")
        self.matching_policy = _normalize_matching_policy(self.matching_policy)
        _validate_severity(self.severity_threshold, "severity_threshold")

    def to_dict(self) -> Dict[str, Any]:
        self.validate()
        return asdict(self)


@dataclass
class TriggerProfile:
    id: str
    name: str
    description: str = ""
    created_at: float = 0
    updated_at: float = 0
    rule_groups: List[TriggerRuleGroup] = field(default_factory=list)
    rules: List[TriggerRule] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TriggerProfile":
        profile_id = str(data.get("id") or f"profile_{uuid.uuid4().hex}")
        return cls(
            id=profile_id,
            name=str(data.get("name") or profile_id).strip(),
            description=str(data.get("description", "")),
            created_at=_coerce_float(data.get("created_at"), 0),
            updated_at=_coerce_float(data.get("updated_at"), 0),
            rule_groups=[
                TriggerRuleGroup.from_dict(item) for item in data.get("rule_groups", [])
            ],
            rules=[TriggerRule.from_dict(item) for item in data.get("rules", [])],
        )

    def validate(self) -> None:
        _require_non_empty(self.id, "profile id")
        _require_non_empty(self.name, "profile name")
        group_ids = {group.id for group in self.rule_groups}
        for group in self.rule_groups:
            group.validate()
        for rule in self.rules:
            rule.validate()
            if group_ids and rule.group_id not in group_ids:
                raise ValueError(f"rule group_id does not exist: {rule.group_id}")

    def to_dict(self) -> Dict[str, Any]:
        self.validate()
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "rule_groups": [group.to_dict() for group in self.rule_groups],
            "rules": [rule.to_dict() for rule in self.rules],
        }


@dataclass
class ScanRange:
    start: int = 1
    end: Optional[int] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ScanRange":
        end_value = data.get("end")
        return cls(
            start=_coerce_int(data.get("start"), 1),
            end=None if end_value is None or end_value == "" else _coerce_int(end_value, 0),
        )

    def validate(self) -> None:
        if self.start <= 0:
            raise ValueError("scan range start must be a positive integer")
        if self.end is not None:
            if self.end <= 0:
                raise ValueError("scan range end must be a positive integer")
            if self.end < self.start:
                raise ValueError("scan range end must be greater than or equal to start")

    def to_dict(self) -> Dict[str, Any]:
        self.validate()
        return {"start": self.start, "end": self.end}


@dataclass
class TriggerScanConfig:
    scan_mode: str = DEFAULT_SCAN_MODE
    scan_range: ScanRange = field(default_factory=ScanRange)
    scan_api_ids: List[str] = field(default_factory=list)
    min_confidence: float = DEFAULT_MIN_CONFIDENCE
    keep_low_confidence: bool = DEFAULT_KEEP_LOW_CONFIDENCE
    verification_enabled: bool = True
    verification_api_id: str = ""
    precise_chapter_batch_size: int = DEFAULT_PRECISE_CHAPTER_BATCH_SIZE
    verification_chapter_batch_size: int = DEFAULT_VERIFICATION_CHAPTER_BATCH_SIZE
    max_quote_chars: int = DEFAULT_MAX_QUOTE_CHARS
    generate_skip_advice: bool = DEFAULT_GENERATE_SKIP_ADVICE
    minimum_output_characters: int = DEFAULT_MINIMUM_OUTPUT_CHARACTERS

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TriggerScanConfig":
        scan_mode = str(data.get("scan_mode") or DEFAULT_SCAN_MODE).strip()
        return cls(
            scan_mode=scan_mode,
            scan_range=ScanRange.from_dict(data.get("scan_range", {}) or {}),
            scan_api_ids=_string_list(data.get("scan_api_ids", [])),
            min_confidence=_coerce_float(data.get("min_confidence"), DEFAULT_MIN_CONFIDENCE),
            keep_low_confidence=bool(
                data.get("keep_low_confidence", DEFAULT_KEEP_LOW_CONFIDENCE)
            ),
            verification_enabled=bool(
                data.get("verification_enabled", True)
            ),
            verification_api_id=str(data.get("verification_api_id", "")).strip(),
            precise_chapter_batch_size=_coerce_int(
                data.get("precise_chapter_batch_size"),
                DEFAULT_PRECISE_CHAPTER_BATCH_SIZE,
            ),
            verification_chapter_batch_size=_coerce_int(
                data.get("verification_chapter_batch_size"),
                DEFAULT_VERIFICATION_CHAPTER_BATCH_SIZE,
            ),
            max_quote_chars=_coerce_int(
                data.get("max_quote_chars"), DEFAULT_MAX_QUOTE_CHARS
            ),
            generate_skip_advice=bool(
                data.get("generate_skip_advice", DEFAULT_GENERATE_SKIP_ADVICE)
            ),
            minimum_output_characters=_coerce_int(
                data.get("minimum_output_characters"), DEFAULT_MINIMUM_OUTPUT_CHARACTERS
            ),
        )

    def validate(self) -> None:
        if self.scan_mode not in SCAN_MODES:
            raise ValueError("scan_mode must be precise; hybrid scan mode has been removed")
        self.scan_range.validate()
        _validate_confidence(self.min_confidence, "min_confidence")
        if self.precise_chapter_batch_size <= 0:
            raise ValueError("precise_chapter_batch_size must be a positive integer")
        if self.verification_chapter_batch_size <= 0:
            raise ValueError("verification_chapter_batch_size must be a positive integer")
        if self.max_quote_chars <= 0:
            raise ValueError("max_quote_chars must be a positive integer")
        if self.minimum_output_characters < 0:
            raise ValueError("minimum_output_characters must be greater than or equal to 0")

    def to_dict(self) -> Dict[str, Any]:
        self.validate()
        return {
            "scan_mode": self.scan_mode,
            "scan_range": self.scan_range.to_dict(),
            "scan_api_ids": self.scan_api_ids,
            "min_confidence": self.min_confidence,
            "keep_low_confidence": self.keep_low_confidence,
            "verification_enabled": self.verification_enabled,
            "verification_api_id": self.verification_api_id,
            "precise_chapter_batch_size": self.precise_chapter_batch_size,
            "verification_chapter_batch_size": self.verification_chapter_batch_size,
            "max_quote_chars": self.max_quote_chars,
            "generate_skip_advice": self.generate_skip_advice,
            "minimum_output_characters": self.minimum_output_characters,
        }


@dataclass
class SpoilerDescription:
    description: str = ""
    skip_advice: str = ""
    evidence_quote: str = ""

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SpoilerDescription":
        return cls(
            description=str(data.get("description", "")),
            skip_advice=str(data.get("skip_advice", "")),
            evidence_quote=str(data.get("evidence_quote", "")),
        )

    def to_dict(self) -> Dict[str, str]:
        return asdict(self)


@dataclass
class SpoilerLevels:
    low: SpoilerDescription = field(default_factory=SpoilerDescription)
    standard: SpoilerDescription = field(default_factory=SpoilerDescription)
    detailed: SpoilerDescription = field(default_factory=SpoilerDescription)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SpoilerLevels":
        return cls(
            low=SpoilerDescription.from_dict(data.get("low", {}) or {}),
            standard=SpoilerDescription.from_dict(data.get("standard", {}) or {}),
            detailed=SpoilerDescription.from_dict(data.get("detailed", {}) or {}),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "low": self.low.to_dict(),
            "standard": self.standard.to_dict(),
            "detailed": self.detailed.to_dict(),
        }


@dataclass
class ScanFinding:
    finding_id: str
    rule_id: str
    rule_name: str
    chapter_file: str
    chapter_title: str = ""
    paragraph_ids: List[str] = field(default_factory=list)
    severity: int = 1
    confidence: float = 0
    is_main_plot: bool = False
    review_status: str = "unreviewed"
    user_note: str = ""
    in_skip_list: bool = False
    spoiler_levels: SpoilerLevels = field(default_factory=SpoilerLevels)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ScanFinding":
        finding_id = str(data.get("finding_id") or f"finding_{uuid.uuid4().hex}")
        return cls(
            finding_id=finding_id,
            rule_id=str(data.get("rule_id", "")).strip(),
            rule_name=str(data.get("rule_name", "")).strip(),
            chapter_file=str(data.get("chapter_file", "")).strip(),
            chapter_title=str(data.get("chapter_title", "")),
            paragraph_ids=_string_list(data.get("paragraph_ids", [])),
            severity=_coerce_int(data.get("severity"), 1),
            confidence=_coerce_float(data.get("confidence"), 0),
            is_main_plot=bool(data.get("is_main_plot", False)),
            review_status=str(data.get("review_status") or "unreviewed").strip(),
            user_note=str(data.get("user_note", "")),
            in_skip_list=bool(data.get("in_skip_list", False)),
            spoiler_levels=SpoilerLevels.from_dict(data.get("spoiler_levels", {}) or {}),
        )

    def validate(self) -> None:
        _require_non_empty(self.finding_id, "finding_id")
        _require_non_empty(self.rule_id, "rule_id")
        _require_non_empty(self.rule_name, "rule_name")
        _require_non_empty(self.chapter_file, "chapter_file")
        if not self.paragraph_ids:
            raise ValueError("paragraph_ids is required")
        _validate_severity(self.severity)
        _validate_confidence(self.confidence)
        if self.review_status not in REVIEW_STATUSES:
            raise ValueError(
                "review_status must be one of: unreviewed, confirmed, false_positive"
            )

    def to_dict(self) -> Dict[str, Any]:
        self.validate()
        data = asdict(self)
        data["spoiler_levels"] = self.spoiler_levels.to_dict()
        return data


@dataclass
class EventSummary:
    low: str = ""
    standard: str = ""
    detailed: str = ""

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EventSummary":
        return cls(
            low=str(data.get("low", "")),
            standard=str(data.get("standard", "")),
            detailed=str(data.get("detailed", "")),
        )

    def to_dict(self) -> Dict[str, str]:
        return asdict(self)


@dataclass
class ScanEvent:
    event_id: str
    rule_id: str
    rule_name: str
    first_chapter: str
    related_chapters: List[str] = field(default_factory=list)
    max_severity: int = 1
    max_confidence: float = 0
    is_main_plot: bool = False
    finding_ids: List[str] = field(default_factory=list)
    event_summary: EventSummary = field(default_factory=EventSummary)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ScanEvent":
        event_id = str(data.get("event_id") or f"event_{uuid.uuid4().hex}")
        return cls(
            event_id=event_id,
            rule_id=str(data.get("rule_id", "")).strip(),
            rule_name=str(data.get("rule_name", "")).strip(),
            first_chapter=str(data.get("first_chapter", "")).strip(),
            related_chapters=_string_list(data.get("related_chapters", [])),
            max_severity=_coerce_int(data.get("max_severity"), 1),
            max_confidence=_coerce_float(data.get("max_confidence"), 0),
            is_main_plot=bool(data.get("is_main_plot", False)),
            finding_ids=_string_list(data.get("finding_ids", [])),
            event_summary=EventSummary.from_dict(data.get("event_summary", {}) or {}),
        )

    def validate(self) -> None:
        _require_non_empty(self.event_id, "event_id")
        _require_non_empty(self.rule_id, "rule_id")
        _require_non_empty(self.rule_name, "rule_name")
        _require_non_empty(self.first_chapter, "first_chapter")
        _validate_severity(self.max_severity, "max_severity")
        _validate_confidence(self.max_confidence, "max_confidence")

    def to_dict(self) -> Dict[str, Any]:
        self.validate()
        data = asdict(self)
        data["event_summary"] = self.event_summary.to_dict()
        return data


@dataclass
class RuleHitSummary:
    rule_id: str
    count: int = 0
    max_severity: int = 1

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RuleHitSummary":
        return cls(
            rule_id=str(data.get("rule_id", "")).strip(),
            count=_coerce_int(data.get("count"), 0),
            max_severity=_coerce_int(data.get("max_severity"), 1),
        )

    def validate(self) -> None:
        _require_non_empty(self.rule_id, "rule_id")
        if self.count < 0:
            raise ValueError("rule hit count must be greater than or equal to 0")
        _validate_severity(self.max_severity, "max_severity")

    def to_dict(self) -> Dict[str, Any]:
        self.validate()
        return asdict(self)


@dataclass
class ScanReportSummary:
    total_findings: int = 0
    verified_findings: int = 0
    pending_review: int = 0
    rules_hit: List[RuleHitSummary] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ScanReportSummary":
        return cls(
            total_findings=_coerce_int(data.get("total_findings"), 0),
            verified_findings=_coerce_int(data.get("verified_findings"), 0),
            pending_review=_coerce_int(data.get("pending_review"), 0),
            rules_hit=[
                RuleHitSummary.from_dict(item) for item in data.get("rules_hit", [])
            ],
        )

    def validate(self) -> None:
        for field_name in ["total_findings", "verified_findings", "pending_review"]:
            if getattr(self, field_name) < 0:
                raise ValueError(f"{field_name} must be greater than or equal to 0")
        for rule_hit in self.rules_hit:
            rule_hit.validate()

    def to_dict(self) -> Dict[str, Any]:
        self.validate()
        return {
            "total_findings": self.total_findings,
            "verified_findings": self.verified_findings,
            "pending_review": self.pending_review,
            "rules_hit": [rule_hit.to_dict() for rule_hit in self.rules_hit],
        }


@dataclass
class ScanReport:
    report_id: str
    project_slug: str
    profile_id: str
    profile_name: str
    scan_mode: str = DEFAULT_SCAN_MODE
    scan_range: ScanRange = field(default_factory=ScanRange)
    scan_config: TriggerScanConfig = field(default_factory=TriggerScanConfig)
    created_at: float = 0
    completed_at: Optional[float] = None
    status: str = "pending"
    summary: ScanReportSummary = field(default_factory=ScanReportSummary)
    events: List[ScanEvent] = field(default_factory=list)
    findings: List[ScanFinding] = field(default_factory=list)
    profile_snapshot: Optional[Dict[str, Any]] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ScanReport":
        report_id = str(data.get("report_id") or f"report_{uuid.uuid4().hex}")
        scan_config_data = dict(data.get("scan_config", {}) or {})
        if scan_config_data.get("scan_mode") == "hybrid":
            scan_config_data["scan_mode"] = DEFAULT_SCAN_MODE
        return cls(
            report_id=report_id,
            project_slug=str(data.get("project_slug", "")).strip(),
            profile_id=str(data.get("profile_id", "")).strip(),
            profile_name=str(data.get("profile_name", "")).strip(),
            scan_mode=str(data.get("scan_mode") or DEFAULT_SCAN_MODE).strip(),
            scan_range=ScanRange.from_dict(data.get("scan_range", {}) or {}),
            scan_config=TriggerScanConfig.from_dict(scan_config_data),
            created_at=_coerce_float(data.get("created_at"), 0),
            completed_at=(
                None
                if data.get("completed_at") is None
                else _coerce_float(data.get("completed_at"), 0)
            ),
            status=str(data.get("status") or "pending").strip(),
            summary=ScanReportSummary.from_dict(data.get("summary", {}) or {}),
            events=[ScanEvent.from_dict(item) for item in data.get("events", [])],
            findings=[ScanFinding.from_dict(item) for item in data.get("findings", [])],
            profile_snapshot=data.get("profile_snapshot"),
        )

    def validate(self) -> None:
        _require_non_empty(self.report_id, "report_id")
        _require_non_empty(self.project_slug, "project_slug")
        _require_non_empty(self.profile_id, "profile_id")
        _require_non_empty(self.profile_name, "profile_name")
        if self.scan_mode not in LEGACY_REPORT_SCAN_MODES:
            raise ValueError("scan_mode must be one of: hybrid, precise")
        if self.status not in REPORT_STATUSES:
            raise ValueError(
                "status must be one of: pending, running, completed, failed, cancelled"
            )
        self.scan_range.validate()
        self.scan_config.validate()
        self.summary.validate()
        for event in self.events:
            event.validate()
        for finding in self.findings:
            finding.validate()

    def to_dict(self) -> Dict[str, Any]:
        self.validate()
        return {
            "report_id": self.report_id,
            "project_slug": self.project_slug,
            "profile_id": self.profile_id,
            "profile_name": self.profile_name,
            "scan_mode": self.scan_mode,
            "scan_range": self.scan_range.to_dict(),
            "scan_config": self.scan_config.to_dict(),
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "status": self.status,
            "summary": self.summary.to_dict(),
            "events": [event.to_dict() for event in self.events],
            "findings": [finding.to_dict() for finding in self.findings],
            "profile_snapshot": self.profile_snapshot,
        }


@dataclass
class SkipListItem:
    chapter_file: str
    chapter_title: str = ""
    paragraph_range: str = ""
    rule_name: str = ""
    severity: int = 1
    user_note: str = ""
    source_finding_id: str = ""

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SkipListItem":
        return cls(
            chapter_file=str(data.get("chapter_file", "")).strip(),
            chapter_title=str(data.get("chapter_title", "")),
            paragraph_range=str(data.get("paragraph_range", "")).strip(),
            rule_name=str(data.get("rule_name", "")).strip(),
            severity=_coerce_int(data.get("severity"), 1),
            user_note=str(data.get("user_note", "")),
            source_finding_id=str(data.get("source_finding_id", "")).strip(),
        )

    def validate(self) -> None:
        _require_non_empty(self.chapter_file, "chapter_file")
        _require_non_empty(self.rule_name, "rule_name")
        _validate_severity(self.severity)

    def to_dict(self) -> Dict[str, Any]:
        self.validate()
        return asdict(self)


@dataclass
class SkipList:
    skip_list_id: str
    project_slug: str
    items: List[SkipListItem] = field(default_factory=list)
    created_at: float = 0
    updated_at: float = 0

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SkipList":
        skip_list_id = str(data.get("skip_list_id") or f"skip_{uuid.uuid4().hex}")
        return cls(
            skip_list_id=skip_list_id,
            project_slug=str(data.get("project_slug", "")).strip(),
            items=[SkipListItem.from_dict(item) for item in data.get("items", [])],
            created_at=_coerce_float(data.get("created_at"), 0),
            updated_at=_coerce_float(data.get("updated_at"), 0),
        )

    def validate(self) -> None:
        _require_non_empty(self.skip_list_id, "skip_list_id")
        _require_non_empty(self.project_slug, "project_slug")
        for item in self.items:
            item.validate()

    def to_dict(self) -> Dict[str, Any]:
        self.validate()
        return {
            "skip_list_id": self.skip_list_id,
            "project_slug": self.project_slug,
            "items": [item.to_dict() for item in self.items],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


BUILTIN_RULE_GROUPS = [
    TriggerRuleGroup(
        id="group_romance",
        name="感情类",
        rules=[
            "rule_ntr",
            "rule_abuse_romance",
            "rule_harem",
            "rule_relationship_control",
        ],
    ),
    TriggerRuleGroup(
        id="group_character",
        name="角色类",
        rules=[
            "rule_character_death",
            "rule_character_blacken",
            "rule_protagonist_stupid",
        ],
    ),
    TriggerRuleGroup(
        id="group_violence",
        name="暴力类",
        rules=["rule_gore_torture", "rule_sexual_violence", "rule_animal_harm"],
    ),
    TriggerRuleGroup(
        id="group_plot",
        name="剧情类",
        rules=[
            "rule_betrayal",
            "rule_mind_control",
            "rule_bad_ending",
            "rule_long_misunderstanding",
        ],
    ),
    TriggerRuleGroup(
        id="group_sensitive",
        name="敏感类",
        rules=["rule_minor_sensitive", "rule_coercive_relationship"],
    ),
]

BUILTIN_RULES = [
    TriggerRule(
        id="rule_ntr",
        name="NTR / 感情背叛",
        group_id="group_romance",
        description="恋人、伴侣或明确感情对象被他人夺走、出轨或背叛。",
        matching_policy="explicit_or_strongly_implied",
        severity_threshold=3,
        examples=["伴侣明确出轨", "恋人被他人夺走并造成主角痛苦"],
        negative_examples=["普通误会", "无恋爱关系的单方面吃醋"],
    ),
    TriggerRule(
        id="rule_abuse_romance",
        name="感情线虐恋",
        group_id="group_romance",
        description="重要感情关系中出现长期精神虐待、强迫关系、PUA 或冷暴力。",
        matching_policy="explicit_or_strongly_implied",
        severity_threshold=2,
        examples=["以爱为名限制自由", "长期羞辱或贬低伴侣"],
        negative_examples=["普通争吵后和解", "短暂误会但无长期伤害"],
    ),
    TriggerRule(
        id="rule_harem",
        name="后宫 / 多角关系",
        group_id="group_romance",
        description="主角同时与多人保持暧昧、恋爱或承诺关系。",
        matching_policy="explicit_or_strongly_implied",
        severity_threshold=2,
        examples=["主角与多人确认亲密关系"],
        negative_examples=["普通队友情", "未被文本支持的读者猜测"],
    ),
    TriggerRule(
        id="rule_relationship_control",
        name="亲密关系操控",
        group_id="group_romance",
        description="亲密关系中出现控制社交、行动、资源或情绪的行为。",
        matching_policy="explicit_or_strongly_implied",
        severity_threshold=2,
        examples=["限制伴侣与外界接触", "用威胁控制对方选择"],
        negative_examples=["合理安全提醒", "双方明确同意的保护安排"],
    ),
    TriggerRule(
        id="rule_character_death",
        name="主要角色死亡",
        group_id="group_character",
        description="主角、重要配角或长期陪伴角色死亡。",
        matching_policy="explicit_or_strongly_implied",
        severity_threshold=3,
        examples=["重要配角牺牲", "主角死亡或被确认死亡"],
        negative_examples=["假死且立即揭示", "梦境中的死亡"],
    ),
    TriggerRule(
        id="rule_character_blacken",
        name="角色黑化",
        group_id="group_character",
        description="重要角色因重大事件转向极端、复仇、反派或伤害无辜。",
        matching_policy="explicit_or_strongly_implied",
        severity_threshold=3,
        examples=["重要角色开始主动伤害无辜"],
        negative_examples=["短暂愤怒", "策略性伪装"],
    ),
    TriggerRule(
        id="rule_protagonist_stupid",
        name="主角降智",
        group_id="group_character",
        description="主角智力、判断或能力表现明显低于既有设定并推动负面剧情。",
        matching_policy="explicit_or_strongly_implied",
        severity_threshold=2,
        examples=["主角无视已知危险反复犯错"],
        negative_examples=["信息不足导致的合理误判"],
    ),
    TriggerRule(
        id="rule_gore_torture",
        name="血腥酷刑",
        group_id="group_violence",
        description="出现血腥、酷刑、肢解或长时间折磨描写。",
        matching_policy="explicit_only",
        severity_threshold=3,
        examples=["详细酷刑描写", "明显血腥肢体伤害"],
        negative_examples=["普通战斗受伤", "一笔带过的打斗"],
    ),
    TriggerRule(
        id="rule_sexual_violence",
        name="性暴力",
        group_id="group_violence",
        description="出现强迫性行为、性侵威胁或相关创伤剧情。",
        matching_policy="explicit_or_strongly_implied",
        severity_threshold=4,
        examples=["明确强迫性行为", "以性侵作为威胁"],
        negative_examples=["双方明确同意的亲密关系"],
    ),
    TriggerRule(
        id="rule_animal_harm",
        name="动物伤害",
        group_id="group_violence",
        description="动物被虐待、杀害或被用作残酷情节工具。",
        matching_policy="explicit_or_strongly_implied",
        severity_threshold=2,
        examples=["宠物被伤害作为威胁"],
        negative_examples=["普通狩猎或食物来源的简略提及"],
    ),
    TriggerRule(
        id="rule_betrayal",
        name="背叛",
        group_id="group_plot",
        description="重要盟友、亲人、师门或组织对主角方做出重大背叛。",
        matching_policy="explicit_or_strongly_implied",
        severity_threshold=3,
        examples=["亲近角色出卖主角"],
        negative_examples=["战略分歧", "误会导致的短暂冲突"],
    ),
    TriggerRule(
        id="rule_mind_control",
        name="精神控制",
        group_id="group_plot",
        description="角色被洗脑、操控意识、夺舍或失去自主意志。",
        matching_policy="explicit_or_strongly_implied",
        severity_threshold=3,
        examples=["重要角色被洗脑伤害同伴"],
        negative_examples=["普通催眠表演", "自愿伪装被控制"],
    ),
    TriggerRule(
        id="rule_bad_ending",
        name="烂尾 / 开放式 BE",
        group_id="group_plot",
        description="结局明显悲剧、关键问题未解决或主要角色走向不可逆失败。",
        matching_policy="explicit_or_strongly_implied",
        severity_threshold=3,
        examples=["主线以悲剧结束", "关键冲突无解决且暗示失败"],
        negative_examples=["阶段性低谷", "续作伏笔"],
    ),
    TriggerRule(
        id="rule_long_misunderstanding",
        name="重大误会长期不解",
        group_id="group_plot",
        description="关键角色之间的误会持续多章且造成重大伤害或关系破裂。",
        matching_policy="explicit_or_strongly_implied",
        severity_threshold=2,
        examples=["误会持续推动虐恋或敌对"],
        negative_examples=["当章解释清楚的小误会"],
    ),
    TriggerRule(
        id="rule_minor_sensitive",
        name="未成年人相关敏感剧情",
        group_id="group_sensitive",
        description="涉及未成年人被性化、虐待、剥削或其他敏感伤害剧情。",
        matching_policy="explicit_or_strongly_implied",
        severity_threshold=4,
        examples=["未成年人遭受剥削或严重伤害"],
        negative_examples=["正常成长烦恼", "校园日常冲突"],
    ),
    TriggerRule(
        id="rule_coercive_relationship",
        name="强迫关系",
        group_id="group_sensitive",
        description="角色被胁迫进入亲密、婚约、主仆或依附关系。",
        matching_policy="explicit_or_strongly_implied",
        severity_threshold=3,
        examples=["以生命或资源威胁迫使建立关系"],
        negative_examples=["双方协商后的合作关系"],
    ),
]


def default_trigger_scan_config(scan_mode: str = DEFAULT_SCAN_MODE) -> TriggerScanConfig:
    normalized_mode = DEFAULT_SCAN_MODE if scan_mode == "hybrid" else scan_mode
    return TriggerScanConfig(
        scan_mode=normalized_mode,
        verification_enabled=True,
    )


def builtin_trigger_profile(timestamp: float = 0) -> TriggerProfile:
    return TriggerProfile(
        id="profile_builtin_default",
        name="默认避雷档案",
        description="包含常见网文阅读雷点的内置模板，可按个人偏好编辑。",
        created_at=timestamp,
        updated_at=timestamp,
        rule_groups=[
            TriggerRuleGroup.from_dict(group.to_dict()) for group in BUILTIN_RULE_GROUPS
        ],
        rules=[TriggerRule.from_dict(rule.to_dict()) for rule in BUILTIN_RULES],
    )
