## 1. Backend Configuration Recovery

- [x] 1.1 Add a focused helper for backing up corrupted local configuration files to `.bak` or a non-overwriting `.bak` variant.
- [x] 1.2 Extend API configuration loading to return safe defaults plus a domain warning after corrupted JSON or unusable configuration data is backed up.
- [x] 1.3 Extend user settings loading to return safe defaults plus a domain warning after corrupted settings data is backed up.
- [x] 1.4 Extend chapter pattern configuration loading to return safe defaults plus a domain warning after corrupted pattern data is backed up.
- [x] 1.5 Preserve current behavior for missing configuration files while only warning on corrupted or unusable existing files.

## 2. Output Directory Validation

- [x] 2.1 Split output directory resolution into strict active-operation validation and compat historical-read resolution.
- [x] 2.2 Reject invalid project-level custom output directories during project save, output migration checks, task-start auto-save, and workflow task creation.
- [x] 2.3 Preserve the previous saved output target when strict validation rejects an invalid custom output directory.
- [x] 2.4 Return compat warnings when historical, imported, or detail-loaded projects contain invalid saved custom output directories and fall back to the effective default output directory.
- [x] 2.5 Add an explicit backend path for clearing the project-level custom output directory so the default output directory can be used after user confirmation.

## 3. Local Path Capability Boundaries

- [x] 3.1 Update the open-output-directory route to derive the directory from project metadata and effective output resolution instead of trusting arbitrary client paths.
- [x] 3.2 Reject any open-directory request that targets a path other than the current project effective output directory.
- [x] 3.3 Normalize local picker and output opener failures into actionable backend errors for headless, missing GUI dependency, missing directory, or OS opener failure cases.

## 4. WebUI Feedback And Recovery

- [x] 4.1 Extend frontend API types and client handling for configuration recovery warnings, output directory validation errors, and local path capability errors.
- [x] 4.2 Display API configuration recovery warnings in the API configuration page or section.
- [x] 4.3 Display user settings recovery warnings in the user settings page or section.
- [x] 4.4 Display chapter pattern recovery warnings in the chapter pattern or chapter splitting surface.
- [x] 4.5 Show invalid custom output directory errors near the output directory control while preserving the invalid path for editing.
- [x] 4.6 Add a “use default output directory” action that clears the custom output directory only after user selection.
- [x] 4.7 Display local picker and open-output-directory failures near the controls that triggered them.

## 5. Tests And Verification

- [x] 5.1 Add backend tests for corrupted API config, user settings, and chapter pattern backup/warning behavior, including backup-write failure.
- [x] 5.2 Add backend tests for strict custom output directory rejection and compat historical-read fallback warnings.
- [x] 5.3 Add API tests for task-start/save rejection, explicit default-output fallback, and open-output-directory boundary enforcement.
- [x] 5.4 Add backend tests for local picker/open output failure normalization.
- [x] 5.5 Add frontend focused tests for local configuration warning display, invalid output directory recovery, preserved invalid path editing, and local capability error placement.
- [x] 5.6 Run focused Python tests, focused frontend tests, `python -m pytest`, `npm run test`, `npm run build`, and `openspec validate --all` as scope and runtime allow.

## 6. Documentation Sync

- [x] 6.1 Update stability audit follow-up docs to mark configuration/path boundary hardening according to the implemented scope.
- [x] 6.2 Document the local single-user path capability boundary and the distinction between strict active validation and compat historical fallback.
- [x] 6.3 Record verification commands and any intentionally deferred path/config follow-ups in the change notes or related maintenance docs.
