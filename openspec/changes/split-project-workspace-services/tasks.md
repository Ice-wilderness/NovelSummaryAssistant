## 1. Baseline And Public Facade

- [x] 1.1 Review imports of `webui_backend.project_workspace` across `webui_backend/` and `tests/` to identify public symbols that must remain compatible.
- [x] 1.2 Run baseline `python -m pytest tests/test_project_workspace.py` and record any pre-existing failures before refactoring.
- [x] 1.3 Add or confirm focused facade/import assertions for existing public project workspace symbols if current tests do not cover them.
- [x] 1.4 Review `git status` and commit the baseline/facade test block if files changed.

## 2. Helper Package And Low-State Utilities

- [x] 2.1 Create the internal helper package for project workspace services without changing existing external imports.
- [x] 2.2 Move low-state utilities such as JSON file helpers, text/summary file counters, safe project naming helpers, and workflow export subdir mapping only when their public import behavior remains stable.
- [x] 2.3 Run `python -m pytest tests/test_project_workspace.py tests/test_imports.py`.
- [x] 2.4 Review `git status` and commit the helper package / low-state utility block.

## 3. Progress And Import Recognition

- [ ] 3.1 Extract project progress scanning helpers for novel, article, splitter, trigger scan artifact, paragraph index, and legacy cache recognition.
- [ ] 3.2 Keep imported and historical project status recognition compatible with existing metadata, grouped chapter names, trigger scan artifacts, and legacy output layouts.
- [ ] 3.3 Run focused project workspace tests covering import, progress recognition, grouped chapter compatibility, and trigger scan artifact detection.
- [ ] 3.4 Review `git status` and commit the progress/import recognition block.

## 4. Output Directory And Deletion Safety

- [ ] 4.1 Extract managed output directory resolution, ownership metadata writing, ownership verification, and preserved-output message helpers.
- [ ] 4.2 Extract output migration helpers while preserving migration prompts, nested migration protection, failure rollback, and metadata update semantics.
- [ ] 4.3 Extract project deletion cleanup helpers while preserving managed-output-only deletion and custom/imported/missing-ownership output preservation.
- [ ] 4.4 Run focused project workspace tests for default export directories, ownership metadata, migration, deletion, and preserved output messages.
- [ ] 4.5 Review `git status` and commit the output/deletion safety block.

## 5. Uploads And Local Directory Opening

- [ ] 5.1 Extract upload storage, duplicate filename handling, uploaded reference serialization, reference resolution, and clear-upload helpers.
- [ ] 5.2 Extract local directory opening helpers while preserving existing OS-specific behavior and test patch compatibility.
- [ ] 5.3 Run focused project workspace and API tests for upload ordering, missing references, oversized/unsupported uploads, clear uploads, and open-directory behavior.
- [ ] 5.4 Review `git status` and commit the uploads/local-open block.

## 6. Facade Cleanup And Contract Verification

- [ ] 6.1 Remove imports, helpers, or aliases made unused by this refactor while preserving `webui_backend.project_workspace` as the public facade.
- [ ] 6.2 Run `python -m pytest tests/test_project_workspace.py tests/test_api_app.py tests/test_imports.py`.
- [ ] 6.3 Run full `python -m pytest`.
- [ ] 6.4 Run `npm run build` only if frontend-facing API types, request/response shapes, or frontend files are touched.
- [ ] 6.5 Review OpenSpec artifacts against the implemented behavior and update tasks/specs only if the implementation scope changed.
- [ ] 6.6 Review `git status` and commit the final cleanup/verification block.
