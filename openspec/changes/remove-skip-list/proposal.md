## Why

跳读清单是雷点扫描功能中的一个独立功能模块，允许用户将扫描发现加入清单、手动添加条目、编辑备注并导出 Markdown。该功能的实际使用频率极低——用户通常直接在扫描报告中复核条目，而非将其整理到独立的跳读清单中。维护该功能增加了代码复杂度、API 数量、测试负担和 UI 噪音。移除此功能可以简化雷点扫描工作台，降低后续维护成本。

## What Changes

- 移除"跳读清单"工作台标签页及其全部 UI（条目表格、手动添加表单、导出按钮）
- 移除扫描结果中"加入跳读清单"按钮及相关状态
- 移除跳读清单后端 API 端点（6 个端点）及 `SkipListStore` 存储逻辑
- 移除 `SkipListItem`、`SkipList` 数据模型及 `ScanFinding.in_skip_list` 字段 **BREAKING**
- 移除项目进度中的"跳读清单"阶段及 `skip_item_count` 统计
- 保留 `generate_skip_advice` 配置选项和 `skip_advice` 字段——跳读建议仍由 AI 在扫描时生成并在报告中展示，不受本次移除影响

## Capabilities

### New Capabilities

（无新增能力）

### Modified Capabilities

- `trigger-scan-results`: 移除 Skip List 需求及相关场景（添加至清单、按章节查看、导出清单）
- `webui-workbench`: 移除跳读清单标签页描述；移除扫描配置中跳读建议生成的引用（实际保留该功能，仅修正文档）
- `managed-project-outputs`: 移除 skip list 文件作为项目输出工件的引用
- `configuration-management`: 移除 skip-advice 偏好持久化的引用（实际保留该功能，仅修正文档）
- `stage-progress-visualization`: 移除跳读清单作为进度阶段的引用

## Impact

- **后端模型** (`trigger_models.py`): 移除 `SkipListItem`、`SkipList` 类，移除 `ScanFinding.in_skip_list` 字段
- **后端存储** (`reporting.py`): 移除 `SkipListStore` 类，移除 `render_skip_list_markdown()` 函数，移除 `SKIP_LIST_FILENAME` 常量
- **后端 API** (`api_app.py`): 移除 6 个跳读清单端点及 `skip_list_store_for_project()` 辅助函数
- **后端进度** (`project_workspace.py`): 移除 `skip_item_count` 统计及"跳读清单"阶段
- **后端工作流** (`workflow_services.py`): 保留 `skip_advice_setting` 变量（传递给 AI prompt，不受影响）
- **前端类型** (`types.ts`): 移除 `SkipListItem`、`SkipListResponse` 接口，移除 `in_skip_list` 字段，保留 `generate_skip_advice` 和 `skip_advice`
- **前端 API** (`client.ts`): 移除 6 个跳读清单 API 方法
- **前端页面** (`TriggerScanPage.tsx`): 移除跳读标签页、相关状态、函数、UI 组件，保留"生成跳读建议"开关和跳读建议展示
- **前端样式** (`styles.css`): 移除 `.skip-chapter-group` 相关样式
- **测试** (`test_project_workspace.py`): 移除跳读清单相关测试数据和断言
- **规范文档**: 更新 `trigger-scan-results`、`webui-workbench`、`managed-project-outputs`、`configuration-management`、`stage-progress-visualization` 规范
