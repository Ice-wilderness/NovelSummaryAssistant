## 1. Backend Configuration Recovery

- [ ] 1.1 Add a focused helper for backing up corrupted local configuration files to `.bak` or a non-overwriting `.bak` variant.
- [ ] 1.2 Extend API configuration loading to return safe defaults plus a domain warning after corrupted JSON or unusable configuration data is backed up.
- [ ] 1.3 Extend user settings loading to return safe defaults plus a domain warning after corrupted settings data is backed up.
- [ ] 1.4 Extend chapter pattern configuration loading to return safe defaults plus a domain warning after corrupted pattern data is backed up.
- [ ] 1.5 Preserve current behavior for missing configuration files while only warning on corrupted or unusable existing files.

## 2. Output Directory Validation

- [ ] 2.1 Split output directory resolution into strict active-operation validation and compat historical-read resolution.
- [ ] 2.2 Reject invalid project-level custom output directories during project save, output migration checks, task-start auto-save, and workflow task creation.
- [ ] 2.3 Preserve the previous saved output target when strict validation rejects an invalid custom output directory.
- [ ] 2.4 Return compat warnings when historical, imported, or detail-loaded projects contain invalid saved custom output directories and fall back to the effective default output directory.
- [ ] 2.5 Add an explicit backend path for clearing the project-level custom output directory so the default output directory can be used after user confirmation.

## 3. Local Path Capability Boundaries

- [ ] 3.1 Update the open-output-directory route to derive the directory from project metadata and effective output resolution instead of trusting arbitrary client paths.
- [ ] 3.2 Reject any open-directory request that targets a path other than the current project effective output directory.
- [ ] 3.3 Normalize local picker and output opener failures into actionable backend errors for headless, missing GUI dependency, missing directory, or OS opener failure cases.

## 4. WebUI Feedback And Recovery

- [ ] 4.1 Extend frontend API types and client handling for configuration recovery warnings, output directory validation errors, and local path capability errors.
- [ ] 4.2 Display API configuration recovery warnings in the API configuration page or section.
- [ ] 4.3 Display user settings recovery warnings in the user settings page or section.
- [ ] 4.4 Display chapter pattern recovery warnings in the chapter pattern or chapter splitting surface.
- [ ] 4.5 Show invalid custom output directory errors near the output directory control while preserving the invalid path for editing.
- [ ] 4.6 Add a “use default output directory” action that clears the custom output directory only after user selection.
- [ ] 4.7 Display local picker and open-output-directory failures near the controls that triggered them.

## 5. Tests And Verification

- [ ] 5.1 Add backend tests for corrupted API config, user settings, and chapter pattern backup/warning behavior, including backup-write failure.
- [ ] 5.2 Add backend tests for strict custom output directory rejection and compat historical-read fallback warnings.
- [ ] 5.3 Add API tests for task-start/save rejection, explicit default-output fallback, and open-output-directory boundary enforcement.
- [ ] 5.4 Add backend tests for local picker/open output failure normalization.
- [ ] 5.5 Add frontend focused tests for local configuration warning display, invalid output directory recovery, preserved invalid path editing, and local capability error placement.
- [ ] 5.6 Run focused Python tests, focused frontend tests, `python -m pytest`, `npm run test`, `npm run build`, and `openspec validate --all` as scope and runtime allow.

## 6. Documentation Sync

- [ ] 6.1 Update stability audit follow-up docs to mark configuration/path boundary hardening according to the implemented scope.
- [ ] 6.2 Document the local single-user path capability boundary and the distinction between strict active validation and compat historical fallback.
- [ ] 6.3 Record verification commands and any intentionally deferred path/config follow-ups in the change notes or related maintenance docs.
