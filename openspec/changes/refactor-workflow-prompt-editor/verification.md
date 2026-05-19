## Verification

Date: 2026-05-19

### Checks Completed

- Legacy prompt cache migration: verified by `tests.test_config_service`, including default-only load, legacy `prompt_cache/*.txt` load, and missing legacy file fallback.
- Structured prompt save/load: verified by `tests.test_config_service`, including message role/order preservation after saving `prompt_workflows.json`.
- Prompt module references: verified by `tests.test_config_service` and `tests.test_api_app`, including module creation, missing module reference errors, and preventing deletion of referenced modules.
- Prompt node reset: verified by `tests.test_config_service` and `tests.test_api_app`, restoring one node to default messages without resetting unrelated modules.
- Task start path: verified by `python -m unittest discover tests` and `tests.test_webui_e2e`, including article summary and chapter splitter task startup through the WebUI API.
- Frontend build path: verified by `npm run build` in `frontend`, covering TypeScript checks and Vite production build.

### Notes

- The runtime now reads `prompt_cache/prompt_workflows.json` when present and falls back to legacy prompt text files otherwise.
- The prompt editor keeps legacy `/api/prompts` compatibility while exposing structured workflow prompt configuration to the new UI.
