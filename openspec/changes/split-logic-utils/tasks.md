## 1. Baseline And Boundary Review

- [x] 1.1 Review `logic/utils.py` public symbols, internal helper dependencies, and current callers across `logic/`, `splitters/`, `webui_backend/`, and `tests/`.
- [x] 1.2 Run baseline `python -m pytest tests/test_utils.py` and record any pre-existing failures.
- [x] 1.3 Decide final focused module names using the design as guidance and avoiding a `logic/utils/` package.
- [x] 1.4 Review `git status` before editing implementation files.

## 2. Extract Pure Output, Naming, And Batching Helpers

- [x] 2.1 Move summary output format/path helpers into a focused module and re-export them from `logic/utils.py`.
- [x] 2.2 Move filename sanitizing, chapter range parsing, numeric extraction, and natural sort helpers into a focused module and re-export them from `logic/utils.py`.
- [x] 2.3 Move small-summary batch naming and sequential batch/API allocation helpers into a focused module and re-export them from `logic/utils.py`.
- [x] 2.4 Run focused tests covering utility helpers, chapter granularity, and state resume behavior.
- [x] 2.5 Clean up imports made unused by this block, review `git status`, and commit the block.

## 3. Extract File IO, Prompt Runtime, And Progress Helpers

- [x] 3.1 Move robust file reading, joined file reading, global prompt cache path, prompt loading, tag extraction, and character extraction helpers into focused modules.
- [x] 3.2 Move stage progress, progress log message formatting, and pause check helpers only if they can be separated without changing caller semantics.
- [x] 3.3 Keep existing `logic.utils` imports and `from logic import utils` attribute access working.
- [x] 3.4 Run focused tests for prompt loading, trigger scan prompts, article/custom summary paths, and workflow cancellation/pause behavior.
- [x] 3.5 Clean up imports made unused by this block, review `git status`, and commit the block.

## 4. Extract API Diagnostic Logging Helpers

- [x] 4.1 Move API task log path, failure log directory, redaction, async log locking, failure log writing, task log writing, and cleanup helpers into a focused module.
- [x] 4.2 Preserve existing `.summarizer_cache/api_failures/` layout, JSON payload shape, redaction behavior, retention behavior, and async locking semantics.
- [x] 4.3 Keep existing test and mock paths stable through the `logic.utils` facade unless a narrower behavior test is more appropriate.
- [x] 4.4 Run focused LLM API and API failure log tests.
- [x] 4.5 Clean up imports made unused by this block, review `git status`, and commit the block.

## 5. Extract Chapter Writing And Splitter-Adjacent Helpers

- [ ] 5.1 Move regex match group extraction, numeric chapter writing, regex chapter processing, final summary path, chapter file discovery, and related splitter-adjacent helpers into focused modules.
- [ ] 5.2 Preserve existing chapter file naming, offset handling, title extraction, log callback behavior, and failure behavior.
- [ ] 5.3 Run focused chapter splitting, chapter granularity, splitter, summary workflow, and trigger scan tests affected by chapter helper movement.
- [ ] 5.4 Clean up imports made unused by this block, review `git status`, and commit the block.

## 6. Final Compatibility And Verification

- [ ] 6.1 Confirm `logic/utils.py` is reduced to a compatibility facade plus any helpers intentionally left in place.
- [ ] 6.2 Confirm no new module imports `logic.utils`, avoiding circular dependency through the facade.
- [ ] 6.3 Run `python -m pytest`.
- [ ] 6.4 Run frontend build or tests only if an implementation step unexpectedly touches frontend-facing contracts.
- [ ] 6.5 Update OpenSpec artifacts if implementation boundaries differ from this plan.
- [ ] 6.6 Review `git status` and commit final cleanup or verification updates.
