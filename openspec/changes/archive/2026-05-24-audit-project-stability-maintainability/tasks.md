## 1. Scope And Inventory

- [x] 1.1 Create `docs/stability_audit/` and define the report file structure with an overview, module reports, and a cross-module summary.
- [x] 1.2 Inventory source, configuration, tests, OpenSpec artifacts, and existing documentation to list covered modules and key paths in `docs/stability_audit/00-overview.md`.

## 2. Module Audit Reports

- [x] 2.1 Audit the React/Vite frontend workbench, including views, API client, state, hooks, shared components, and UX/runtime-state assumptions; write `docs/stability_audit/frontend.md`.
- [x] 2.2 Audit the WebUI backend API and service layer, including request models, service boundaries, task endpoints, file/config services, and error handling; write `docs/stability_audit/webui-backend.md`.
- [x] 2.3 Audit the core summary workflow logic, including orchestration, LLM calls, prompt composition, state manager behavior, paragraph indexing, and summary stages; write `docs/stability_audit/summary-workflows.md`.
- [x] 2.4 Audit the trigger scan workflow, including pipeline state, prompt generation, JSON parsing, reporting, profile handling, and result contracts; write `docs/stability_audit/trigger-scan.md`.
- [x] 2.5 Audit chapter splitting and pattern configuration, including splitter strategies, chapter pattern persistence, preview behavior, and integration with summary workflows; write `docs/stability_audit/chapter-splitting.md`.
- [x] 2.6 Audit configuration, file upload/local picking, workspace management, managed outputs, and path/security boundaries; write `docs/stability_audit/config-files-workspace.md`.

## 3. Quality And Project Process

- [x] 3.1 Audit tests and verification coverage, mapping existing tests to major modules, running the full feasible test suite, adding focused verification tests when needed for accuracy, and identifying high-risk gaps; write `docs/stability_audit/tests-and-quality.md`.
- [x] 3.2 Audit OpenSpec artifacts, archived changes, README/runtime notes, and project documentation for drift or missing operational guidance; write `docs/stability_audit/openspec-and-docs.md`.

## 4. Synthesis And Verification

- [x] 4.1 Create `docs/stability_audit/cross-module-risks.md` with prioritized risks spanning multiple modules, evidence, impact, and suggested follow-up changes.
- [x] 4.2 Update `docs/stability_audit/00-overview.md` with links to all module reports, covered scope, top risks, recommended follow-up order, estimated implementation complexity, executed test commands, results, and any known verification limits.
- [x] 4.3 Run documentation consistency checks plus the relevant test commands needed to support the audit findings, request extra authorization if required, and verify the reports satisfy the OpenSpec requirements.
