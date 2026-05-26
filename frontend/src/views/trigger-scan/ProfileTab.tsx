import {
  ChevronDown,
  Copy,
  FileDown,
  FileUp,
  Plus,
  Save,
  Trash2
} from "lucide-react";
import type { ChangeEvent, RefObject } from "react";
import type {
  TriggerMatchingPolicy,
  TriggerProfile,
  TriggerRule,
  TriggerRuleGroup
} from "../../api/types";
import {
  NumberInput,
  SelectField,
  TextAreaField,
  TextInput,
  ToggleSwitch
} from "../../components/forms/FormControls";
import { classNames } from "./display";
import {
  joinLines,
  matchingPolicyLabel,
  matchingPolicyOptions,
  splitLines
} from "./profileDraft";

interface ProfileTabProps {
  profiles: TriggerProfile[];
  selectedProfileId: string;
  selectedProfile: TriggerProfile | null;
  profileDraft: TriggerProfile | null;
  profileDirty: boolean;
  activeGroupId: string | null;
  expandedRules: Set<string>;
  importFileRef: RefObject<HTMLInputElement>;
  onSelectProfile: (profileId: string) => void;
  onCreateProfile: () => void;
  onDuplicateProfile: () => void;
  onDeleteProfile: () => void;
  onExportProfile: () => void;
  onImportFileChange: (event: ChangeEvent<HTMLInputElement>) => void;
  onSaveProfile: () => void;
  onUpdateProfileDraft: <K extends keyof TriggerProfile>(key: K, value: TriggerProfile[K]) => void;
  onAddGroup: () => void;
  onSetActiveGroupId: (groupId: string | null) => void;
  onUpdateGroup: (groupId: string, changes: Partial<TriggerRuleGroup>) => void;
  onDeleteGroup: (groupId: string) => void;
  onAddRule: (groupId: string) => void;
  onUpdateRule: <K extends keyof TriggerRule>(ruleId: string, key: K, value: TriggerRule[K]) => void;
  onDeleteRule: (ruleId: string) => void;
  onToggleRuleExpanded: (ruleId: string) => void;
  onExpandAllRules: () => void;
  onCollapseAllRules: () => void;
}

