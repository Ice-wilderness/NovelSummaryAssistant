import { Play, RefreshCw } from "lucide-react";
import React, { useCallback, useEffect, useMemo, useState } from "react";
import { apiClient } from "../api/client";
import type {
  ProjectRecord,
  ScanFinding,
  ScanReport,
  SpoilerLevel,
  TriggerProfile,
  TriggerReviewStatus,
  TriggerRule,
  TriggerRuleGroup,
  TriggerScanConfig,
  TriggerScanPrecheckResponse,
  TriggerScanReportHistoryItem
} from "../api/types";
import { GuidancePanel } from "../components/common/Guidance";
import type { Stage } from "../components/StageProgressBar";
import {
  StudioMotionSurface,
  StudioStatusBadge
} from "../components/studio/StudioPrimitives";
import { useTaskActions } from "../hooks/useTaskActions";
import { useTaskAvailability } from "../hooks/useTaskAvailability";
import { useAppState } from "../state/AppState";
import { isFinding, reportWarningMessages } from "./trigger-scan/display";
import { triggerTabs, type ResultView, type TriggerTab } from "./trigger-scan/options";
import { cloneProfile, createGroup, createRule } from "./trigger-scan/profileDraft";
import {
  buildRuleOptions,
  emptyFilters,
  filterFindings,
  paginateFindings,
  totalFindingPages,
  type ResultFilters,
  visibleEvents as getVisibleEvents
} from "./trigger-scan/resultFilters";
import { ProfileTab } from "./trigger-scan/ProfileTab";
import { ScanConfigTab } from "./trigger-scan/ScanConfigTab";
import { ContextModal, type ContextState } from "./trigger-scan/ContextModal";
import { ResultsTab } from "./trigger-scan/ResultsTab";

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
  const [reportsProjectSlug, setReportsProjectSlug] = useState("");
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
  const reportRequestRef = React.useRef(0);
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
      const requestId = reportRequestRef.current + 1;
      reportRequestRef.current = requestId;
      if (!projectSlug) {
        setReports([]);
        setReportsProjectSlug("");
        setSelectedReportId("");
        setReport(null);
        return;
      }
      setReports([]);
      setReportsProjectSlug("");
      setReport((current) => current?.project_slug === projectSlug ? current : null);
      try {
        const items = await apiClient.listTriggerScanReports(projectSlug);
        if (requestId !== reportRequestRef.current) {
          return;
        }
        setReportsProjectSlug(projectSlug);
        setReports(items);
        setSelectedReportId((current) =>
          current && items.some((item) => item.report_id === current)
            ? current
            : items[0]?.report_id ?? ""
        );
        if (items.length === 0) {
          setReport(null);
        }
      } catch (error: unknown) {
        if (requestId !== reportRequestRef.current) {
          return;
        }
        setReports([]);
        setReportsProjectSlug(projectSlug);
        setSelectedReportId("");
        setReport(null);
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
    if (
      reportsProjectSlug !== selectedProjectSlug ||
      !reports.some((item) => item.report_id === selectedReportId)
    ) {
      setReport((current) =>
        current?.project_slug === selectedProjectSlug && current.report_id === selectedReportId
          ? current
          : null
      );
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
  }, [dispatch, reports, reportsProjectSlug, selectedProjectSlug, selectedReportId, showError]);

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

  const selectProject = useCallback((projectSlug: string) => {
    setSelectedProjectSlug(projectSlug);
    setReports([]);
    setReportsProjectSlug("");
    setSelectedReportId("");
    setReport(null);
    setResumeReportId("");
    setPrecheck(null);
    setContextState(null);
    setStatusMessage(projectSlug ? "正在切换扫描项目" : "请选择扫描项目");
  }, []);

  const loadResumeReportConfig = async (reportId: string) => {
    setResumeReportId(reportId);
    setPrecheck(null);
    if (!reportId) {
      return;
    }
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
    } catch {
      // Keep the existing silent fallback for stale or unreadable resume reports.
    }
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
    <ScanConfigTab
      activeApis={activeApis}
      canPrecheck={canPrecheck}
      canStart={canStart}
      generateSkipAdvice={generateSkipAdvice}
      keepLowConfidence={keepLowConfidence}
      latestTriggerTask={latestTriggerTask}
      liveFindings={liveFindings}
      maxQuoteChars={maxQuoteChars}
      minConfidence={minConfidence}
      minimumOutputCharacters={minimumOutputCharacters}
      onCancelDecision={() => setPrecheck(null)}
      onControlTriggerTask={(action) => void controlTriggerTask(action)}
      onGenerateSkipAdviceChange={setGenerateSkipAdvice}
      onKeepLowConfidenceChange={setKeepLowConfidence}
      onLoadProjects={() => void loadProjects()}
      onMaxQuoteCharsChange={setMaxQuoteChars}
      onMinConfidenceChange={setMinConfidence}
      onMinimumOutputCharactersChange={setMinimumOutputCharacters}
      onPreciseChapterBatchSizeChange={(value) => {
        setPreciseChapterBatchSize(value);
        setPrecheck(null);
      }}
      onRangeEndChange={(value) => {
        setRangeEnd(value);
        setPrecheck(null);
      }}
      onRangeStartChange={(value) => {
        setRangeStart(value);
        setPrecheck(null);
      }}
      onResumeReportChange={(reportId) => void loadResumeReportConfig(reportId)}
      onRunPrecheck={() => void runPrecheck()}
      onSaveConfig={() => void saveConfig()}
      onScanApiToggle={toggleScanApi}
      onSelectedProfileChange={setSelectedProfileId}
      onSelectedProjectChange={selectProject}
      onStartScan={() => void startScan()}
      onVerificationApiChange={setVerificationApiId}
      onVerificationChapterBatchSizeChange={(value) => {
        setVerificationChapterBatchSize(value);
        setPrecheck(null);
      }}
      onVerificationEnabledChange={setVerificationEnabled}
      preciseChapterBatchSize={preciseChapterBatchSize}
      precheck={precheck}
      profiles={profiles}
      rangeEnd={rangeEnd}
      rangeStart={rangeStart}
      reports={reports}
      resumeReportId={resumeReportId}
      scanApiIds={scanApiIds}
      scanCurrentStage={scanCurrentStage}
      scanProjects={scanProjects}
      scanStages={scanStages}
      selectedProfileId={selectedProfileId}
      selectedProjectSlug={selectedProjectSlug}
      triggerEvents={triggerEvents}
      verificationApiId={verificationApiId}
      verificationChapterBatchSize={verificationChapterBatchSize}
      verificationEnabled={verificationEnabled}
    />
  );

  const renderResultsTab = () => (
    <ResultsTab
      expandedEventIds={expandedEventIds}
      filteredFindings={filteredFindings}
      filters={filters}
      findingPage={findingPage}
      globalSpoiler={globalSpoiler}
      itemSpoilers={itemSpoilers}
      notes={notes}
      onDeleteReport={(reportId) => void deleteReport(reportId)}
      onExportReport={(format) => void exportReport(format)}
      onOpenContext={(finding) => void openContext(finding)}
      onRefreshReports={() => void refreshReports()}
      onSetExpandedEventIds={setExpandedEventIds}
      onSetFilters={setFilters}
      onSetFindingPage={setFindingPage}
      onSetGlobalSpoiler={(level) => {
        setGlobalSpoiler(level);
        setItemSpoilers({});
      }}
      onSetItemSpoilers={setItemSpoilers}
      onSetNotes={setNotes}
      onSetPageSize={setPageSize}
      onSetResultView={setResultView}
      onSetSelectedReportId={setSelectedReportId}
      onUpdateFinding={(finding, payload) => void updateFinding(finding, payload)}
      pageSize={pageSize}
      pagedFindings={pagedFindings}
      report={report}
      reportWarnings={reportWarnings}
      reports={reports}
      resultView={resultView}
      ruleOptions={ruleOptions}
      selectedReportId={selectedReportId}
      totalPages={totalPages}
      visibleEvents={visibleEvents}
    />
  );

  return (
    <section className="workflow-view trigger-studio">
      <header className="trigger-studio-hero">
        <div className="trigger-studio-hero__copy">
          <span>Trigger Review Studio</span>
          <h2>雷点扫描</h2>
          <p>{statusMessage || `${scanProjects.length} 个可扫描项目 · ${profiles.length} 个档案`}</p>
        </div>
        <div className="trigger-studio-hero__stats" aria-label="雷点扫描状态">
          <StudioStatusBadge tone={canStart ? "success" : "warning"}>
            {canStart ? "可扫描" : "待配置"}
          </StudioStatusBadge>
          <span>{profiles.length} 个档案</span>
          <span>{reports.length} 份报告</span>
          <span>{liveFindings.length} 条实时发现</span>
        </div>
        <div className="command-row trigger-studio-hero__actions">
          <button className="secondary-command" onClick={() => void loadProfiles()} type="button">
            <RefreshCw size={17} />
            <span>加载档案</span>
          </button>
          <button className="primary-command" disabled={!canStart} onClick={() => void startScan()} type="button">
            <Play size={17} />
            <span>开始</span>
          </button>
        </div>
      </header>

      <div className="trigger-studio-context">
        <section className="trigger-context-card">
          <strong>项目</strong>
          <span>{selectedProject?.project_name || "未选择项目"}</span>
        </section>
        <section className="trigger-context-card">
          <strong>档案</strong>
          <span>{selectedProfile?.name || "未选择档案"}</span>
        </section>
        <section className="trigger-context-card">
          <strong>报告</strong>
          <span>{report ? `${report.findings.length} 条发现 · ${report.status}` : "未载入报告"}</span>
        </section>
        <section className="trigger-context-card">
          <strong>待复核</strong>
          <span>{report?.summary.pending_review ?? 0}</span>
        </section>
      </div>

      <div className="trigger-flow-guide">
        <GuidancePanel
          title="扫描工作台"
          items={[
            "先维护雷点档案，再选择小说总结或章节分割项目启动扫描。",
            "扫描会直接读取所选章节原文；可通过精扫每批章节控制单次请求规模。",
            "报告中的逐条结果可复核、备注、查看上下文。"
          ]}
        />
      </div>

      <div className="trigger-studio-tabs" role="tablist" aria-label="雷点扫描工作台">
        {triggerTabs.map((tab) => (
          <button
            aria-selected={activeTab === tab.key}
            className="trigger-studio-tab"
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

      <StudioMotionSurface className="trigger-studio-panel" key={activeTab}>
        {activeTab === "profiles" ? renderProfileTab() : null}
        {activeTab === "scan" ? renderScanTab() : null}
        {activeTab === "results" ? renderResultsTab() : null}
      </StudioMotionSurface>

      {contextState ? (
        <ContextModal
          contextState={contextState}
          onClose={() => setContextState(null)}
        />
      ) : null}
    </section>
  );
}
