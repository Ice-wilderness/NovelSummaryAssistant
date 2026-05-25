## ADDED Requirements

### Requirement: Modular route registration preserves the public API contract
系统 SHALL 将 WebUI 后端 API 路由拆分到职责清晰的路由模块中，同时保持拆分前已暴露的公开 method/path 契约不变。

#### Scenario: Existing API routes remain registered
- **WHEN** the application is created through `create_app(...)`
- **THEN** the FastAPI route table contains the existing public API methods and paths that were served before the refactor

#### Scenario: Existing frontend calls remain compatible
- **WHEN** the frontend calls an existing `/api/...` endpoint with the same request payload as before
- **THEN** the endpoint returns the same response shape and status-code semantics as before the route split

### Requirement: Route modules share one application runtime context
系统 SHALL ensure split route modules use the same application state, runtime, configured paths, and service factories initialized by `create_app(...)`.

#### Scenario: Test-injected paths are honored by split routes
- **WHEN** `create_app(...)` is called with explicit config, prompt cache, runtime base, user settings, or trigger profile paths
- **THEN** requests handled by split route modules read and write through those injected paths rather than default global paths

#### Scenario: Task routes use the configured runtime
- **WHEN** `create_app(...)` is called with a supplied `TaskRuntime`
- **THEN** task creation, lookup, pause, resume, cancel, and event stream routes operate on that supplied runtime

### Requirement: Application assembly remains the stable entry point
系统 SHALL keep `create_app(...)` as the stable factory that initializes app state, registers modular API routes, and preserves frontend static resource handling.

#### Scenario: Static frontend fallback remains available
- **WHEN** `create_app(...)` is called with a frontend dist directory containing built assets
- **THEN** the root and fallback frontend routes continue to serve the built WebUI as before

#### Scenario: API registration is centralized
- **WHEN** a developer reads the application factory
- **THEN** it is clear which route modules are registered and in what broad responsibility groups

### Requirement: The route split is protected as a no-behavior-change refactor
系统 SHALL include focused verification that detects route registration loss or externally visible API behavior drift introduced by the modularization.

#### Scenario: Route parity is verified
- **WHEN** the backend API test suite runs
- **THEN** it fails if a required public route method/path is no longer registered

#### Scenario: Existing API behavior tests continue to pass
- **WHEN** existing backend API, project workspace, task runtime, trigger profile, and trigger scan tests run
- **THEN** they continue to pass without requiring callers to use new URLs or payload shapes
