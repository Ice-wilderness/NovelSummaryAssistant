## 1. Boundary Parsing Foundation

- [x] 1.1 Add a focused chapter boundary module with lightweight result and error models.
- [x] 1.2 Implement shared boundary parsing for default regex mode.
- [x] 1.3 Implement shared boundary parsing for simple/raw regex mode.
- [x] 1.4 Implement shared boundary parsing for title-list mode, including unmatched-title preview items.
- [x] 1.5 Add focused Python tests for default, regex, title-list, no-match, and line/word-count boundary results.

## 2. Raw Regex Safety

- [x] 2.1 Add raw regex validation for empty, invalid, overlong, and obvious high-risk nested-repeat patterns.
- [x] 2.2 Add raw regex preflight checks before preview or actual split scans full source text.
- [x] 2.3 Preserve existing raw no-group auto-wrap and grouped raw behavior after validation.
- [x] 2.4 Add focused tests for accepted raw regex, auto-wrap, invalid syntax, overlong input, high-risk pattern rejection, and preflight failure.

## 3. Preview And Split Integration

- [ ] 3.1 Update `preview_split` and `/api/chapters/preview-split` to use shared boundary results and return actionable 400 errors.
- [ ] 3.2 Update actual split paths to write chapter files from shared boundary results.
- [ ] 3.3 Ensure split failures preserve structured error messages instead of only `(False, 0)`.
- [ ] 3.4 Ensure direct split API and splitter task logs expose the user-readable failure reason.
- [ ] 3.5 Add or update tests for preview/split consistency and direct split error responses.

## 4. Project Ingest Safety

- [ ] 4.1 Update novel-summary source split ingestion to validate boundaries before replacing project inputs/uploads.
- [ ] 4.2 Use a temporary output location or equivalent guard so failed split attempts leave existing project uploads unchanged.
- [ ] 4.3 Add project workspace/API tests covering failed source split preserving existing uploads and successful split replacing uploads.

## 5. Frontend Error Display

- [ ] 5.1 Ensure SplitterPage displays preview and direct split safety errors clearly through existing API error handling.
- [ ] 5.2 Ensure NovelSummaryPage displays source split safety errors without clearing current project chapter state.
- [ ] 5.3 Add focused frontend tests for raw regex rejection and project source split failure messaging where practical.

## 6. Verification

- [ ] 6.1 Run focused Python tests for chapter boundaries, chapter splitter, project workspace, workflow services, and API routes.
- [ ] 6.2 Run focused frontend tests for splitter and novel summary split flows.
- [ ] 6.3 Run `python -m pytest`.
- [ ] 6.4 Run `npm run test` and `npm run build` in `frontend/`.
- [ ] 6.5 Run `openspec validate harden-chapter-splitting-boundaries --strict` and `openspec validate --all`.