export function ProfileTab({
  profiles,
  selectedProfileId,
  selectedProfile,
  profileDraft,
  profileDirty,
  activeGroupId,
  expandedRules,
  importFileRef,
  onSelectProfile,
  onCreateProfile,
  onDuplicateProfile,
  onDeleteProfile,
  onExportProfile,
  onImportFileChange,
  onSaveProfile,
  onUpdateProfileDraft,
  onAddGroup,
  onSetActiveGroupId,
  onUpdateGroup,
  onDeleteGroup,
  onAddRule,
  onUpdateRule,
  onDeleteRule,
  onToggleRuleExpanded,
  onExpandAllRules,
  onCollapseAllRules
}: ProfileTabProps) {
  const visibleRules = profileDraft
    ? activeGroupId === null
      ? profileDraft.rules
      : profileDraft.rules.filter((rule) => rule.group_id === activeGroupId)
    : [];
  const activeGroup = profileDraft?.rule_groups.find((group) => group.id === activeGroupId) ?? null;

  return (
    <section className="trigger-grid">
      <ProfileList
        importFileRef={importFileRef}
        onCreateProfile={onCreateProfile}
        onDeleteProfile={onDeleteProfile}
        onDuplicateProfile={onDuplicateProfile}
        onExportProfile={onExportProfile}
        onImportFileChange={onImportFileChange}
        onSelectProfile={onSelectProfile}
        profileDraft={profileDraft}
        profiles={profiles}
        selectedProfile={selectedProfile}
        selectedProfileId={selectedProfileId}
      />

      <div className="trigger-editor-panel">
        {profileDraft ? (
          <>
            <ProfileHeader
              onAddGroup={onAddGroup}
              onSaveProfile={onSaveProfile}
              profileDirty={profileDirty}
              profileDraft={profileDraft}
            />
            <div className="form-grid form-grid--two">
              <TextInput
                label="档案名称"
                onChange={(event) => onUpdateProfileDraft("name", event.target.value)}
                value={profileDraft.name}
              />
              <TextInput
                label="说明"
                onChange={(event) => onUpdateProfileDraft("description", event.target.value)}
                value={profileDraft.description}
              />
            </div>

            <RuleGroupTabs
              activeGroupId={activeGroupId}
              onSetActiveGroupId={onSetActiveGroupId}
              profileDraft={profileDraft}
            />

            {activeGroup ? (
              <div className="rule-group-edit">
                <TextInput
                  label="分组名称"
                  onChange={(event) => onUpdateGroup(activeGroup.id, { name: event.target.value })}
                  value={activeGroup.name}
                />
                <button
                  className="secondary-command secondary-command--compact"
                  onClick={() => onAddRule(activeGroup.id)}
                  type="button"
                >
                  <Plus size={16} />
                  <span>规则</span>
                </button>
                <button
                  className="danger-command"
                  onClick={() => {
                    onDeleteGroup(activeGroup.id);
                    onSetActiveGroupId(null);
                  }}
                  type="button"
                >
                  <Trash2 size={16} />
                  <span>删除分组</span>
                </button>
              </div>
            ) : null}

            {visibleRules.length > 0 ? (
              <div className="command-row">
                <button className="secondary-command secondary-command--compact" onClick={onExpandAllRules} type="button">
                  <span>全部展开</span>
                </button>
                <button className="secondary-command secondary-command--compact" onClick={onCollapseAllRules} type="button">
                  <span>全部折叠</span>
                </button>
                {activeGroupId === null ? (
                  <button
                    className="secondary-command secondary-command--compact"
                    disabled={profileDraft.rule_groups.length === 0}
                    onClick={() => {
                      const groupId = profileDraft.rule_groups[0]?.id;
                      if (groupId) onAddRule(groupId);
                    }}
                    type="button"
                  >
                    <Plus size={16} />
                    <span>规则</span>
                  </button>
                ) : null}
              </div>
            ) : null}

            {visibleRules.length === 0 ? (
              <span className="empty-state">
                {activeGroup ? "此分组暂无规则" : "暂无规则，请添加分组和规则"}
              </span>
            ) : (
              <div className="rule-card-list">
                {visibleRules.map((rule) => (
                  <RuleCard
                    expanded={expandedRules.has(rule.id)}
                    key={rule.id}
                    onDeleteRule={onDeleteRule}
                    onToggleRuleExpanded={onToggleRuleExpanded}
                    onUpdateRule={onUpdateRule}
                    profileDraft={profileDraft}
                    rule={rule}
                  />
                ))}
              </div>
            )}
          </>
        ) : (
          <span className="empty-state">请选择或新建雷点档案。</span>
        )}
      </div>
    </section>
  );
}

function ProfileList({
  profiles,
  selectedProfileId,
  selectedProfile,
  profileDraft,
  importFileRef,
  onSelectProfile,
  onCreateProfile,
  onDuplicateProfile,
  onDeleteProfile,
  onExportProfile,
  onImportFileChange
}: Pick<
  ProfileTabProps,
  | "profiles"
  | "selectedProfileId"
  | "selectedProfile"
  | "profileDraft"
  | "importFileRef"
  | "onSelectProfile"
  | "onCreateProfile"
  | "onDuplicateProfile"
  | "onDeleteProfile"
  | "onExportProfile"
  | "onImportFileChange"
>) {
  return (
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
              onClick={() => onSelectProfile(profile.id)}
              type="button"
            >
              <span>{profile.name}</span>
              <small>{profile.rules.filter((rule) => rule.enabled).length} 条启用规则</small>
            </button>
          ))
        )}
      </div>
      <div className="command-row">
        <button className="secondary-command secondary-command--compact" onClick={onCreateProfile} type="button">
          <Plus size={16} />
          <span>新建</span>
        </button>
        <button
          className="secondary-command secondary-command--compact"
          disabled={!selectedProfile}
          onClick={onDuplicateProfile}
          type="button"
        >
          <Copy size={16} />
          <span>复制</span>
        </button>
        <button
          className="danger-command"
          disabled={!selectedProfile}
          onClick={onDeleteProfile}
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
          onClick={onExportProfile}
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
          onChange={onImportFileChange}
          ref={importFileRef}
          style={{ display: "none" }}
          type="file"
        />
      </div>
    </aside>
  );
}

