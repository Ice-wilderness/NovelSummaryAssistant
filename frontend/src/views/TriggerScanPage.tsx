import {
  Check,
  ChevronDown,
  Copy,
  Eye,
  FileDown,
  FileUp,
  History,
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
import { IconButton } from "../components/common/IconButton";
import { apiClient } from "../api/client";
import { apiDisplayName } from "../api/display";
import type {
  ProjectRecord,
  ScanFinding,
  ScanReport,
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
import {
  classNames,
  evidenceQuote,
  formatTime,
  isFinding,
  pathName,
  reportStatusText,
  reportWarningMessages,
  reviewStatusText,
  skipAdvice,
  spoilerText,
  statusText,
  workflowLabel
} from "./trigger-scan/display";
import { spoilerOptions, triggerTabs, type ResultView, type TriggerTab } from "./trigger-scan/options";
import {
  cloneProfile,
  createGroup,
  createRule,
  joinLines,
  matchingPolicyLabel,
  matchingPolicyOptions,
  splitLines
} from "./trigger-scan/profileDraft";
import {
  buildRuleOptions,
  emptyFilters,
  filterFindings,
  paginateFindings,
  reviewOptions,
  totalFindingPages,
  type ResultFilters,
  visibleEvents as getVisibleEvents
} from "./trigger-scan/resultFilters";
import { ProfileTab } from "./trigger-scan/ProfileTab";

function reviewBadge(status: string) {
  const cls = `review-badge review-badge--${status}`;
  return <span className={cls}>{reviewStatusText(status)}</span>;
}

function SpoilerToggle({
  value,
  onChange,
}: {
  value: SpoilerLevel;
  onChange: (level: SpoilerLevel) => void;
}) {
  return (
    <div className="spoiler-toggle">
      {spoilerOptions.map((opt) => (
        <button
          key={opt.value}
          aria-pressed={value === opt.value ? "true" : undefined}
          onClick={() => onChange(opt.value)}
          type="button"
        >
          {opt.label}
        </button>
      ))}
    </div>
  );
}

interface ContextState {
  finding: ScanFinding;
  response: TriggerScanContextResponse | null;
  isLoading: boolean;
  error: string;
}

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
  const reportWarnings = useMemo(
    () => (report ? reportWarningMessages(report) : []),
    [report]
  );

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

  const { startTask, watchTask } = useTaskActions({
    onTaskTerminal: () => {
      void refreshReports();
      void loadProjects();
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
  }, [refreshReports, selectedProjectSlug]);

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
        if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });
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

  const deleteReport = async (reportId?: string) => {
    const targetId = reportId || report?.report_id;
    const targetSlug = report?.project_slug;
    if (!targetId || !targetSlug || !window.confirm(`删除报告 ${targetId}？`)) {
      return;
    }
    try {
      await apiClient.deleteTriggerScanReport(targetSlug, targetId);
      if (targetId === selectedReportId) {
        setSelectedReportId("");
        setReport(null);
      }
      await refreshReports(targetSlug);
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
      setReport((current) => {
        if (!current) return current;
        const findings = current.findings.map((item) =>
          item.finding_id === updated.finding_id ? updated : item
        );
        return {
          ...current,
          findings,
          summary: {
            ...current.summary,
            verified_findings: findings.filter((f) => f.review_status === "confirmed").length,
            pending_review: findings.filter((f) => f.review_status === "unreviewed").length
          }
        };
      });
      setStatusMessage("条目已更新");
    } catch (error: unknown) {
      showError(error, "更新条目失败");
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

  const ruleOptions = useMemo(
    () => buildRuleOptions(report?.findings ?? []),
    [report?.findings]
  );

  const filteredFindings = useMemo(
    () => filterFindings(report?.findings ?? [], filters),
    [filters, report?.findings]
  );

  const totalPages = totalFindingPages(filteredFindings.length, pageSize);
  const pagedFindings = useMemo(
    () => paginateFindings(filteredFindings, findingPage, pageSize),
    [filteredFindings, findingPage, pageSize]
  );
  // Reset to page 1 when filters or pageSize change
  useEffect(() => { setFindingPage(1); }, [filters, pageSize]);

  const visibleEvents = useMemo(
    () => (report ? getVisibleEvents(report, filteredFindings, filters) : []),
    [filteredFindings, filters, report]
  );

  // Resolve spoiler level for a finding with optional event-level fallback
  const getFindingSpoiler = useCallback(
    (findingId: string, eventId?: string): SpoilerLevel => {
      return itemSpoilers[findingId] ?? (eventId ? itemSpoilers[eventId] : undefined) ?? globalSpoiler;
    },
    [itemSpoilers, globalSpoiler]
  );

  // Cascade spoiler level to an event and all its findings
  const setEventSpoilerLevel = useCallback(
    (eventId: string, findingIds: string[], level: SpoilerLevel) => {
      setItemSpoilers((current) => {
        const next = { ...current, [eventId]: level };
        for (const fid of findingIds) {
          next[fid] = level;
        }
        return next;
      });
    },
    []
  );

  // Shared body rendering for a finding (used by both event view and table view)
  const renderFindingBody = (finding: ScanFinding, spoilerLevel: SpoilerLevel) => {
    const evidence = spoilerLevel === "detailed" ? evidenceQuote(finding) : "";
    const advice = skipAdvice(finding, spoilerLevel);
    return (
      <>
        <span>{spoilerText(finding, spoilerLevel)}</span>
        {evidence ? <small>证据：{evidence}</small> : null}
        {advice ? <small>建议：{advice}</small> : null}
      </>
    );
  };

  const renderProfileTab = () => (
    <ProfileTab
      activeGroupId={activeGroupId}
      expandedRules={expandedRules}
      importFileRef={importFileRef}
      onAddGroup={addGroup}
      onAddRule={addRule}
      onCollapseAllRules={collapseAllRules}
      onCreateProfile={() => void createProfile()}
      onDeleteGroup={deleteGroup}
      onDeleteProfile={() => void deleteProfile()}
      onDeleteRule={deleteRule}
      onDuplicateProfile={() => void duplicateProfile()}
      onExpandAllRules={expandAllRules}
      onExportProfile={exportProfile}
      onImportFileChange={handleImportFileChange}
      onSaveProfile={() => void saveProfile()}
      onSelectProfile={setSelectedProfileId}
      onSetActiveGroupId={setActiveGroupId}
      onToggleRuleExpanded={toggleRuleExpanded}
      onUpdateGroup={updateGroup}
      onUpdateProfileDraft={updateProfileDraft}
      onUpdateRule={updateRule}
      profileDirty={profileDirty}
      profileDraft={profileDraft}
      profiles={profiles}
      selectedProfile={selectedProfile}
      selectedProfileId={selectedProfileId}
    />
  );

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
        <div className="finding-actions__left">
          <input
            className="text-control finding-actions__note"
            placeholder="备注"
            value={noteValue}
            onChange={(event) =>
              setNotes((current) => ({ ...current, [finding.finding_id]: event.target.value }))
            }
          />
          <button
            className="secondary-command secondary-command--compact"
            onClick={() => void updateFinding(finding, { user_note: noteValue })}
            type="button"
          >
            <Save size={16} />
            <span>备注</span>
          </button>
        </div>
        <div className="finding-actions__right">
          <SpoilerToggle
            value={selectedSpoiler}
            onChange={(level) =>
              setItemSpoilers((current) => ({
                ...current,
                [finding.finding_id]: level,
              }))
            }
          />
          <div className="finding-actions__buttons">
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
            <button className="secondary-command secondary-command--compact" onClick={() => void openContext(finding)} type="button">
              <Eye size={16} />
              <span>上下文</span>
            </button>
          </div>
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
        <div className="history-panel">
          <div className="history-list">
            {reports.length === 0 ? (
              <span className="empty-state">暂无报告。先选择扫描标签页启动扫描。</span>
            ) : (
              reports.map((item) => (
                <div
                  className={classNames(
                    "history-item",
                    selectedReportId === item.report_id && "history-item--active"
                  )}
                  key={item.report_id}
                >
                  <button
                    className="history-item__restore"
                    onClick={() => setSelectedReportId(item.report_id)}
                    type="button"
                  >
                    <span className={`status-pill status-pill--${item.status === "completed" ? "success" : item.status || "idle"}`}>
                      {reportStatusText(item.status)}
                    </span>
                    <span className="history-item__content">
                      <strong title={item.profile_name}>{item.profile_name}</strong>
                      <small>
                        {item.finding_count} 条 · {formatTime(item.created_at)}
                      </small>
                    </span>
                  </button>
                  <IconButton
                    label="删除报告"
                    onClick={() => void deleteReport(item.report_id)}
                  >
                    <Trash2 size={16} />
                  </IconButton>
                </div>
              ))
            )}
          </div>
        </div>
        <div style={{ marginBottom: 16 }}>
          <span style={{ fontSize: 12, color: "var(--color-muted)", marginRight: 8 }}>全局剧透</span>
          <div className="spoiler-toggle">
            {spoilerOptions.map((opt) => (
              <button
                key={opt.value}
                aria-pressed={globalSpoiler === opt.value ? "true" : undefined}
                onClick={() => {
                  setGlobalSpoiler(opt.value as SpoilerLevel);
                  setItemSpoilers({});
                }}
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

          {reportWarnings.length > 0 ? (
            <section className="report-warning-panel" aria-label="扫描报告警告">
              <ShieldAlert size={18} />
              <div>
                {reportWarnings.map((warning) => (
                  <span key={warning}>{warning}</span>
                ))}
              </div>
            </section>
          ) : null}

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
                    .filter((finding): finding is ScanFinding => Boolean(finding))
                    .filter((finding) => {
                      if (filters.reviewStatus && finding.review_status !== filters.reviewStatus) return false;
                      return true;
                    });
                  return (
                    <section className="event-card" key={event.event_id}>
                      <header className="event-card__header">
                        <div className="event-card__heading">
                          <strong className="event-card__title">{event.rule_name}</strong>
                          <span
                            className="event-card__meta"
                            title={(event.related_chapters.join("、") || event.first_chapter) + ` · 严重度 ${event.max_severity} · 置信度 ${event.max_confidence.toFixed(2)}`}
                          >
                            {event.related_chapters.join("、") || event.first_chapter} · 严重度{" "}
                            {event.max_severity} · 置信度 {event.max_confidence.toFixed(2)}
                          </span>
                        </div>
                        <div className="event-card__actions">
                          <SpoilerToggle
                            value={selectedSpoiler}
                            onChange={(level) =>
                              setEventSpoilerLevel(event.event_id, event.finding_ids, level)
                            }
                          />
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
                          {related.map((finding) => {
                            const findingSpoiler = getFindingSpoiler(finding.finding_id, event.event_id);
                            return (
                              <section className="finding-card" key={finding.finding_id}>
                                <header className="finding-card__header">
                                  <strong>{pathName(finding.chapter_file)} · {finding.paragraph_ids.join(", ")}</strong>
                                  {reviewBadge(finding.review_status)}
                                </header>
                                <div className="finding-card__detail">
                                  {renderFindingBody(finding, findingSpoiler)}
                                </div>
                                {renderFindingActions(finding)}
                              </section>
                            );
                          })}
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
                            {renderFindingBody(finding, selectedSpoiler)}
                          </td>
                          <td>{reviewBadge(finding.review_status)}</td>
                          <td>{renderFindingActions(finding)}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 12, flexWrap: "wrap", gap: 8 }}>
                  <div style={{ fontSize: 13, color: "var(--color-muted)" }}>
                    共 {filteredFindings.length} 条，每页
                    <select
                      value={pageSize}
                      onChange={(e) => setPageSize(Number(e.target.value))}
                      style={{ margin: "0 4px", padding: "2px 6px", border: "1px solid var(--color-border)", borderRadius: 4, fontSize: 13 }}
                    >
                      <option value={10}>10</option>
                      <option value={20}>20</option>
                      <option value={50}>50</option>
                      <option value={100}>100</option>
                    </select>
                    条
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
                    <button
                      className="secondary-command secondary-command--compact"
                      disabled={findingPage <= 1}
                      onClick={() => setFindingPage(1)}
                      type="button"
                      title="首页"
                    >
                      «
                    </button>
                    <button
                      className="secondary-command secondary-command--compact"
                      disabled={findingPage <= 1}
                      onClick={() => setFindingPage((p) => p - 1)}
                      type="button"
                    >
                      ‹
                    </button>
                    {(() => {
                      const pages: Array<number | string> = [];
                      const range = 2; // pages to show around current
                      for (let i = 1; i <= totalPages; i++) {
                        if (i === 1 || i === totalPages || (i >= findingPage - range && i <= findingPage + range)) {
                          pages.push(i);
                        } else if (pages[pages.length - 1] !== "...") {
                          pages.push("...");
                        }
                      }
                      return pages.map((p, idx) =>
                        p === "..." ? (
                          <span key={`ellipsis-${idx}`} style={{ padding: "0 6px", color: "var(--color-muted)" }}>…</span>
                        ) : (
                          <button
                            key={p}
                            className={classNames(
                              "secondary-command secondary-command--compact",
                              findingPage === p && "primary-command"
                            )}
                            onClick={() => setFindingPage(p as number)}
                            type="button"
                            style={findingPage === p ? { fontWeight: 700, minWidth: 32 } : { minWidth: 32 }}
                          >
                            {p}
                          </button>
                        )
                      );
                    })()}
                    <button
                      className="secondary-command secondary-command--compact"
                      disabled={findingPage >= totalPages}
                      onClick={() => setFindingPage((p) => p + 1)}
                      type="button"
                    >
                      ›
                    </button>
                    <button
                      className="secondary-command secondary-command--compact"
                      disabled={findingPage >= totalPages}
                      onClick={() => setFindingPage(totalPages)}
                      type="button"
                      title="末页"
                    >
                      »
                    </button>
                  </div>
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
          "报告中的逐条结果可复核、备注、查看上下文。"
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
            <div className="context-modal__body">
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
            </div>
          </section>
        </div>
      ) : null}
    </section>
  );
}
