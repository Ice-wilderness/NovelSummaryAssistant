## 1. API Client Error Handling

- [x] 1.1 Add focused tests for `requestJson` covering successful JSON, failed JSON with `detail`, failed non-JSON text/HTML, and empty failed responses.
- [x] 1.2 Update `frontend/src/api/client.ts` so failed non-JSON responses throw `ApiError` with HTTP status and readable status text or body preview instead of raw JSON parse errors.
- [x] 1.3 Keep existing successful JSON behavior and existing `ApiError` detail behavior for backend JSON errors.

## 2. Upload Size Preflight

- [x] 2.1 Add a shared frontend upload limit constant or helper that represents the backend single-file 100 MB limit.
- [x] 2.2 Add tests that oversized managed project uploads are rejected before file contents are read.
- [x] 2.3 Update `useManagedProject.uploadFiles` to reject files larger than 100 MB before `arrayBuffer()` and before calling the upload API.
- [x] 2.4 Add or update tests that oversized novel source split uploads are rejected before file contents are read.
- [x] 2.5 Update `NovelSummaryPage.handleSourceUpload` to apply the same 100 MB preflight while preserving existing UTF-8/GBK decoding for accepted files.

## 3. Splitter API Client Consolidation

- [x] 3.1 Add or update API client tests for `apiClient.startSplitter` request behavior if current coverage is missing.
- [x] 3.2 Replace the page-local `fetch("/api/tasks/splitter")` path in `NovelSummaryPage.confirmSplitAndIngest` with `apiClient.startSplitter`.
- [x] 3.3 Preserve existing split-and-ingest success behavior: clear source file/content, refresh project state, and clear preview results.

## 4. Verification

- [x] 4.1 Run the focused frontend tests added or changed for this change.
- [x] 4.2 Run `npm run test` in `frontend/`.
- [x] 4.3 Run `npm run build` in `frontend/`.
- [x] 4.4 Run `openspec validate harden-frontend-api-upload --strict`.