function ProfileHeader({
  profileDraft,
  profileDirty,
  onAddGroup,
  onSaveProfile
}: Pick<ProfileTabProps, "profileDraft" | "profileDirty" | "onAddGroup" | "onSaveProfile"> & {
  profileDraft: TriggerProfile;
}) {
  return (
    <header className="config-card__header">
      <h3>{profileDraft.name || "未命名档案"}</h3>
      <div className="command-row">
        <button className="secondary-command secondary-command--compact" onClick={onAddGroup} type="button">
          <Plus size={16} />
          <span>分组</span>
        </button>
        <button
          className="primary-command"
          disabled={!profileDirty}
          onClick={onSaveProfile}
          type="button"
        >
          <Save size={17} />
          <span>保存档案</span>
        </button>
      </div>
    </header>
  );
}

function RuleGroupTabs({
  profileDraft,
  activeGroupId,
  onSetActiveGroupId
}: Pick<ProfileTabProps, "activeGroupId" | "onSetActiveGroupId"> & {
  profileDraft: TriggerProfile;
}) {
  return (
    <div className="rule-group-tabs">
      <button
        aria-selected={activeGroupId === null ? "true" : undefined}
        className="rule-group-tab"
        onClick={() => onSetActiveGroupId(null)}
        type="button"
      >
        全部
        <small>
          {profileDraft.rules.filter((rule) => rule.enabled).length}/{profileDraft.rules.length}
        </small>
      </button>
      {profileDraft.rule_groups.map((group) => {
        const groupRules = profileDraft.rules.filter((rule) => rule.group_id === group.id);
        const enabledCount = groupRules.filter((rule) => rule.enabled).length;
        return (
          <button
            aria-selected={activeGroupId === group.id ? "true" : undefined}
            className="rule-group-tab"
            key={group.id}
            onClick={() => onSetActiveGroupId(group.id)}
            type="button"
          >
            {group.name}
            <small>{enabledCount}/{groupRules.length}</small>
          </button>
        );
      })}
    </div>
  );
}

function RuleCard({
  rule,
  profileDraft,
  expanded,
  onUpdateRule,
  onDeleteRule,
  onToggleRuleExpanded
}: {
  rule: TriggerRule;
  profileDraft: TriggerProfile;
  expanded: boolean;
  onUpdateRule: ProfileTabProps["onUpdateRule"];
  onDeleteRule: ProfileTabProps["onDeleteRule"];
  onToggleRuleExpanded: ProfileTabProps["onToggleRuleExpanded"];
}) {
  return (
    <section className="rule-card" key={rule.id}>
      <div
        className="rule-card__summary"
        onClick={() => onToggleRuleExpanded(rule.id)}
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
            onUpdateRule(rule.id, "enabled", checked);
          }}
        />
        <button
          className={classNames(
            "rule-card__expand-btn",
            expanded && "rule-card__expand-btn--open"
          )}
          onClick={(event) => {
            event.stopPropagation();
            onToggleRuleExpanded(rule.id);
          }}
          type="button"
        >
          <ChevronDown size={16} />
        </button>
      </div>
      {expanded ? (
        <div className="rule-card__body">
          <div className="form-grid form-grid--two">
            <TextInput
              label="规则名称"
              onChange={(event) => onUpdateRule(rule.id, "name", event.target.value)}
              value={rule.name}
            />
            <SelectField
              label="所属分组"
              onChange={(event) =>
                onUpdateRule(rule.id, "group_id", event.target.value)
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
                onUpdateRule(
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
                onUpdateRule(
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
            onChange={(event) => onUpdateRule(rule.id, "description", event.target.value)}
            value={rule.description}
          />
          <div className="form-grid form-grid--two">
            <TextAreaField
              label="正例"
              onChange={(event) =>
                onUpdateRule(rule.id, "examples", splitLines(event.target.value))
              }
              value={joinLines(rule.examples)}
            />
            <TextAreaField
              label="反例"
              onChange={(event) =>
                onUpdateRule(rule.id, "negative_examples", splitLines(event.target.value))
              }
              value={joinLines(rule.negative_examples)}
            />
          </div>
          <div className="command-row">
            <button
              className="danger-command"
              onClick={() => onDeleteRule(rule.id)}
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
}
