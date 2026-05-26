import type {
  TriggerMatchingPolicy,
  TriggerProfile,
  TriggerRule,
  TriggerRuleGroup
} from "../../api/types";

export const matchingPolicyOptions: Array<{ label: string; value: TriggerMatchingPolicy }> = [
  { label: "仅明确出现", value: "explicit_only" },
  { label: "明确或强暗示", value: "explicit_or_strongly_implied" },
  { label: "任何线索", value: "any_hint" }
];

export function splitLines(value: string) {
  return value
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);
}

export function joinLines(values: string[]) {
  return values.join("\n");
}

export function randomId(prefix: string) {
  return `${prefix}_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
}

export function createGroup(): TriggerRuleGroup {
  const id = randomId("group");
  return {
    id,
    name: "新分组",
    rules: []
  };
}

export function createRule(groupId: string): TriggerRule {
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

export function cloneProfile(profile: TriggerProfile): TriggerProfile {
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

export function matchingPolicyLabel(policy: string) {
  const option = matchingPolicyOptions.find((item) => item.value === policy);
  return option?.label ?? policy;
}
