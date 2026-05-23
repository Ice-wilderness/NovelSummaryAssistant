## REMOVED Requirements

### Requirement: Skip List

**Reason**: 跳读清单功能使用频率极低，用户通常在扫描报告中直接复核条目。维护该功能增加了不必要的代码复杂度、API 数量和 UI 噪音。

**Migration**: 用户已有的 `skip_list.json` 文件不会被自动删除，但不再被系统读取。扫描报告中的"加入跳读清单"按钮已移除。如需保留历史跳读数据，可在升级前通过导出功能导出为 Markdown 文件。
