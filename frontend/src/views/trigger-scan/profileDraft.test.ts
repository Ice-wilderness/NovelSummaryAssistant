import { describe, expect, it, vi } from "vitest";
import type { TriggerProfile } from "../../api/types";
import { cloneProfile, createGroup, createRule, joinLines, splitLines } from "./profileDraft";

const profile: TriggerProfile = {
  id: "profile-1",
  name: "档案",
  description: "",
  created_at: 1,
  updated_at: 2,
  rule_groups: [{ id: "group-1", name: "分组", rules: ["rule-1"] }],
  rules: [
    {
      id: "rule-1",
      name: "规则",
      group_id: "group-1",
      description: "",
      matching_policy: "explicit_or_strongly_implied",
      severity_threshold: 2,
      enabled: true,
      examples: ["正例"],
      negative_examples: ["反例"]
    }
  ]
};

describe("trigger profile draft helpers", () => {
  it("splits and joins non-empty trimmed lines", () => {
    expect(splitLines("  a\n\n b \r\n")).toEqual(["a", "b"]);
    expect(joinLines(["a", "b"])).toBe("a\nb");
  });

  it("deep clones mutable rule arrays", () => {
    const draft = cloneProfile(profile);

    draft.rule_groups[0].rules.push("rule-2");
    draft.rules[0].examples.push("新增");

    expect(profile.rule_groups[0].rules).toEqual(["rule-1"]);
    expect(profile.rules[0].examples).toEqual(["正例"]);
  });

  it("creates default groups and rules with stable prefixes", () => {
    vi.spyOn(Date, "now").mockReturnValue(1000);
    vi.spyOn(Math, "random").mockReturnValue(0.5);

    const group = createGroup();
    const rule = createRule(group.id);

    expect(group.id).toMatch(/^group_/);
    expect(group.name).toBe("新分组");
    expect(rule.group_id).toBe(group.id);
    expect(rule.matching_policy).toBe("explicit_or_strongly_implied");
  });
});
