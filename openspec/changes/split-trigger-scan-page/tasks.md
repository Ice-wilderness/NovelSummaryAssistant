## 1. Baseline And Test Setup

- [x] 1.1 Review `TriggerScanPage.tsx` state, effects, handlers, helper functions, and JSX regions to confirm extraction boundaries.
- [x] 1.2 Run baseline `npm run build` from `frontend/` and record any pre-existing failures.
- [x] 1.3 Add minimal frontend test dependencies and scripts using the existing npm / `package-lock.json` workflow.
- [x] 1.4 Add a tiny smoke test or helper test to confirm the new test command runs.
- [x] 1.5 Review `git status` and commit the test setup block.

## 2. Extract Pure Helpers

- [x] 2.1 Move status/report display helpers, warning message generation, spoiler text helpers, path/chapter formatting, and class-name helpers into focused trigger-scan utility modules.
- [x] 2.2 Move profile draft helpers such as clone/create group/create rule and line split/join helpers into focused modules.
- [x] 2.3 Move result filtering, event visibility, pagination, and finding display derivation into pure helpers where practical.
- [x] 2.4 Add focused tests for representative helper behavior, including `cancelled`, `partial_failed`, `unverified` warnings, spoiler fallback, and filter/pagination edge cases.
- [x] 2.5 Run the new frontend test command and `npm run build`.
- [x] 2.6 Review `git status` and commit the pure helper extraction block.

## 3. Split Profile Management UI

- [x] 3.1 Extract the profile tab into focused components for profile list/actions, profile metadata, rule groups, and rule editor rows.
- [x] 3.2 Keep existing profile create/save/delete/import/export behavior, dirty state, expanded rules, and active group handling unchanged.
- [x] 3.3 Add component or helper tests for profile editing behavior where the extracted boundary is testable without over-mocking the whole page.
- [x] 3.4 Run the new frontend test command and `npm run build`.
- [x] 3.5 Review `git status` and commit the profile UI split block.

## 4. Split Scan Configuration UI

- [ ] 4.1 Extract project selection, range controls, API selection, verification settings, low-confidence settings, resume selection, precheck decisions, and task controls into scan configuration components.
- [ ] 4.2 Preserve existing defaults, disabled states, validation messages, startup-check flow, resume payload fields, and task availability behavior.
- [ ] 4.3 Add focused tests for request/config derivation or validation helpers if they are extracted.
- [ ] 4.4 Run the new frontend test command and `npm run build`.
- [ ] 4.5 Review `git status` and commit the scan configuration split block.

## 5. Split Results And Review UI

- [ ] 5.1 Extract report history selection, report summary, warning display, event list, finding filters, finding list, pagination, and spoiler controls into results components.
- [ ] 5.2 Extract finding review actions, note editing, context lookup trigger, and context modal rendering while preserving API calls and local state updates.
- [ ] 5.3 Preserve `partial_failed`, `cancelled`, `failed`, `completed`, deterministic aggregation, and `unverified` warning display semantics.
- [ ] 5.4 Add focused tests for warning display, filtering, pagination, review status controls, or context modal behavior where practical.
- [ ] 5.5 Run the new frontend test command and `npm run build`.
- [ ] 5.6 Review `git status` and commit the results/review split block.

## 6. Final Integration And Verification

- [ ] 6.1 Reduce `TriggerScanPage.tsx` to orchestration, shared state wiring, effects, and tab composition.
- [ ] 6.2 Remove imports, helper functions, props, or files made unused by this refactor.
- [ ] 6.3 Run the new frontend test command.
- [ ] 6.4 Run `npm run build`.
- [ ] 6.5 Run relevant Python tests only if any API contract, generated type expectation, or backend-adjacent behavior is touched.
- [ ] 6.6 Review OpenSpec artifacts against implemented scope and update tasks/specs if the implementation boundary changes.
- [ ] 6.7 Review `git status` and commit the final cleanup/verification block.
