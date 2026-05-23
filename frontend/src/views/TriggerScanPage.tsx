import {
  Check,
  ChevronDown,
  Copy,
  Eye,
  FileDown,
  FileUp,
  ListChecks,
  Play,
  Plus,
  RefreshCw,
  Save,
  Search,
  ShieldAlert,
  Square,
  Trash2,
  X
} from "lucide-react";
import React, { useCallback, useEffect, useMemo, useState } from "react";
import { apiClient } from "../api/client";
import { apiDisplayName } from "../api/display";
import type {
  ProjectRecord,
  ScanFinding,
  ScanReport,
  SkipListItem,
  SkipListResponse,
  SpoilerLevel,
  TriggerMatchingPolicy,
  TriggerProfile,
  TriggerReviewStatus,
  TriggerRule,
  TriggerRuleGroup,
  TriggerScanConfig,
  TriggerScanContextResponse,
  TriggerScanPrecheckResponse,
  TriggerScanReportHistoryItem
} from "../api/types";
import { GuidancePanel } from "../components/common/Guidance";
import { StageProgressBar, type Stage } from "../components/StageProgressBar";
import {
  NumberInput,
  SelectField,
  TextAreaField,
  TextInput,
  ToggleSwitch
} from "../components/forms/FormControls";
import { useTaskActions } from "../hooks/useTaskActions";
import { useTaskAvailability } from "../hooks/useTaskAvailability";
import { useAppState } from "../state/AppState";

type TriggerTab = "profiles" | "scan" | "results" | "skip";
type ResultView = "events" | "findings";

const triggerTabs: Array<{ key: TriggerTab; label: string; meta: string }> = [
  { key: "profiles", label: "档案", meta: "规则" },
  { key: "scan", label: "扫描", meta: "配置" },
  { key: "results", label: "结果", meta: "报告" },
  { key: "skip", label: "跳读", meta: "清单" }
];

const matchingPolicyOptions: Array<{ label: string; value: TriggerMatchingPolicy }> = [
  { label: "仅明确出现", value: "explicit_only" },
  { label: "明确或强暗示", value: "explicit_or_strongly_implied" },
  { label: "任何线索", value: "any_hint" }
];

const spoilerOptions: Array<{ label: string; value: SpoilerLevel }> = [
  { label: "低剧透", value: "low" },
  { label: "标准", value: "standard" },
  { label: "详细", value: "detailed" }
];

const reviewOptions: Array<{ label: string; value: TriggerReviewStatus | "" }> = [
  { label: "全部", value: "" },
  { label: "未复核", value: "unreviewed" },
  { label: "确认", value: "confirmed" },
  { label: "误报", value: "false_positive" }
];

function classNames(...values: Array<string | false | undefined>) {
  return values.filter(Boolean).join(" ");
}

function splitLines(value: string) {
  return value
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);
}

function joinLines(values: string[]) {
  return values.join("\n");
}

