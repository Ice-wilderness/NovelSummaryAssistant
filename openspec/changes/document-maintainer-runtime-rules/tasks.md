## 1. Documentation Structure

- [ ] 1.1 Add README maintainer entry with development commands, validation commands, OpenSpec workflow, runtime directory overview, and links to deeper docs.
- [ ] 1.2 Add `docs/runtime_behavior_notes.md` as the stable entry for task states, event streams, repair, configuration recovery, and local path boundaries.
- [ ] 1.3 Add `docs/spec_to_test_mapping.md` for high-value specs, representative tests, and recommended verification commands.
- [ ] 1.4 Add `docs/archived_changes_index.md` for notable archived changes, related current specs/docs, and detailed artifact locations.

## 2. Runtime Rules Content

- [ ] 2.1 Document terminal task state meanings and maintenance boundaries for `success`, `failed`, `cancelled`, `partial_failed`, and `interrupted`.
- [ ] 2.2 Document task event replay rules, including `event_id`, `Last-Event-ID`, query cursor replay, replay gap, heartbeat, retention, and status fallback behavior.
- [ ] 2.3 Document project reconcile and repair boundaries, including no silent repair, LLM/overwrite confirmation, unsupported workflow behavior, and repair task separation from original task history.
- [ ] 2.4 Document configuration recovery and local filesystem boundaries, including `.bak` recovery warnings, strict versus compat output directory handling, local picker failure, and `open_directory` output-only scope.

## 3. Maintenance Mapping

- [ ] 3.1 Map task runtime, managed project outputs, configuration management, file upload, trigger scan, summary partial status, chapter splitting, and modularity specs to representative tests.
- [ ] 3.2 Mark the mapping as a navigation aid that does not replace running the documented backend, frontend, build, and OpenSpec validation commands.
- [ ] 3.3 Index recent stability and maintainability archived changes by topic without duplicating their proposal/design/tasks content.

## 4. Verification

- [ ] 4.1 Check README and docs links/paths for consistency after documentation edits.
- [ ] 4.2 Run `openspec validate document-maintainer-runtime-rules --strict`.
- [ ] 4.3 Run `openspec validate --all`.
- [ ] 4.4 Confirm `git status --short` only contains the intended README/docs/OpenSpec documentation changes before commit.
