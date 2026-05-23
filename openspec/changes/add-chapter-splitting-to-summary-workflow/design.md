## Context

当前项目有两个独立的工作流页面：
- **章节分割**（[SplitterPage.tsx](frontend/src/views/SplitterPage.tsx)）：上传单个体积文件 → 选择分割模式 → 输出到独立目录
- **小说总结**（[NovelSummaryPage.tsx](frontend/src/views/NovelSummaryPage.tsx)）：上传已分割的章节文件 → 多层级总结

两者唯一的关联是：用户先到分割页切分，再到总结页导入。分割的正则表达式目前是 SplitterPage 上的一个 textarea，每次需要手动输入或粘贴，无法保存、命名或切换。

## Goals / Non-Goals

**Goals:**
- 小说总结页面可直接上传源文件并执行分割，结果直接进入项目章节列表
- 正则模式抽象为可管理、可切换、可导入/导出的配置模块
- 分割前可预览结果（章节数量+名称列表）
- 分割入口保持双轨制：总结页内 → 直接作为项目章节；独立分割页 → 保持现有导出逻辑

**Non-Goals:**
- 不改变默认策略和标题列表策略的行为
- 不改变已有项目的数据迁移逻辑
- 不引入数据库依赖（继续使用 JSON 文件存储）

## Decisions

### 1. 正则配置模块存储方案

**Decision**: JSON 数组文件 `chapter_patterns.json`，存放在应用根目录。

**Rationale**: 与现有 `api_configs.json`、`user_settings.json` 保持一致的模式。每个配置是一个独立对象，包含 id、name、pattern、description、created_at。支持独立导入/导出（JSON 格式），方便用户社区分享。

**Alternatives considered**:
- 存到 `user_settings.json` 中：会使 settings 臃肿，且配置本质上是独立资源
- 存到数据库：新增依赖，对于配置管理过度设计

### 2. 正则配置存储完整正则表达式

**Decision**: 每个配置存储一份**完整的、可直接编译的正则表达式字符串**，同时保留 `n` 占位符语法作为简化的"构建器"模式。配置新增 `regex_mode` 字段区分两种来源：

- `regex_mode: "raw"` — 存储用户直接编写的完整正则，由系统编译后直接使用。适用于你举例的复杂匹配场景（零宽断言、多分支、Unicode 字符类等）
- `regex_mode: "simple"` — 存储 `第n章` 风格的占位符模式，系统按现有 [regex_strategy.py](splitters/regex_strategy.py) 逻辑自动构建正则后使用（向后兼容，适合简单需求）

无论哪种模式，底层都会产出一个 `chapter_pattern`（编译后的 regex），交给 `process_chapters_with_regex` 使用。该函数要求：
- `match.group(1)` = 章节标题行
- `match.group(2)` = 章节编号（用于文件名生成和分卷偏移）

对于 `"raw"` 模式且用户正则不含捕获组的情况，系统自动包裹为 `^\s*(({regex}).*)` 以满足 group(1)/group(2) 的约定。

**预设配置**：系统出厂预置若干默认配置，将当前 [default_strategy.py](splitters/default_strategy.py) 的内置正则和 [regex_strategy.py](splitters/regex_strategy.py) 的常用模板打包为配置项。

**Rationale**: `第n章` 占位符语法无法表达零宽断言、多分支或、Unicode 字符类等高级正则特性。存储完整正则 + 支持两种模式，既保留简单用户的使用体验（构建器），也不限制高级用户编写任意复杂正则的自由。配合预览功能，用户可以即时验证正则是否正确匹配目标章节标题。

### 3. 预览机制

**Decision**: 新增后端 API `POST /api/chapters/preview-split`，接收源文件内容和正则配置 → 返回章节列表（名称、行号范围），不写入任何文件。前端展示预览后，用户确认才执行实际分割。

**Rationale**: 预览必须是只读操作，不应产生副作用。预览数据量可控（最多几百条记录），直接返回 JSON。

### 4. 分割结果的处理分支

**Decision**: 后端通过 `context` 参数区分两种场景：
- `context: "novel_summary"` — 分割结果写入项目 inputs 目录，更新 project.uploads
- `context: "chapter_split"` — 保持现有行为，写入独立导出目录

**Rationale**: 最小化改动，复用同一个 split 管线，通过参数控制输出目标。

### 5. 前端 UI 改动

**Decision**: 在 [NovelSummaryPage.tsx](frontend/src/views/NovelSummaryPage.tsx) 的"项目与文件"区域内新增一个"源文件（待分割）"上传区域，明确标注与下方"已分割章节"的区别。新增一个"分割预览/执行"面板。

### 6. 正则配置的导入/导出格式

**Decision**: 导出使用独立 JSON 文件，格式为单配置对象（含 `name`、`regex_mode`、`pattern`、`description`），不包含内部 id 和时间戳字段。导入时接受单配置对象或配置数组，由系统分配新 id 和时间戳。

**Rationale**: 与 API 配置的存储格式对齐。独立文件方便用户在社区分享正则配置（如"适用于起点中文网的章节正则"），导出时不带内部元数据避免导入到他人环境时冲突。导入支持数组格式方便批量迁移。

**Export 示例**:
```json
{
  "name": "某点章节匹配",
  "regex_mode": "raw",
  "pattern": "(?<=[\\s])(?:序章|楔子|正文(?!完|结)|终章|后记|尾声|番外|第\\s{0,4}[\\d〇零一二两三四五六七八九十百千万壹贰叁肆伍陆柒捌玖拾佰仟]+?\\s{0,4}(?:章|节(?!课)|卷|集(?![合和]))).{0,50}$",
  "description": "支持序章、楔子、第X章/节/卷/集等多种格式"
}
```

### 7. 实现流程约束

**Constraint**: 每完成一个功能块（对应 tasks.md 中一个 `## N.` 分组）后，必须将变更提交到 git 仓库，commit message 格式为 `feat(<scope>): <描述>`。在开始下一个功能块之前先确认当前块的所有变更已提交。

**Rationale**: 分块提交便于追踪每个功能块的变更范围，出问题时可以精确 revert，也方便 code review 时按功能维度查看 diff。

## Risks / Trade-offs

- **[性能]** 大文件（>10MB）的预览可能需要扫描全文 → 后台异步处理，前端展示 loading 状态
- **[兼容性]** 正则配置模块的格式变更可能影响已有用户 → 版本字段 + 向后兼容读取
- **[复杂性]** 双入口逻辑可能让代码路径变复杂 → 通过 context 参数在入口处明确分支，核心分割逻辑保持不变