function randomId(prefix: string) {
  return `${prefix}_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
}

function createGroup(): TriggerRuleGroup {
  const id = randomId("group");
  return {
    id,
    name: "新分组",
    rules: []
  };
}

function createRule(groupId: string): TriggerRule {
  return {
    id: randomId("rule"),
    name: "新规则",
    group_id: groupId,
    description: "",
    matching_policy: "explicit_or_strongly_implied",
    severity_threshold: 2,
    enabled: true,
    examples: [],
    negative_examples: []
  };
}

function cloneProfile(profile: TriggerProfile): TriggerProfile {
  return {
    ...profile,
    rule_groups: profile.rule_groups.map((group) => ({ ...group, rules: [...group.rules] })),
    rules: profile.rules.map((rule) => ({
      ...rule,
      examples: [...rule.examples],
      negative_examples: [...rule.negative_examples]
    }))
  };
}

function formatTime(timestamp?: number | null) {
  if (!timestamp) {
    return "暂无时间";
  }
  return new Date(timestamp * 1000).toLocaleString();
}

function workflowLabel(project: ProjectRecord) {
  return project.workflow_type === "chapter_split" ? "章节分割" : "小说总结";
}

function chapterNumber(path: string) {
  const name = path.split(/[\\/]/).pop() ?? path;
  const match = name.match(/第\s*0*(\d+)\s*[章回]/);
  return match ? Number.parseInt(match[1], 10) : null;
}

function pathName(path: string) {
  return path.split(/[\\/]/).pop() ?? path;
}

function isFinding(value: unknown): value is ScanFinding {
  return Boolean(
    value &&
      typeof value === "object" &&
      "finding_id" in value &&
      "rule_name" in value &&
      "chapter_file" in value
  );
}

function spoilerText(finding: ScanFinding, level: SpoilerLevel) {
  const detail = finding.spoiler_levels[level] ?? finding.spoiler_levels.standard;
  return detail?.description || "";
}

function skipAdvice(finding: ScanFinding, level: SpoilerLevel) {
  const detail = finding.spoiler_levels[level] ?? finding.spoiler_levels.standard;
  return detail?.skip_advice || "";
}

function evidenceQuote(finding: ScanFinding) {
  return finding.spoiler_levels.detailed?.evidence_quote || "";
}

function statusText(status: string) {
  switch (status) {
    case "running":
      return "运行中";
    case "paused":
      return "已暂停";
    case "canceling":
      return "取消中";
    case "cancelled":
      return "已取消";
    case "success":
      return "已完成";
    case "failed":
      return "失败";
    case "completed":
      return "已完成";
    default:
      return status || "暂无";
  }
}

function reviewBadge(status: string) {
  const labelMap: Record<string, string> = {
    unreviewed: "未复核",
    confirmed: "已确认",
    false_positive: "误报"
  };
  const label = labelMap[status] || status || "暂无";
  const cls = `review-badge review-badge--${status}`;
  return <span className={cls}>{label}</span>;
}

interface ResultFilters {
  ruleId: string;
  reviewStatus: string;
  minSeverity: number;
  minConfidence: number;
  chapterText: string;
  mainPlot: "all" | "main" | "side";
  highRiskOnly: boolean;
}

interface ContextState {
  finding: ScanFinding;
  response: TriggerScanContextResponse | null;
  isLoading: boolean;
  error: string;
}

const emptyFilters: ResultFilters = {
  ruleId: "",
  reviewStatus: "",
  minSeverity: 1,
  minConfidence: 0,
  chapterText: "",
  mainPlot: "all",
  highRiskOnly: false
};

const emptySkipDraft: SkipListItem = {
  chapter_file: "",
  chapter_title: "",
  paragraph_range: "",
  rule_name: "",
  severity: 1,
  user_note: "",
  source_finding_id: ""
};

export function TriggerScanPage() {
  const { state, dispatch } = useAppState();
  const { latestTask, isTaskBusy } = useTaskAvailability();
  const [activeTab, setActiveTab] = useState<TriggerTab>("scan");
  const [projects, setProjects] = useState<ProjectRecord[]>([]);
  const [profiles, setProfiles] = useState<TriggerProfile[]>([]);
  const [selectedProjectSlug, setSelectedProjectSlug] = useState("");
  const [selectedProfileId, setSelectedProfileId] = useState("");
  const [profileDraft, setProfileDraft] = useState<TriggerProfile | null>(null);
  const [statusMessage, setStatusMessage] = useState("");
  const [activeGroupId, setActiveGroupId] = useState<string | null>(null);
  const [expandedRules, setExpandedRules] = useState<Set<string>>(new Set());
  const importFileRef = React.useRef<HTMLInputElement>(null);

  const [rangeStart, setRangeStart] = useState(1);
  const [rangeEnd, setRangeEnd] = useState<number | "">("");
  const [scanApiIds, setScanApiIds] = useState<string[]>([]);
  const [minConfidence, setMinConfidence] = useState(0.45);
  const [keepLowConfidence, setKeepLowConfidence] = useState(false);
  const [verificationEnabled, setVerificationEnabled] = useState(true);
  const [verificationApiId, setVerificationApiId] = useState("");
  const [preciseChapterBatchSize, setPreciseChapterBatchSize] = useState(5);
  const [verificationChapterBatchSize, setVerificationChapterBatchSize] = useState(5);
  const [maxQuoteChars, setMaxQuoteChars] = useState(80);
  const [generateSkipAdvice, setGenerateSkipAdvice] = useState(true);
  const [minimumOutputCharacters, setMinimumOutputCharacters] = useState(0);
  const [precheck, setPrecheck] = useState<TriggerScanPrecheckResponse | null>(null);
  const [resumeReportId, setResumeReportId] = useState("");

  const [reports, setReports] = useState<TriggerScanReportHistoryItem[]>([]);
  const [selectedReportId, setSelectedReportId] = useState("");
  const [report, setReport] = useState<ScanReport | null>(null);
  const [resultView, setResultView] = useState<ResultView>("events");
  const [globalSpoiler, setGlobalSpoiler] = useState<SpoilerLevel>("standard");
  const [itemSpoilers, setItemSpoilers] = useState<Record<string, SpoilerLevel>>({});
  const [expandedEventIds, setExpandedEventIds] = useState<Set<string>>(new Set());
  const [findingPage, setFindingPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [filters, setFilters] = useState<ResultFilters>(emptyFilters);
  const [notes, setNotes] = useState<Record<string, string>>({});
  const [contextState, setContextState] = useState<ContextState | null>(null);
  const [skipList, setSkipList] = useState<SkipListResponse | null>(null);
  const [skipDraft, setSkipDraft] = useState<SkipListItem>(emptySkipDraft);

  const activeApis = useMemo(
    () => state.apiConfigs.filter((config) => config.is_active),
    [state.apiConfigs]
  );
  const scanProjects = useMemo(
    () =>
      projects.filter((project) =>
        ["novel_summary", "chapter_split"].includes(String(project.workflow_type))
      ),
    [projects]
  );
  const selectedProject = useMemo(
    () => scanProjects.find((project) => project.project_slug === selectedProjectSlug) ?? null,
    [scanProjects, selectedProjectSlug]
  );
  const selectedProfile = useMemo(
    () => profiles.find((profile) => profile.id === selectedProfileId) ?? null,
    [profiles, selectedProfileId]
  );
  const latestTriggerTask = useMemo(
    () =>
      state.taskOrder
        .map((taskId) => state.tasks[taskId])
        .find((task) => task?.task_type === "trigger_scan") ?? null,
    [state.taskOrder, state.tasks]
  );
  const triggerEvents = latestTriggerTask?.events ?? [];
  const liveFindings = useMemo(
    () =>
      triggerEvents
        .map((event) => event.data?.finding)
        .filter(isFinding)
        .slice(-8)
        .reverse(),
    [triggerEvents]
  );
  const scanStages = useMemo((): Stage[] => {
    for (let i = triggerEvents.length - 1; i >= 0; i--) {
      const ev = triggerEvents[i];
      if (ev.event_type === "progress" && Array.isArray(ev.data?.stages)) {
        return ev.data.stages as Stage[];
      }
    }
    return [];
  }, [triggerEvents]);
  const scanCurrentStage = useMemo(() => {
    for (let i = triggerEvents.length - 1; i >= 0; i--) {
      const ev = triggerEvents[i];
      if (ev.event_type === "progress" && typeof ev.data?.current_stage === "string") {
        return ev.data.current_stage as string;
      }
    }
    return "";
  }, [triggerEvents]);

  const showError = useCallback(
    (error: unknown, fallback = "操作失败") => {
      dispatch({
        type: "set_error",
        message: error instanceof Error ? error.message : fallback
      });
    },
    [dispatch]
  );

  const loadProfiles = useCallback(async () => {
    try {
      const items = await apiClient.listTriggerProfiles();
      setProfiles(items);
      setSelectedProfileId((current) =>
        current && items.some((profile) => profile.id === current) ? current : items[0]?.id ?? ""
      );
      dispatch({ type: "set_error", message: null });
    } catch (error: unknown) {
      showError(error, "加载雷点档案失败");
    }
  }, [dispatch, showError]);

  const loadProjects = useCallback(async () => {
    try {
      const items = await apiClient.listProjects();
      setProjects(items);
      setSelectedProjectSlug((current) => {
        const scanItems = items.filter((project) =>
          ["novel_summary", "chapter_split"].includes(String(project.workflow_type))
        );
        return current && scanItems.some((project) => project.project_slug === current)
          ? current
          : scanItems[0]?.project_slug ?? "";
      });
      dispatch({ type: "set_error", message: null });
    } catch (error: unknown) {
      showError(error, "加载项目失败");
    }
  }, [dispatch, showError]);

  const refreshReports = useCallback(
    async (projectSlug = selectedProjectSlug) => {
      if (!projectSlug) {
        setReports([]);
        setSelectedReportId("");
        setReport(null);
        return;
      }
      try {
        const items = await apiClient.listTriggerScanReports(projectSlug);
        setReports(items);
        setSelectedReportId((current) =>
          current && items.some((item) => item.report_id === current)
            ? current
            : items[0]?.report_id ?? ""
        );
      } catch (error: unknown) {
        setReports([]);
        showError(error, "加载扫描报告失败");
      }
    },
    [selectedProjectSlug, showError]
  );

  const loadSkipList = useCallback(
    async (projectSlug = selectedProjectSlug) => {
      if (!projectSlug) {
        setSkipList(null);
        return;
      }
      try {
        setSkipList(await apiClient.getTriggerScanSkipList(projectSlug));
      } catch {
        setSkipList(null);
      }
    },
    [selectedProjectSlug]
  );

  const { startTask, watchTask } = useTaskActions({
    onTaskTerminal: () => {
      void refreshReports();
      void loadProjects();
      void loadSkipList();
    }
  });

  useEffect(() => {
    void loadProjects();
    void loadProfiles();
  }, [loadProfiles, loadProjects]);

  useEffect(() => {
    setProfileDraft(selectedProfile ? cloneProfile(selectedProfile) : null);
  }, [selectedProfile?.id, selectedProfile?.updated_at]);

  useEffect(() => {
    const activeIds = activeApis.map((config) => config.id);
    setScanApiIds((current) => {
      const kept = current.filter((apiId) => activeIds.includes(apiId));
      return kept.length > 0 ? kept : activeIds;
    });
    setVerificationApiId((current) =>
      current && activeIds.includes(current) ? current : activeIds[0] ?? ""
    );
  }, [activeApis]);

  useEffect(() => {
    void refreshReports(selectedProjectSlug);
    void loadSkipList(selectedProjectSlug);
    setPrecheck(null);
    if (selectedProjectSlug) {
      apiClient.loadTriggerScanConfig(selectedProjectSlug).then((cfg) => {
        setRangeStart(cfg.scan_range?.start ?? 1);
        setRangeEnd(cfg.scan_range?.end ?? "");
        setScanApiIds(cfg.scan_api_ids ?? []);
        setMinConfidence(cfg.min_confidence ?? 0.45);
        setKeepLowConfidence(cfg.keep_low_confidence ?? false);
        setVerificationEnabled(cfg.verification_enabled ?? true);
        setVerificationApiId(cfg.verification_api_id ?? "");
        setPreciseChapterBatchSize(cfg.precise_chapter_batch_size ?? 5);
        setVerificationChapterBatchSize(cfg.verification_chapter_batch_size ?? 5);
        setMaxQuoteChars(cfg.max_quote_chars ?? 80);
        setGenerateSkipAdvice(cfg.generate_skip_advice ?? true);
        setMinimumOutputCharacters(cfg.minimum_output_characters ?? 0);
        setStatusMessage("已加载项目扫描配置");
      }).catch(() => { /* no saved config */ });
    }
  }, [loadSkipList, refreshReports, selectedProjectSlug]);

  useEffect(() => {
    if (!selectedProjectSlug || !selectedReportId) {
      setReport(null);
      return;
    }
    let cancelled = false;
    let pollTimer: ReturnType<typeof setTimeout> | null = null;
    const loadReport = () => {
      apiClient
        .getTriggerScanReport(selectedProjectSlug, selectedReportId)
        .then((item) => {
          if (!cancelled) {
            setReport(item);
            setNotes({});
            setItemSpoilers({});
            dispatch({ type: "set_error", message: null });
            // Keep polling while scan is running
            if (item.status === "running" || item.status === "pending") {
              pollTimer = setTimeout(loadReport, 3000);
            }
          }
        })
        .catch((error: unknown) => {
          if (!cancelled) {
            showError(error, "加载报告详情失败");
          }
        });
    };
    loadReport();
    return () => {
      cancelled = true;
      if (pollTimer !== null) clearTimeout(pollTimer);
    };
  }, [dispatch, selectedProjectSlug, selectedReportId, showError]);

  // Auto-scroll to matched paragraphs when context modal opens
  useEffect(() => {
    if (contextState?.response?.paragraphs) {
      setTimeout(() => {
        const el = document.querySelector(".context-paragraph--matched");
        if (el) el.scrollIntoView({ behavior: "smooth", block: "center" });
      }, 100);
    }
  }, [contextState?.response]);

  const profileDirty = useMemo(
    () => Boolean(profileDraft && selectedProfile && JSON.stringify(profileDraft) !== JSON.stringify(selectedProfile)),
    [profileDraft, selectedProfile]
  );

  const scanConfig = useMemo<TriggerScanConfig>(
    () => ({
      scan_mode: "precise",
      scan_range: {
        start: Math.max(1, rangeStart || 1),
        end: rangeEnd === "" ? null : Math.max(1, rangeEnd)
      },
      scan_api_ids: scanApiIds,
      min_confidence: minConfidence,
      keep_low_confidence: keepLowConfidence,
      verification_enabled: verificationEnabled,
      verification_api_id: verificationEnabled ? verificationApiId : "",
      precise_chapter_batch_size: preciseChapterBatchSize,
      verification_chapter_batch_size: verificationChapterBatchSize,
      max_quote_chars: maxQuoteChars,
      generate_skip_advice: generateSkipAdvice,
      minimum_output_characters: minimumOutputCharacters
    }),
    [
      generateSkipAdvice,
      keepLowConfidence,
      maxQuoteChars,
      minConfidence,
      minimumOutputCharacters,
      preciseChapterBatchSize,
      rangeEnd,
      rangeStart,
      scanApiIds,
      verificationApiId,
      verificationChapterBatchSize,
      verificationEnabled
    ]
  );

  const canPrecheck =
    Boolean(selectedProjectSlug && selectedProfileId && scanApiIds.length > 0) &&
    preciseChapterBatchSize > 0 &&
    verificationChapterBatchSize > 0 &&
    maxQuoteChars > 0;
  const canStart = canPrecheck && !isTaskBusy;

  const buildScanRequest = () => {
    if (!selectedProjectSlug || !selectedProfileId) {
      return null;
    }
    return {
      project_slug: selectedProjectSlug,
      profile_id: selectedProfileId,
      scan_config: scanConfig,
      custom_output_directory_path: selectedProject?.custom_output_directory || undefined,
      resume_from_report_id: resumeReportId || undefined
    };
  };

  const toggleScanApi = (apiId: string, checked: boolean) => {
    setScanApiIds((current) =>
      checked ? [...new Set([...current, apiId])] : current.filter((id) => id !== apiId)
    );
  };

  const createProfile = async () => {
    const name = window.prompt("新档案名称", "我的雷点档案");
    if (!name?.trim()) {
      return;
    }
    try {
      const profile = await apiClient.createTriggerProfile({ name: name.trim(), from_template: true });
      setProfiles((current) => [profile, ...current]);
      setSelectedProfileId(profile.id);
      setStatusMessage("档案已创建");
    } catch (error: unknown) {
      showError(error, "创建档案失败");
    }
  };

  const duplicateProfile = async () => {
    if (!selectedProfile) {
      return;
    }
    const name = window.prompt("副本名称", `${selectedProfile.name} 副本`);
    if (!name?.trim()) {
      return;
    }
    try {
      const profile = await apiClient.duplicateTriggerProfile(selectedProfile.id, {
        name: name.trim()
      });
      setProfiles((current) => [profile, ...current]);
      setSelectedProfileId(profile.id);
      setStatusMessage("档案已复制");
    } catch (error: unknown) {
      showError(error, "复制档案失败");
    }
  };

  const deleteProfile = async () => {
    if (!selectedProfile || !window.confirm(`删除档案「${selectedProfile.name}」？`)) {
      return;
    }
    try {
      await apiClient.deleteTriggerProfile(selectedProfile.id);
      await loadProfiles();
      setStatusMessage("档案已删除");
    } catch (error: unknown) {
      showError(error, "删除档案失败");
    }
  };

  const saveProfile = async () => {
    if (!profileDraft) {
      return;
    }
    try {
      const saved = await apiClient.updateTriggerProfile(profileDraft.id, {
        name: profileDraft.name,
        description: profileDraft.description,
        rule_groups: profileDraft.rule_groups,
        rules: profileDraft.rules
      });
      setProfiles((current) =>
        current.map((profile) => (profile.id === saved.id ? saved : profile))
      );
      setProfileDraft(cloneProfile(saved));
      setStatusMessage("档案已保存");
      dispatch({ type: "set_error", message: null });
    } catch (error: unknown) {
      showError(error, "保存档案失败");
    }
  };

  const updateProfileDraft = <K extends keyof TriggerProfile>(
    key: K,
    value: TriggerProfile[K]
  ) => {
    setProfileDraft((current) => (current ? { ...current, [key]: value } : current));
  };

  const addGroup = () => {
    setProfileDraft((current) =>
      current ? { ...current, rule_groups: [...current.rule_groups, createGroup()] } : current
    );
  };

  const updateGroup = (groupId: string, changes: Partial<TriggerRuleGroup>) => {
    setProfileDraft((current) =>
      current
        ? {
            ...current,
            rule_groups: current.rule_groups.map((group) =>
              group.id === groupId ? { ...group, ...changes } : group
            )
          }
        : current
    );
  };

  const deleteGroup = (groupId: string) => {
    const rulesInGroup = profileDraft?.rules.filter((rule) => rule.group_id === groupId) ?? [];
    if (
      rulesInGroup.length > 0 &&
      !window.confirm(`该分组包含 ${rulesInGroup.length} 条规则。是否同时删除这些规则？`)
    ) {
      return;
    }
    setProfileDraft((current) =>
      current
        ? {
            ...current,
            rule_groups: current.rule_groups.filter((group) => group.id !== groupId),
            rules: current.rules.filter((rule) => rule.group_id !== groupId)
          }
        : current
    );
  };

  const addRule = (groupId: string) => {
    const rule = createRule(groupId);
    setProfileDraft((current) =>
      current
        ? {
            ...current,
            rules: [...current.rules, rule],
            rule_groups: current.rule_groups.map((group) =>
              group.id === groupId ? { ...group, rules: [...group.rules, rule.id] } : group
            )
          }
        : current
    );
  };

  const updateRule = <K extends keyof TriggerRule>(
    ruleId: string,
    key: K,
    value: TriggerRule[K]
  ) => {
    setProfileDraft((current) => {
      if (!current) {
        return current;
      }
      const previous = current.rules.find((rule) => rule.id === ruleId);
      const nextRules = current.rules.map((rule) =>
        rule.id === ruleId ? { ...rule, [key]: value } : rule
      );
      let nextGroups = current.rule_groups;
      if (key === "group_id" && previous && typeof value === "string" && previous.group_id !== value) {
        nextGroups = current.rule_groups.map((group) => {
          const withoutRule = group.rules.filter((id) => id !== ruleId);
          return group.id === value
            ? { ...group, rules: [...withoutRule, ruleId] }
            : { ...group, rules: withoutRule };
        });
      }
      return { ...current, rules: nextRules, rule_groups: nextGroups };
    });
  };

  const deleteRule = (ruleId: string) => {
    setProfileDraft((current) =>
      current
        ? {
            ...current,
            rules: current.rules.filter((rule) => rule.id !== ruleId),
            rule_groups: current.rule_groups.map((group) => ({
              ...group,
              rules: group.rules.filter((id) => id !== ruleId)
            }))
          }
        : current
    );
  };

  const toggleRuleExpanded = (ruleId: string) => {
    setExpandedRules((current) => {
      const next = new Set(current);
      if (next.has(ruleId)) {
        next.delete(ruleId);
      } else {
        next.add(ruleId);
      }
      return next;
    });
  };

  const expandAllRules = () => {
    if (!profileDraft) return;
    const visibleRules =
      activeGroupId === null
        ? profileDraft.rules
        : profileDraft.rules.filter((rule) => rule.group_id === activeGroupId);
    setExpandedRules((current) => {
      const next = new Set(current);
      visibleRules.forEach((rule) => next.add(rule.id));
      return next;
    });
  };

  const collapseAllRules = () => {
    if (!profileDraft) return;
    const visibleRules =
      activeGroupId === null
        ? profileDraft.rules
        : profileDraft.rules.filter((rule) => rule.group_id === activeGroupId);
    setExpandedRules((current) => {
      const next = new Set(current);
      visibleRules.forEach((rule) => next.delete(rule.id));
      return next;
    });
  };

  const exportProfile = () => {
    if (!profileDraft) return;
    const data = {
      name: profileDraft.name,
      description: profileDraft.description,
      rule_groups: profileDraft.rule_groups,
      rules: profileDraft.rules,
    };
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `${profileDraft.name || "profile"}.trigger-profile.json`;
    anchor.click();
    URL.revokeObjectURL(url);
    setStatusMessage("档案已导出");
  };

  const importProfile = async (file: File) => {
    try {
      const text = await file.text();
      const data = JSON.parse(text);
      if (!data || typeof data !== "object") {
        throw new Error("无效的档案文件格式");
      }
      const profile = await apiClient.importTriggerProfile(data);
      setProfiles((current) => [profile, ...current]);
      setSelectedProfileId(profile.id);
      setStatusMessage(`档案「${profile.name}」导入成功`);
    } catch (error: unknown) {
      showError(error, "导入档案失败");
    }
  };

  const handleImportFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      void importProfile(file);
    }
    event.target.value = "";
  };

  const matchingPolicyLabel = (policy: string) => {
    const option = matchingPolicyOptions.find((item) => item.value === policy);
    return option?.label ?? policy;
  };

  const saveConfig = async () => {
    if (!selectedProjectSlug) {
      dispatch({ type: "set_error", message: "请选择项目" });
      return;
    }
    try {
      await apiClient.saveTriggerScanConfig(selectedProjectSlug, scanConfig);
      setStatusMessage("扫描配置已保存");
    } catch (error: unknown) {
      showError(error, "保存扫描配置失败");
    }
  };

  const runPrecheck = async () => {
    const request = buildScanRequest();
    if (!request) {
      dispatch({ type: "set_error", message: "请选择项目和雷点档案" });
      return null;
    }
    try {
      const response = await apiClient.precheckTriggerScan(request);
      setPrecheck(response);
      setStatusMessage(response.ready ? "预检通过，可以启动扫描" : "预检需要处理");
      dispatch({ type: "set_error", message: null });
      return response;
    } catch (error: unknown) {
      showError(error, "扫描预检失败");
      return null;
    }
  };

  const startScan = async () => {
    const request = buildScanRequest();
    if (!request) {
      dispatch({ type: "set_error", message: "请选择项目和雷点档案" });
      return;
    }
    const check = await runPrecheck();
    if (!check?.ready) {
      return;
    }
    const task = await startTask(() => apiClient.startTriggerScan(request));
    if (task) {
      setStatusMessage("雷点扫描已启动");
    }
  };

  const migrateProject = async () => {
    if (!selectedProject) {
      return;
    }
    if (
      !window.confirm(
        `项目「${selectedProject.project_name}」需要迁移为单章文件后才能精确定位。是否现在迁移？`
      )
    ) {
      return;
    }
    try {
      const result = await apiClient.migrateChapterGranularity(selectedProject.project_slug);
      await loadProjects();
      setSelectedProjectSlug(result.project.project_slug);
      setStatusMessage("章节粒度迁移已完成");
    } catch (directError: unknown) {
      const directMessage = directError instanceof Error ? directError.message : String(directError);
      if (!window.confirm(`直接迁移失败：${directMessage}\n\n是否选择原始整本 TXT 重新拆分？`)) {
        return;
      }
      const sourceTxtPath = await apiClient.pickFile("选择原始整本 TXT");
      if (!sourceTxtPath) {
        return;
      }
      try {
        const result = await apiClient.migrateChapterGranularity(
          selectedProject.project_slug,
          sourceTxtPath
        );
        await loadProjects();
        setSelectedProjectSlug(result.project.project_slug);
        setStatusMessage("已使用原始 TXT 完成迁移");
      } catch (fallbackError: unknown) {
        showError(fallbackError, "迁移失败");
      }
    }
  };

  const controlTriggerTask = async (action: "resume" | "cancel") => {
    if (!latestTriggerTask) {
      return;
    }
    try {
      const task =
        action === "resume"
          ? await apiClient.resumeTask(latestTriggerTask.task_id)
          : await apiClient.cancelTask(latestTriggerTask.task_id);
      watchTask(task);
      setStatusMessage(action === "resume" ? "已请求恢复扫描" : "已请求取消扫描");
    } catch (error: unknown) {
      showError(error, action === "resume" ? "恢复扫描失败" : "取消扫描失败");
    }
  };

  const exportReport = async (format: "md" | "json") => {
    if (!report) {
      return;
    }
    try {
      const exported = await apiClient.exportTriggerScanReport(
        report.project_slug,
        report.report_id,
        format
      );
      setStatusMessage(`已导出：${exported.path}`);
    } catch (error: unknown) {
      showError(error, "导出报告失败");
    }
  };

  const deleteReport = async () => {
    if (!report || !window.confirm(`删除报告 ${report.report_id}？`)) {
      return;
    }
    try {
      await apiClient.deleteTriggerScanReport(report.project_slug, report.report_id);
      await refreshReports(report.project_slug);
      setStatusMessage("报告已删除");
    } catch (error: unknown) {
      showError(error, "删除报告失败");
    }
  };

  const updateFinding = async (
    finding: ScanFinding,
    payload: { review_status?: TriggerReviewStatus; user_note?: string }
  ) => {
    if (!report) {
      return;
    }
    try {
      const updated = await apiClient.updateTriggerScanFinding(
        report.project_slug,
        report.report_id,
        finding.finding_id,
        payload
      );
      setReport((current) =>
        current
          ? {
              ...current,
              findings: current.findings.map((item) =>
                item.finding_id === updated.finding_id ? updated : item
              )
            }
          : current
      );
      setStatusMessage("条目已更新");
    } catch (error: unknown) {
      showError(error, "更新条目失败");
    }
  };

  const addFindingToSkipList = async (finding: ScanFinding) => {
    if (!report) {
      return;
    }
    try {
      const updatedSkipList = await apiClient.addTriggerScanFindingToSkipList(
        report.project_slug,
        report.report_id,
        finding.finding_id,
        { user_note: notes[finding.finding_id] ?? finding.user_note }
      );
      setSkipList(updatedSkipList);
      setReport((current) =>
        current
          ? {
              ...current,
              findings: current.findings.map((item) =>
                item.finding_id === finding.finding_id ? { ...item, in_skip_list: true } : item
              )
            }
          : current
      );
      setStatusMessage("已加入跳读清单");
    } catch (error: unknown) {
      showError(error, "加入跳读清单失败");
    }
  };

  const openContext = async (finding: ScanFinding) => {
    if (!report) {
      return;
    }
    setContextState({ finding, response: null, isLoading: true, error: "" });
    try {
      const response = await apiClient.getTriggerScanFindingContext(
        report.project_slug,
        report.report_id,
        finding.finding_id,
        9999,
        9999
      );
      setContextState({ finding, response, isLoading: false, error: "" });
    } catch (error: unknown) {
      setContextState({
        finding,
        response: null,
        isLoading: false,
        error: error instanceof Error ? error.message : "加载上下文失败"
      });
    }
  };

  const updateSkipDraft = <K extends keyof SkipListItem>(key: K, value: SkipListItem[K]) => {
    setSkipDraft((current) => ({ ...current, [key]: value }));
  };

  const addManualSkipItem = async () => {
    if (!selectedProjectSlug || !skipDraft.chapter_file.trim() || !skipDraft.rule_name.trim()) {
      dispatch({ type: "set_error", message: "请填写章节文件和雷点名称" });
      return;
    }
    try {
      const item = {
        ...skipDraft,
        source_finding_id: skipDraft.source_finding_id || randomId("manual_skip")
      };
      const saved = await apiClient.addTriggerScanSkipItem(selectedProjectSlug, item);
      setSkipList(saved);
      setSkipDraft(emptySkipDraft);
      setStatusMessage("跳读条目已添加");
    } catch (error: unknown) {
      showError(error, "添加跳读条目失败");
    }
  };

  const updateSkipItem = async (item: SkipListItem, userNote: string) => {
    if (!selectedProjectSlug || !item.source_finding_id) {
      return;
    }
    try {
      const updated = await apiClient.updateTriggerScanSkipItem(
        selectedProjectSlug,
        item.source_finding_id,
        { user_note: userNote }
      );
      setSkipList((current) =>
        current
          ? {
              ...current,
              items: current.items.map((entry) =>
                entry.source_finding_id === updated.source_finding_id ? updated : entry
              ),
              grouped: undefined
            }
          : current
      );
      setStatusMessage("跳读备注已保存");
    } catch (error: unknown) {
      showError(error, "保存跳读备注失败");
    }
  };

  const deleteSkipItem = async (item: SkipListItem) => {
    if (!selectedProjectSlug || !item.source_finding_id) {
      return;
    }
    try {
      const saved = await apiClient.deleteTriggerScanSkipItem(
        selectedProjectSlug,
        item.source_finding_id
      );
      setSkipList(saved);
      setStatusMessage("跳读条目已删除");
    } catch (error: unknown) {
      showError(error, "删除跳读条目失败");
    }
  };

  const exportSkipList = async () => {
    if (!selectedProjectSlug) {
      return;
    }
    try {
      const exported = await apiClient.exportTriggerScanSkipList(selectedProjectSlug);
      setStatusMessage(`已导出：${exported.path}`);
    } catch (error: unknown) {
      showError(error, "导出跳读清单失败");
    }
  };

  const ruleOptions = useMemo(() => {
    const rules = new Map<string, string>();
    report?.findings.forEach((finding) => {
      rules.set(finding.rule_id, finding.rule_name);
    });
    return Array.from(rules.entries()).map(([value, label]) => ({ value, label }));
  }, [report?.findings]);

  const filteredFindings = useMemo(() => {
    const chapterFilter = filters.chapterText.trim().toLocaleLowerCase();
    return (report?.findings ?? []).filter((finding) => {
      if (filters.ruleId && finding.rule_id !== filters.ruleId) {
        return false;
      }
      if (filters.reviewStatus && finding.review_status !== filters.reviewStatus) {
        return false;
      }
      if (finding.severity < filters.minSeverity) {
        return false;
      }
      if (finding.confidence < filters.minConfidence) {
        return false;
      }
      if (chapterFilter) {
        const chapterText = `${finding.chapter_file} ${finding.chapter_title}`.toLocaleLowerCase();
        if (!chapterText.includes(chapterFilter)) {
          return false;
        }
      }
      if (filters.mainPlot === "main" && !finding.is_main_plot) {
        return false;
      }
      if (filters.mainPlot === "side" && finding.is_main_plot) {
        return false;
      }
      if (filters.highRiskOnly && finding.severity < 4 && finding.confidence < 0.8) {
        return false;
      }
      return true;
    });
  }, [filters, report?.findings]);

  const totalPages = Math.max(1, Math.ceil(filteredFindings.length / pageSize));
  const pagedFindings = useMemo(
    () => filteredFindings.slice((findingPage - 1) * pageSize, findingPage * pageSize),
    [filteredFindings, findingPage, pageSize]
  );
  // Reset to page 1 when filters or pageSize change
  useEffect(() => { setFindingPage(1); }, [filters, pageSize]);

  const visibleEvents = useMemo(() => {
    if (!report) {
      return [];
    }
    const visibleFindingIds = new Set(filteredFindings.map((finding) => finding.finding_id));
    const filtering =
      filters.ruleId ||
      filters.reviewStatus ||
      filters.minSeverity > 1 ||
      filters.minConfidence > 0 ||
      filters.chapterText.trim() ||
      filters.mainPlot !== "all" ||
      filters.highRiskOnly;
    return report.events.filter((event) => {
      if (!filtering) {
        return true;
      }
      return event.finding_ids.some((findingId) => visibleFindingIds.has(findingId));
    });
  }, [filteredFindings, filters, report]);

  const skipGroups = useMemo(() => {
    const grouped: Record<string, SkipListItem[]> = {};
    (skipList?.items ?? []).forEach((item) => {
      grouped[item.chapter_file] = [...(grouped[item.chapter_file] ?? []), item];
    });
    return grouped;
  }, [skipList?.items]);

  const renderProfileTab = () => {
    const visibleRules = profileDraft
      ? activeGroupId === null
        ? profileDraft.rules
        : profileDraft.rules.filter((rule) => rule.group_id === activeGroupId)
      : [];
    const activeGroup = profileDraft?.rule_groups.find((g) => g.id === activeGroupId) ?? null;

    return (
      <section className="trigger-grid">
        <aside className="trigger-side-panel">
          <div className="trigger-side-header">
            <strong>雷点档案</strong>
            <span>{profiles.length} 个</span>
          </div>
          <div className="trigger-list">
            {profiles.length === 0 ? (
              <span className="empty-state">暂无档案</span>
            ) : (
              profiles.map((profile) => (
                <button
                  aria-current={profile.id === selectedProfileId ? "true" : undefined}
                  className="trigger-list-button"
                  key={profile.id}
                  onClick={() => setSelectedProfileId(profile.id)}
                  type="button"
                >
                  <span>{profile.name}</span>
                  <small>{profile.rules.filter((rule) => rule.enabled).length} 条启用规则</small>
                </button>
              ))
            )}
          </div>
          <div className="command-row">
            <button className="secondary-command secondary-command--compact" onClick={createProfile} type="button">
              <Plus size={16} />
              <span>新建</span>
            </button>
            <button
              className="secondary-command secondary-command--compact"
              disabled={!selectedProfile}
              onClick={duplicateProfile}
              type="button"
            >
              <Copy size={16} />
              <span>复制</span>
            </button>
            <button
              className="danger-command"
              disabled={!selectedProfile}
              onClick={deleteProfile}
              type="button"
            >
              <Trash2 size={16} />
              <span>删除</span>
            </button>
          </div>
          <div className="command-row">
            <button
              className="secondary-command secondary-command--compact"
              disabled={!profileDraft}
              onClick={exportProfile}
              type="button"
            >
              <FileDown size={16} />
              <span>导出</span>
            </button>
            <button
              className="secondary-command secondary-command--compact"
              onClick={() => importFileRef.current?.click()}
              type="button"
            >
              <FileUp size={16} />
              <span>导入</span>
            </button>
            <input
              accept=".json"
              onChange={handleImportFileChange}
              ref={importFileRef}
              style={{ display: "none" }}
              type="file"
            />
          </div>
        </aside>

        <div className="trigger-editor-panel">
          {profileDraft ? (
            <>
              <header className="config-card__header">
                <h3>{profileDraft.name || "未命名档案"}</h3>
                <div className="command-row">
                  <button className="secondary-command secondary-command--compact" onClick={addGroup} type="button">
                    <Plus size={16} />
                    <span>分组</span>
                  </button>
                  <button
                    className="primary-command"
                    disabled={!profileDirty}
                    onClick={saveProfile}
                    type="button"
                  >
                    <Save size={17} />
                    <span>保存档案</span>
                  </button>
                </div>
              </header>
              <div className="form-grid form-grid--two">
                <TextInput
                  label="档案名称"
                  onChange={(event) => updateProfileDraft("name", event.target.value)}
                  value={profileDraft.name}
                />
                <TextInput
                  label="说明"
                  onChange={(event) => updateProfileDraft("description", event.target.value)}
                  value={profileDraft.description}
                />
              </div>

              {/* Group tabs */}
              <div className="rule-group-tabs">
                <button
                  aria-selected={activeGroupId === null ? "true" : undefined}
                  className="rule-group-tab"
                  onClick={() => setActiveGroupId(null)}
                  type="button"
                >
                  全部
                  <small>
                    {profileDraft.rules.filter((r) => r.enabled).length}/{profileDraft.rules.length}
                  </small>
                </button>
                {profileDraft.rule_groups.map((group) => {
                  const groupRules = profileDraft.rules.filter((r) => r.group_id === group.id);
                  const enabledCount = groupRules.filter((r) => r.enabled).length;
                  return (
                    <button
                      aria-selected={activeGroupId === group.id ? "true" : undefined}
                      className="rule-group-tab"
                      key={group.id}
                      onClick={() => setActiveGroupId(group.id)}
                      type="button"
                    >
                      {group.name}
                      <small>{enabledCount}/{groupRules.length}</small>
                    </button>
                  );
                })}
              </div>

              {/* Active group edit bar */}
              {activeGroup ? (
                <div className="rule-group-edit">
                  <TextInput
                    label="分组名称"
                    onChange={(event) => updateGroup(activeGroup.id, { name: event.target.value })}
                    value={activeGroup.name}
                  />
                  <button
                    className="secondary-command secondary-command--compact"
                    onClick={() => addRule(activeGroup.id)}
                    type="button"
                  >
                    <Plus size={16} />
                    <span>规则</span>
                  </button>
                  <button
                    className="danger-command"
                    onClick={() => {
                      deleteGroup(activeGroup.id);
                      setActiveGroupId(null);
                    }}
                    type="button"
                  >
                    <Trash2 size={16} />
                    <span>删除分组</span>
                  </button>
                </div>
              ) : null}

              {/* Expand / Collapse all */}
              {visibleRules.length > 0 ? (
                <div className="command-row">
                  <button className="secondary-command secondary-command--compact" onClick={expandAllRules} type="button">
                    <span>全部展开</span>
                  </button>
                  <button className="secondary-command secondary-command--compact" onClick={collapseAllRules} type="button">
                    <span>全部折叠</span>
                  </button>
                  {activeGroupId === null ? (
                    <button
                      className="secondary-command secondary-command--compact"
                      onClick={() => {
                        const groupId = profileDraft.rule_groups[0]?.id;
                        if (groupId) addRule(groupId);
                      }}
                      disabled={profileDraft.rule_groups.length === 0}
                      type="button"
                    >
                      <Plus size={16} />
                      <span>规则</span>
                    </button>
                  ) : null}
                </div>
              ) : null}

              {/* Rule cards */}
              {visibleRules.length === 0 ? (
                <span className="empty-state">
                  {activeGroup ? "此分组暂无规则" : "暂无规则，请添加分组和规则"}
                </span>
              ) : (
                <div className="rule-card-list">
                  {visibleRules.map((rule) => {
                    const isExpanded = expandedRules.has(rule.id);
                    return (
                      <section className="rule-card" key={rule.id}>
                        <div
                          className="rule-card__summary"
                          onClick={() => toggleRuleExpanded(rule.id)}
                        >
                          <strong>{rule.name || "未命名规则"}</strong>
                          <div className="rule-card__summary-tags">
                            <span className="rule-card__summary-tag">
                              {matchingPolicyLabel(rule.matching_policy)}
                            </span>
                            <span className="rule-card__summary-tag">
                              阈值 {rule.severity_threshold}
                            </span>
                            {!rule.enabled ? (
                              <span className="rule-card__summary-tag rule-card__summary-tag--disabled">
                                已禁用
                              </span>
                            ) : null}
                          </div>
                          <ToggleSwitch
                            checked={rule.enabled}
                            label=""
                            onChange={(checked) => {
                              updateRule(rule.id, "enabled", checked);
                            }}
                          />
                          <button
                            className={classNames(
                              "rule-card__expand-btn",
                              isExpanded && "rule-card__expand-btn--open"
                            )}
                            onClick={(e) => {
                              e.stopPropagation();
                              toggleRuleExpanded(rule.id);
                            }}
                            type="button"
                          >
                            <ChevronDown size={16} />
                          </button>
                        </div>
                        {isExpanded ? (
                          <div className="rule-card__body">
                            <div className="form-grid form-grid--two">
                              <TextInput
                                label="规则名称"
                                onChange={(event) => updateRule(rule.id, "name", event.target.value)}
                                value={rule.name}
                              />
                              <SelectField
                                label="所属分组"
                                onChange={(event) =>
                                  updateRule(rule.id, "group_id", event.target.value)
                                }
                                options={profileDraft.rule_groups.map((item) => ({
                                  label: item.name,
                                  value: item.id
                                }))}
                                value={rule.group_id}
                              />
                              <SelectField
                                label="匹配策略"
                                onChange={(event) =>
                                  updateRule(
                                    rule.id,
                                    "matching_policy",
                                    event.target.value as TriggerMatchingPolicy
                                  )
                                }
                                options={matchingPolicyOptions}
                                value={rule.matching_policy}
                              />
                              <NumberInput
                                label="严重度阈值"
                                max={5}
                                min={1}
                                onChange={(event) =>
                                  updateRule(
                                    rule.id,
                                    "severity_threshold",
                                    Number(event.target.value || "1")
                                  )
                                }
                                value={rule.severity_threshold}
                              />
                            </div>
                            <TextAreaField
                              label="描述"
                              onChange={(event) => updateRule(rule.id, "description", event.target.value)}
                              value={rule.description}
                            />
                            <div className="form-grid form-grid--two">
                              <TextAreaField
                                label="正例"
                                onChange={(event) =>
                                  updateRule(rule.id, "examples", splitLines(event.target.value))
                                }
                                value={joinLines(rule.examples)}
                              />
                              <TextAreaField
                                label="反例"
                                onChange={(event) =>
                                  updateRule(rule.id, "negative_examples", splitLines(event.target.value))
                                }
                                value={joinLines(rule.negative_examples)}
                              />
                            </div>
                            <div className="command-row">
                              <button
                                className="danger-command"
                                onClick={() => deleteRule(rule.id)}
                                type="button"
                              >
                                <Trash2 size={16} />
                                <span>删除规则</span>
                              </button>
                            </div>
                          </div>
                        ) : null}
                      </section>
                    );
                  })}
                </div>
              )}
            </>
          ) : (
            <span className="empty-state">请选择或新建雷点档案。</span>
          )}
        </div>
      </section>
    );
  };

  const renderScanTab = () => (
    <div className="scan-config-stack">
      <section className="config-card">
        <header className="config-card__header">
          <h3>项目与档案</h3>
          <div className="command-row">
            <button className="secondary-command secondary-command--compact" onClick={() => void loadProjects()} type="button">
              <RefreshCw size={16} />
              <span>刷新</span>
            </button>
            <button
              className="secondary-command secondary-command--compact"
              disabled={!selectedProject?.requires_granularity_migration}
              onClick={() => void migrateProject()}
              type="button"
            >
              <ListChecks size={16} />
              <span>迁移</span>
            </button>
          </div>
        </header>
        <div className="form-grid form-grid--two">
          <SelectField
            hint="可选择小说总结或章节分割项目。"
            label="扫描项目"
            onChange={(event) => setSelectedProjectSlug(event.target.value)}
            options={scanProjects.map((project) => ({
              label: `${project.project_name} · ${workflowLabel(project)}`,
              value: project.project_slug
            }))}
            value={selectedProjectSlug}
          />
          <SelectField
            label="雷点档案"
            onChange={(event) => setSelectedProfileId(event.target.value)}
            options={profiles.map((profile) => ({ label: profile.name, value: profile.id }))}
            value={selectedProfileId}
          />
        </div>
        <div className="form-grid form-grid--two">
          <SelectField
            hint="选择历史报告以继续扫描未完成章节，或留空开始全新扫描。"
            label="续扫报告"
            onChange={async (event) => {
              const reportId = event.target.value;
              setResumeReportId(reportId);
              setPrecheck(null);
              if (reportId) {
                try {
                  const loadedReport = await apiClient.getTriggerScanReport(selectedProjectSlug, reportId);
                  const cfg = loadedReport.scan_config;
                  setRangeStart(cfg.scan_range?.start ?? 1);
                  setRangeEnd(cfg.scan_range?.end ?? "");
                  setScanApiIds(cfg.scan_api_ids ?? []);
                  setMinConfidence(cfg.min_confidence ?? 0.45);
                  setKeepLowConfidence(cfg.keep_low_confidence ?? false);
                  setVerificationEnabled(cfg.verification_enabled ?? true);
                  setVerificationApiId(cfg.verification_api_id ?? "");
                  setPreciseChapterBatchSize(cfg.precise_chapter_batch_size ?? 5);
                  setVerificationChapterBatchSize(cfg.verification_chapter_batch_size ?? 5);
                  setMaxQuoteChars(cfg.max_quote_chars ?? 80);
                  setGenerateSkipAdvice(cfg.generate_skip_advice ?? true);
                  setMinimumOutputCharacters(cfg.minimum_output_characters ?? 0);
                  setStatusMessage("已加载续扫报告配置");
                } catch { /* ignore load error */ }
              }
            }}
            options={[
              { label: "全新扫描", value: "" },
              ...reports
                .filter((r) => r.status !== "completed")
                .map((r) => ({
                  label: `${formatTime(r.created_at)} · ${r.profile_name} · ${r.finding_count}条 · ${statusText(r.status)}`,
                  value: r.report_id
                }))
            ]}
            value={resumeReportId}
          />
        </div>
        {selectedProject?.requires_granularity_migration ? (
          <span className="field-hint field-hint--warning">
            检测到旧版多章合并文件，需要迁移为单章文件后才能扫描。
          </span>
        ) : null}
      </section>

      <section className="config-card">
        <header className="config-card__header">
          <h3>扫描参数</h3>
          <button
            className="secondary-command secondary-command--compact"
            disabled={!selectedProjectSlug}
            onClick={() => void saveConfig()}
            type="button"
          >
            <Save size={16} />
            <span>保存配置</span>
          </button>
        </header>
        <div className="form-grid form-grid--two">
          <SelectField
            label="二次验证 API"
            onChange={(event) => setVerificationApiId(event.target.value)}
            options={activeApis.map((config) => ({
              label: apiDisplayName(config),
              value: config.id
            }))}
            value={verificationApiId}
          />
          <NumberInput
            label="起始章节"
            min={1}
            onChange={(event) => {
              setRangeStart(Number(event.target.value || "1"));
              setPrecheck(null);
            }}
            value={rangeStart}
          />
          <NumberInput
            label="结束章节"
            min={1}
            onChange={(event) => {
              setRangeEnd(event.target.value ? Number(event.target.value) : "");
              setPrecheck(null);
            }}
            placeholder="留空为最后一章"
            value={rangeEnd}
          />
          <NumberInput
            label="最低置信度"
            max={1}
            min={0}
            onChange={(event) => setMinConfidence(Number(event.target.value || "0"))}
            step={0.05}
            value={minConfidence}
          />
          <NumberInput
            label="证据引用字数"
            min={1}
            onChange={(event) => setMaxQuoteChars(Number(event.target.value || "80"))}
            value={maxQuoteChars}
          />
          <NumberInput
            label="最少输出字数"
            min={0}
            onChange={(event) => setMinimumOutputCharacters(Number(event.target.value || "0"))}
            value={minimumOutputCharacters}
          />
          <NumberInput
            label="精扫每批章节"
            min={1}
            onChange={(event) => {
              setPreciseChapterBatchSize(Number(event.target.value || "5"));
              setPrecheck(null);
            }}
            value={preciseChapterBatchSize}
          />
          <NumberInput
            label="验证每批章节"
            min={1}
            onChange={(event) => {
              setVerificationChapterBatchSize(Number(event.target.value || "5"));
              setPrecheck(null);
            }}
            value={verificationChapterBatchSize}
          />
        </div>
        <div className="option-band option-band--split">
          <ToggleSwitch
            checked={keepLowConfidence}
            label="保留低置信度"
            onChange={setKeepLowConfidence}
          />
          <ToggleSwitch
            checked={verificationEnabled}
            label="二次验证"
            onChange={setVerificationEnabled}
          />
          <ToggleSwitch
            checked={generateSkipAdvice}
            label="生成跳读建议"
            onChange={setGenerateSkipAdvice}
          />
        </div>
      </section>

      <section className="config-card">
        <header className="config-card__header">
          <h3>扫描 API</h3>
          <span className="field-hint">{scanApiIds.length} 个已选</span>
        </header>
        {activeApis.length === 0 ? (
          <span className="empty-state">暂无启用 API，请先在「API 配置」页启用。</span>
        ) : (
          <div className="checkbox-list">
            {activeApis.map((config) => (
              <label className="check-row" key={config.id}>
                <input
                  checked={scanApiIds.includes(config.id)}
                  onChange={(event) => toggleScanApi(config.id, event.target.checked)}
                  type="checkbox"
                />
                <span>{apiDisplayName(config)}</span>
              </label>
            ))}
          </div>
        )}
      </section>

      <section className="config-card">
        <header className="config-card__header">
          <h3>启动检查</h3>
          <div className="command-row">
            <button
              className="secondary-command"
              disabled={!canPrecheck}
              onClick={() => void runPrecheck()}
              type="button"
            >
              <Search size={17} />
              <span>预检</span>
            </button>
            <button
              className="secondary-command"
              disabled={latestTriggerTask?.status !== "paused"}
              onClick={() => void controlTriggerTask("resume")}
              type="button"
            >
              <Play size={17} />
              <span>恢复</span>
            </button>
            <button
              className="secondary-command"
              disabled={!latestTriggerTask || !["pending", "running", "paused"].includes(latestTriggerTask.status)}
              onClick={() => void controlTriggerTask("cancel")}
              type="button"
            >
              <Square size={16} />
              <span>取消</span>
            </button>
            <button
              className="primary-command"
              disabled={!canStart}
              onClick={() => void startScan()}
              type="button"
            >
              <ShieldAlert size={17} />
              <span>开始扫描</span>
            </button>
          </div>
        </header>
        {precheck ? (
          <div className="precheck-panel">
            <div className="result-panel result-panel--compact">
              <strong>{precheck.ready ? "预检通过" : "需要处理"}</strong>
              <span>
                {precheck.pending_chapter_count > 0 && precheck.pending_chapter_count < precheck.selected_chapter_count
                  ? `${precheck.pending_chapter_count} 章待扫描（已完成 ${precheck.completed_chapter_count} 章）`
                  : `${precheck.selected_chapter_count}/${precheck.chapter_count} 章将被扫描`}
              </span>
            </div>
            {precheck.errors.length > 0 ? (
              <div className="precheck-list precheck-list--error">
                {precheck.errors.map((error) => (
                  <span key={error}>{error}</span>
                ))}
              </div>
            ) : null}
            {precheck.warnings.length > 0 ? (
              <div className="precheck-list">
                {precheck.warnings.map((warning) => (
                  <span key={warning}>{warning}</span>
                ))}
              </div>
            ) : null}
            {precheck.decisions.length > 0 ? (
              <div className="command-row">
                {precheck.decisions.includes("migrate_chapter_granularity") ? (
                  <button className="secondary-command secondary-command--compact" onClick={() => void migrateProject()} type="button">
                    <ListChecks size={16} />
                    <span>迁移项目</span>
                  </button>
                ) : null}
                <button className="secondary-command secondary-command--compact" onClick={() => setPrecheck(null)} type="button">
                  <X size={16} />
                  <span>取消决策</span>
                </button>
              </div>
            ) : null}
          </div>
        ) : (
          <span className="empty-state">点击预检后会显示扫描前置检查结果。</span>
        )}
      </section>

      <section className="config-card">
        <header className="config-card__header">
          <h3>实时进度</h3>
          <span className={`status-pill status-pill--${latestTriggerTask?.status ?? "idle"}`}>
            {statusText(latestTriggerTask?.status ?? "")}
          </span>
        </header>
        {latestTriggerTask ? (
          <>
            {scanStages.length > 0 && (
              <StageProgressBar stages={scanStages} currentStage={scanCurrentStage} />
            )}
            <div className="project-progress-panel">
              <header>
                <strong>{latestTriggerTask.progress_text || latestTriggerTask.task_id}</strong>
                <span>{latestTriggerTask.result_summary || latestTriggerTask.error || "等待事件"}</span>
              </header>
              <div className="progress-event-list">
                {triggerEvents.slice(-8).map((event) => (
                  <div className="progress-event-row" key={`${event.task_id}-${event.timestamp}-${event.message}`}>
                    <span>{event.progress_text || event.event_type}</span>
                    <strong>{event.message}</strong>
                  </div>
                ))}
              </div>
            </div>
            {liveFindings.length > 0 ? (
              <div className="live-finding-list">
                {liveFindings.map((finding) => (
                  <div className="result-panel result-panel--compact" key={finding.finding_id}>
                    <strong>{finding.rule_name}</strong>
                    <span>
                      {pathName(finding.chapter_file)} · 严重度 {finding.severity} · 置信度{" "}
                      {finding.confidence.toFixed(2)}
                    </span>
                  </div>
                ))}
              </div>
            ) : null}
          </>
        ) : (
          <span className="empty-state">暂无雷点扫描任务。</span>
        )}
      </section>
    </div>
  );

  const renderFindingActions = (finding: ScanFinding) => {
    const selectedSpoiler = itemSpoilers[finding.finding_id] ?? globalSpoiler;
    const noteValue = notes[finding.finding_id] ?? finding.user_note;
    return (
      <div className="finding-actions">
        <div className="spoiler-toggle">
          {spoilerOptions.map((opt) => (
            <button
              key={opt.value}
              aria-pressed={selectedSpoiler === opt.value ? "true" : undefined}
              onClick={() =>
                setItemSpoilers((current) => ({
                  ...current,
                  [finding.finding_id]: opt.value as SpoilerLevel
                }))
              }
              type="button"
            >
              {opt.label}
            </button>
          ))}
        </div>
        <TextInput
          label="备注"
          onChange={(event) =>
            setNotes((current) => ({ ...current, [finding.finding_id]: event.target.value }))
          }
          value={noteValue}
        />
        <div className="command-row">
          <button
            className="secondary-command secondary-command--compact"
            onClick={() => void updateFinding(finding, { review_status: "confirmed" })}
            type="button"
          >
            <Check size={16} />
            <span>确认</span>
          </button>
          <button
            className="secondary-command secondary-command--compact"
            onClick={() => void updateFinding(finding, { review_status: "false_positive" })}
            type="button"
          >
            <X size={16} />
            <span>误报</span>
          </button>
          <button
            className="secondary-command secondary-command--compact"
            onClick={() => void updateFinding(finding, { user_note: noteValue })}
            type="button"
          >
            <Save size={16} />
            <span>备注</span>
          </button>
          <button className="secondary-command secondary-command--compact" onClick={() => void openContext(finding)} type="button">
            <Eye size={16} />
            <span>上下文</span>
          </button>
          <button
            className="secondary-command secondary-command--compact"
            disabled={finding.in_skip_list}
            onClick={() => void addFindingToSkipList(finding)}
            type="button"
          >
            <ListChecks size={16} />
            <span>{finding.in_skip_list ? "已加入" : "跳读"}</span>
          </button>
        </div>
      </div>
    );
  };

  const renderResultsTab = () => (
    <div className="scan-config-stack">
      <section className="config-card">
        <header className="config-card__header">
          <h3>报告历史</h3>
          <div className="command-row">
            <button className="secondary-command secondary-command--compact" onClick={() => void refreshReports()} type="button">
              <RefreshCw size={16} />
              <span>刷新</span>
            </button>
            <button className="secondary-command secondary-command--compact" disabled={!report} onClick={() => void exportReport("md")} type="button">
              <FileDown size={16} />
              <span>MD</span>
            </button>
            <button className="secondary-command secondary-command--compact" disabled={!report} onClick={() => void exportReport("json")} type="button">
              <FileDown size={16} />
              <span>JSON</span>
            </button>
            <button className="danger-command" disabled={!report} onClick={() => void deleteReport()} type="button">
              <Trash2 size={16} />
              <span>删除</span>
            </button>
          </div>
        </header>
        <div className="form-grid form-grid--two">
          <SelectField
            label="历史报告"
            onChange={(event) => setSelectedReportId(event.target.value)}
            options={reports.map((item) => ({
              label: `${formatTime(item.created_at)} · ${item.profile_name} · ${item.finding_count} 条 · ${item.status}`,
              value: item.report_id
            }))}
            value={selectedReportId}
          />
        </div>
        <div style={{ marginBottom: 16 }}>
          <span style={{ fontSize: 12, color: "var(--color-muted)", marginRight: 8 }}>全局剧透</span>
          <div className="spoiler-toggle">
            {spoilerOptions.map((opt) => (
              <button
                key={opt.value}
                aria-pressed={globalSpoiler === opt.value ? "true" : undefined}
                onClick={() => setGlobalSpoiler(opt.value as SpoilerLevel)}
                type="button"
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>
        <span className="field-hint field-hint--warning">
          AI 扫描结果仅供辅助参考，不能保证覆盖所有雷点或完全避免误判。
        </span>
      </section>

      {report ? (
        <>
          <section className="result-summary-grid">
            <div className="result-panel">
              <strong>发现条目</strong>
              <span>{report.summary.total_findings}</span>
            </div>
            <div className="result-panel">
              <strong>已确认</strong>
              <span>{report.summary.verified_findings}</span>
            </div>
            <div className="result-panel">
              <strong>待复核</strong>
              <span>{report.summary.pending_review}</span>
            </div>
            <div className="result-panel">
              <strong>状态</strong>
              <span>{statusText(report.status)}</span>
            </div>
          </section>

          <section className="config-card">
            <header className="config-card__header">
              <h3>筛选</h3>
              <div className="command-row">
                <button
                  aria-pressed={resultView === "events"}
                  className="secondary-command secondary-command--compact"
                  onClick={() => setResultView("events")}
                  type="button"
                >
                  <span>事件视图</span>
                </button>
                <button
                  aria-pressed={resultView === "findings"}
                  className="secondary-command secondary-command--compact"
                  onClick={() => setResultView("findings")}
                  type="button"
                >
                  <span>逐条视图</span>
                </button>
                <button
                  className="secondary-command secondary-command--compact"
                  onClick={() => setFilters(emptyFilters)}
                  type="button"
                >
                  <X size={16} />
                  <span>清空</span>
                </button>
              </div>
            </header>
            <div className="form-grid form-grid--two">
              <SelectField
                label="雷点类型"
                onChange={(event) => setFilters((current) => ({ ...current, ruleId: event.target.value }))}
                options={[{ label: "全部", value: "" }, ...ruleOptions]}
                value={filters.ruleId}
              />
              <SelectField
                label="复核状态"
                onChange={(event) =>
                  setFilters((current) => ({ ...current, reviewStatus: event.target.value }))
                }
                options={reviewOptions}
                value={filters.reviewStatus}
              />
              <NumberInput
                label="最低严重度"
                max={5}
                min={1}
                onChange={(event) =>
                  setFilters((current) => ({
                    ...current,
                    minSeverity: Number(event.target.value || "1")
                  }))
                }
                value={filters.minSeverity}
              />
              <NumberInput
                label="最低置信度"
                max={1}
                min={0}
                onChange={(event) =>
                  setFilters((current) => ({
                    ...current,
                    minConfidence: Number(event.target.value || "0")
                  }))
                }
                step={0.05}
                value={filters.minConfidence}
              />
              <TextInput
                label="章节过滤"
                onChange={(event) =>
                  setFilters((current) => ({ ...current, chapterText: event.target.value }))
                }
                value={filters.chapterText}
              />
              <SelectField
                label="主线"
                onChange={(event) =>
                  setFilters((current) => ({
                    ...current,
                    mainPlot: event.target.value as ResultFilters["mainPlot"]
                  }))
                }
                options={[
                  { label: "全部", value: "all" },
                  { label: "主线", value: "main" },
                  { label: "非主线", value: "side" }
                ]}
                value={filters.mainPlot}
              />
            </div>
            <ToggleSwitch
              checked={filters.highRiskOnly}
              label="仅显示高置信雷点"
              onChange={(checked) =>
                setFilters((current) => ({ ...current, highRiskOnly: checked }))
              }
            />
            <span className="field-hint">严重度 ≥ 4 且置信度 ≥ 0.8</span>
          </section>

          {resultView === "events" ? (
            <>
              <div className="command-row" style={{ marginBottom: 8 }}>
                <button
                  className="secondary-command secondary-command--compact"
                  onClick={() => setExpandedEventIds(new Set(visibleEvents.map((e) => e.event_id)))}
                  type="button"
                >
                  <span>全部展开</span>
                </button>
                <button
                  className="secondary-command secondary-command--compact"
                  onClick={() => setExpandedEventIds(new Set())}
                  type="button"
                >
                  <span>全部收起</span>
                </button>
              </div>
              <section className="event-list">
              {visibleEvents.length === 0 ? (
                <span className="empty-state">暂无符合筛选条件的事件。</span>
              ) : (
                visibleEvents.map((event) => {
                  const selectedSpoiler = itemSpoilers[event.event_id] ?? globalSpoiler;
                  const related = event.finding_ids
                    .map((findingId) =>
                      report.findings.find((finding) => finding.finding_id === findingId)
                    )
                    .filter((finding): finding is ScanFinding => Boolean(finding));
                  return (
                    <section className="event-card" key={event.event_id}>
                      <header className="event-card__header">
                        <div>
                          <strong>{event.rule_name}</strong>
                          <span>
                            {event.related_chapters.join("、") || event.first_chapter} · 严重度{" "}
                            {event.max_severity} · 置信度 {event.max_confidence.toFixed(2)}
                          </span>
                        </div>
                        <div className="command-row">
                          <div className="spoiler-toggle">
                            {spoilerOptions.map((opt) => (
                              <button
                                key={opt.value}
                                aria-pressed={selectedSpoiler === opt.value ? "true" : undefined}
                                onClick={() =>
                                  setItemSpoilers((current) => ({
                                    ...current,
                                    [event.event_id]: opt.value as SpoilerLevel
                                  }))
                                }
                                type="button"
                              >
                                {opt.label}
                              </button>
                            ))}
                          </div>
                          <button
                            className="secondary-command secondary-command--compact"
                            onClick={() =>
                              setExpandedEventIds((prev) => {
                                const next = new Set(prev);
                                if (next.has(event.event_id)) next.delete(event.event_id);
                                else next.add(event.event_id);
                                return next;
                              })
                            }
                            type="button"
                          >
                            <Eye size={16} />
                            <span>{expandedEventIds.has(event.event_id) ? "收起" : "展开"}</span>
                          </button>
                        </div>
                      </header>
                      <p className="event-summary-text">{event.event_summary[selectedSpoiler]}</p>
                      {expandedEventIds.has(event.event_id) ? (
                        <div className="finding-card-list">
                          {related.map((finding) => (
                            <section className="finding-card" key={finding.finding_id}>
                              <strong>{pathName(finding.chapter_file)} · {finding.paragraph_ids.join(", ")}</strong>
                              <p>{spoilerText(finding, itemSpoilers[finding.finding_id] ?? globalSpoiler)}</p>
                              {renderFindingActions(finding)}
                            </section>
                          ))}
                        </div>
                      ) : null}
                    </section>
                  );
                })
              )}
            </section>
          </>
          ) : (
            <section className="table-shell">
              {filteredFindings.length === 0 ? (
                <span className="empty-state">暂无符合筛选条件的条目。</span>
              ) : (
                <>
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>规则</th>
                      <th>章节</th>
                      <th>段落</th>
                      <th>风险</th>
                      <th>描述</th>
                      <th>状态</th>
                      <th>操作</th>
                    </tr>
                  </thead>
                  <tbody>
                    {pagedFindings.map((finding) => {
                      const selectedSpoiler = itemSpoilers[finding.finding_id] ?? globalSpoiler;
                      return (
                        <tr key={finding.finding_id}>
                          <td>{finding.rule_name}</td>
                          <td>{pathName(finding.chapter_file)}</td>
                          <td>{finding.paragraph_ids.join(", ")}</td>
                          <td>
                            {finding.severity} / {finding.confidence.toFixed(2)}
                            {finding.is_main_plot ? " / 主线" : ""}
                          </td>
                          <td>
                            <span>{spoilerText(finding, selectedSpoiler)}</span>
                            {selectedSpoiler === "detailed" && evidenceQuote(finding) ? (
                              <small>证据：{evidenceQuote(finding)}</small>
                            ) : null}
                            {skipAdvice(finding, selectedSpoiler) ? (
                              <small>建议：{skipAdvice(finding, selectedSpoiler)}</small>
                            ) : null}
                          </td>
                          <td>{reviewBadge(finding.review_status)}</td>
                          <td>{renderFindingActions(finding)}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
                <div className="command-row" style={{ justifyContent: "center", marginTop: 12, alignItems: "center" }}>
                  <button
                    className="secondary-command secondary-command--compact"
                    disabled={findingPage <= 1}
                    onClick={() => setFindingPage((p) => p - 1)}
                    type="button"
                  >
                    上一页
                  </button>
                  <span style={{ padding: "0 12px", fontSize: 13, color: "var(--color-muted)" }}>
                    {findingPage} / {totalPages}（共 {filteredFindings.length} 条）
                  </span>
                  <button
                    className="secondary-command secondary-command--compact"
                    disabled={findingPage >= totalPages}
                    onClick={() => setFindingPage((p) => p + 1)}
                    type="button"
                  >
                    下一页
                  </button>
                  <span style={{ fontSize: 13, color: "var(--color-muted)", marginLeft: 16 }}>每页</span>
                  <select
                    value={pageSize}
                    onChange={(e) => setPageSize(Number(e.target.value))}
                    style={{ padding: "2px 6px", border: "1px solid var(--color-border)", borderRadius: 4, fontSize: 13 }}
                  >
                    <option value={10}>10</option>
                    <option value={20}>20</option>
                    <option value={50}>50</option>
                    <option value={100}>100</option>
                  </select>
                </div>
              </>)}
            </section>
          )}
        </>
      ) : (
        <section className="config-card">
          <span className="empty-state">请选择项目和历史报告。</span>
        </section>
      )}
    </div>
  );

  const renderSkipTab = () => (
    <div className="scan-config-stack">
      <section className="config-card">
        <header className="config-card__header">
          <h3>跳读清单</h3>
          <div className="command-row">
            <button className="secondary-command secondary-command--compact" onClick={() => void loadSkipList()} type="button">
              <RefreshCw size={16} />
              <span>刷新</span>
            </button>
            <button className="secondary-command secondary-command--compact" disabled={!selectedProjectSlug} onClick={() => void exportSkipList()} type="button">
              <FileDown size={16} />
              <span>导出 MD</span>
            </button>
          </div>
        </header>
        <div className="form-grid form-grid--two">
          <TextInput
            label="章节文件"
            onChange={(event) => updateSkipDraft("chapter_file", event.target.value)}
            value={skipDraft.chapter_file}
          />
          <TextInput
            label="章节标题"
            onChange={(event) => updateSkipDraft("chapter_title", event.target.value)}
            value={skipDraft.chapter_title}
          />
          <TextInput
            label="段落范围"
            onChange={(event) => updateSkipDraft("paragraph_range", event.target.value)}
            value={skipDraft.paragraph_range}
          />
          <TextInput
            label="雷点名称"
            onChange={(event) => updateSkipDraft("rule_name", event.target.value)}
            value={skipDraft.rule_name}
          />
          <NumberInput
            label="严重度"
            max={5}
            min={1}
            onChange={(event) => updateSkipDraft("severity", Number(event.target.value || "1"))}
            value={skipDraft.severity}
          />
          <TextInput
            label="备注"
            onChange={(event) => updateSkipDraft("user_note", event.target.value)}
            value={skipDraft.user_note}
          />
        </div>
        <div className="command-row">
          <button className="secondary-command" disabled={!selectedProjectSlug} onClick={() => void addManualSkipItem()} type="button">
            <Plus size={17} />
            <span>添加条目</span>
          </button>
        </div>
      </section>

      <section className="table-shell">
        {!skipList || skipList.items.length === 0 ? (
          <span className="empty-state">暂无跳读条目。</span>
        ) : (
          Object.entries(skipGroups).map(([chapterFile, items]) => (
            <section className="skip-chapter-group" key={chapterFile}>
              <h3>{chapterFile}</h3>
              <table className="data-table">
                <thead>
                  <tr>
                    <th>段落</th>
                    <th>雷点</th>
                    <th>严重度</th>
                    <th>备注</th>
                    <th>操作</th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((item) => (
                    <tr key={item.source_finding_id || `${item.chapter_file}-${item.rule_name}`}>
                      <td>{item.paragraph_range || "-"}</td>
                      <td>{item.rule_name}</td>
                      <td>{item.severity}</td>
                      <td>
                        <TextInput
                          label="备注"
                          onChange={(event) =>
                            setSkipList((current) =>
                              current
                                ? {
                                    ...current,
                                    items: current.items.map((entry) =>
                                      entry.source_finding_id === item.source_finding_id
                                        ? { ...entry, user_note: event.target.value }
                                        : entry
                                    )
                                  }
                                : current
                            )
                          }
                          value={item.user_note}
                        />
                      </td>
                      <td>
                        <div className="command-row">
                          <button
                            className="secondary-command secondary-command--compact"
                            onClick={() => void updateSkipItem(item, item.user_note)}
                            type="button"
                          >
                            <Save size={16} />
                            <span>保存</span>
                          </button>
                          <button
                            className="danger-command"
                            onClick={() => void deleteSkipItem(item)}
                            type="button"
                          >
                            <Trash2 size={16} />
                            <span>删除</span>
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </section>
          ))
        )}
      </section>
    </div>
  );

  return (
    <section className="workflow-view">
      <div className="view-header">
        <div>
          <h2>雷点扫描</h2>
          <span>{statusMessage || `${scanProjects.length} 个可扫描项目 · ${profiles.length} 个档案`}</span>
        </div>
        <div className="command-row">
          <button className="secondary-command" onClick={() => void loadProfiles()} type="button">
            <RefreshCw size={17} />
            <span>加载档案</span>
          </button>
          <button className="primary-command" disabled={!canStart} onClick={() => void startScan()} type="button">
            <Play size={17} />
            <span>开始</span>
          </button>
        </div>
      </div>

      <GuidancePanel
        title="扫描工作台"
        items={[
          "先维护雷点档案，再选择小说总结或章节分割项目启动扫描。",
          "扫描会直接读取所选章节原文；可通过精扫每批章节控制单次请求规模。",
          "报告中的逐条结果可复核、备注、查看上下文，并加入独立跳读清单。"
        ]}
      />

      <div className="prompt-tabs" role="tablist" aria-label="雷点扫描工作台">
        {triggerTabs.map((tab) => (
          <button
            aria-selected={activeTab === tab.key}
            className="prompt-tab"
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            role="tab"
            type="button"
          >
            <span>{tab.label}</span>
            <small>{tab.meta}</small>
          </button>
        ))}
      </div>

      {activeTab === "profiles" ? renderProfileTab() : null}
      {activeTab === "scan" ? renderScanTab() : null}
      {activeTab === "results" ? renderResultsTab() : null}
      {activeTab === "skip" ? renderSkipTab() : null}

      {contextState ? (
        <div className="modal-backdrop" role="presentation">
          <section className="context-modal" role="dialog" aria-modal="true">
            <header className="context-modal__header">
              <div>
                <h3>{contextState.finding.rule_name}</h3>
                <span>
                  {pathName(contextState.finding.chapter_file)} ·{" "}
                  {contextState.finding.paragraph_ids.join(", ")}
                </span>
              </div>
              <button className="icon-button" onClick={() => setContextState(null)} type="button">
                <X size={18} />
              </button>
            </header>
            {contextState.isLoading ? (
              <span className="empty-state">上下文加载中</span>
            ) : contextState.error ? (
              <span className="field-hint field-hint--warning">{contextState.error}</span>
            ) : contextState.response?.warning ? (
              <span className="field-hint field-hint--warning">
                {contextState.response.warning}
              </span>
            ) : (
              <div className="context-paragraph-list">
                {(contextState.response?.paragraphs ?? []).map((paragraph) => (
                  <p
                    className={classNames("context-paragraph", paragraph.matched && "context-paragraph--matched")}
                    key={paragraph.id}
                  >
                    <strong>{paragraph.id}</strong>
                    <span>{paragraph.text}</span>
                  </p>
                ))}
                {contextState.response?.missing_paragraph_ids?.length ? (
                  <span className="field-hint field-hint--warning">
                    缺失段落：{contextState.response.missing_paragraph_ids.join(", ")}
                  </span>
                ) : null}
              </div>
            )}
          </section>
        </div>
      ) : null}
    </section>
  );
}
