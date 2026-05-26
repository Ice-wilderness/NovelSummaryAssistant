import { createRef } from "react";
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { TriggerProfile } from "../../api/types";
import { ProfileTab } from "./ProfileTab";

function profile(): TriggerProfile {
  return {
    id: "profile-1",
    name: "默认档案",
    description: "说明",
    created_at: 1,
    updated_at: 2,
    rule_groups: [
      { id: "group-a", name: "A组", rules: ["rule-a"] },
      { id: "group-b", name: "B组", rules: ["rule-b"] }
    ],
    rules: [
      {
        id: "rule-a",
        name: "规则A",
        group_id: "group-a",
        description: "",
        matching_policy: "explicit_or_strongly_implied",
        severity_threshold: 2,
        enabled: true,
        examples: [],
        negative_examples: []
      },
      {
        id: "rule-b",
        name: "规则B",
        group_id: "group-b",
        description: "",
        matching_policy: "explicit_only",
        severity_threshold: 3,
        enabled: false,
        examples: [],
        negative_examples: []
      }
    ]
  };
}

function renderProfileTab(overrides: Partial<Parameters<typeof ProfileTab>[0]> = {}) {
  const item = profile();
  const props: Parameters<typeof ProfileTab>[0] = {
    activeGroupId: null,
    expandedRules: new Set(),
    importFileRef: createRef<HTMLInputElement>(),
    onAddGroup: vi.fn(),
    onAddRule: vi.fn(),
    onCollapseAllRules: vi.fn(),
    onCreateProfile: vi.fn(),
    onDeleteGroup: vi.fn(),
    onDeleteProfile: vi.fn(),
    onDeleteRule: vi.fn(),
    onDuplicateProfile: vi.fn(),
    onExpandAllRules: vi.fn(),
    onExportProfile: vi.fn(),
    onImportFileChange: vi.fn(),
    onSaveProfile: vi.fn(),
    onSelectProfile: vi.fn(),
    onSetActiveGroupId: vi.fn(),
    onToggleRuleExpanded: vi.fn(),
    onUpdateGroup: vi.fn(),
    onUpdateProfileDraft: vi.fn(),
    onUpdateRule: vi.fn(),
    profileDirty: false,
    profileDraft: item,
    profiles: [item],
    selectedProfile: item,
    selectedProfileId: item.id,
    ...overrides
  };
  render(<ProfileTab {...props} />);
  return props;
}

describe("ProfileTab", () => {
  it("shows profile list and delegates selection", () => {
    const props = renderProfileTab();

    fireEvent.click(screen.getByRole("button", { name: /默认档案/ }));

    expect(props.onSelectProfile).toHaveBeenCalledWith("profile-1");
    expect(screen.getByRole("button", { name: /保存档案/ })).toBeDisabled();
  });

  it("filters visible rules by active group", () => {
    renderProfileTab({ activeGroupId: "group-b" });

    expect(screen.queryByText("规则A")).not.toBeInTheDocument();
    expect(screen.getByText("规则B")).toBeInTheDocument();
  });

  it("enables save when the draft is dirty", () => {
    renderProfileTab({ profileDirty: true });

    expect(screen.getByRole("button", { name: /保存档案/ })).toBeEnabled();
  });
});
