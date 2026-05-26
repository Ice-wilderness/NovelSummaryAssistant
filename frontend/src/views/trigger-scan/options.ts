import type { SpoilerLevel } from "../../api/types";

export type TriggerTab = "profiles" | "scan" | "results";
export type ResultView = "events" | "findings";

export const triggerTabs: Array<{ key: TriggerTab; label: string; meta: string }> = [
  { key: "profiles", label: "档案", meta: "规则" },
  { key: "scan", label: "扫描", meta: "配置" },
  { key: "results", label: "结果", meta: "报告" }
];

export const spoilerOptions: Array<{ label: string; value: SpoilerLevel }> = [
  { label: "低剧透", value: "low" },
  { label: "标准", value: "standard" },
  { label: "详细", value: "detailed" }
];
