## 1. 后端数据模型

- [x] 1.1 从 `webui_backend/trigger_models.py` 移除 `SkipListItem` 和 `SkipList` 数据类，移除 `ScanFinding.in_skip_list` 字段，同步更新 `from_dict`/`to_dict` 方法

## 2. 后端存储逻辑

- [x] 2.1 从 `logic/trigger_scan/reporting.py` 移除 `SkipListStore` 类、`render_skip_list_markdown()` 函数和 `SKIP_LIST_FILENAME` 常量，移除 `SkipListItem`/`SkipList` 的 import

## 3. 后端 API

- [x] 3.1 从 `webui_backend/api_app.py` 移除 6 个跳读清单端点及 `skip_list_store_for_project()` 辅助函数，移除相关 import

## 4. 后端进度展示

- [x] 4.1 从 `webui_backend/project_workspace.py` 的 `_scan_trigger_scan_artifacts()` 移除 `skip_item_count` 统计及 `SKIP_LIST_FILENAME` 读取
- [x] 4.2 从 `_project_progress_novel_summary()` 移除"跳读清单"阶段条目

## 5. 前端类型定义

- [x] 5.1 从 `frontend/src/api/types.ts` 移除 `SkipListItem` 和 `SkipListResponse` 接口，从 `ScanFindingResponse` 移除 `in_skip_list` 字段

## 6. 前端 API 客户端

- [x] 6.1 从 `frontend/src/api/client.ts` 移除 6 个跳读清单 API 方法及 `SkipListItem`/`SkipListResponse` import

## 7. 前端页面

- [x] 7.1 从 `frontend/src/views/TriggerScanPage.tsx` 移除 `TriggerTab` 类型中的 `"skip"`、`triggerTabs` 中的跳读标签页、`skipList`/`skipDraft` 状态及 `emptySkipDraft`
- [x] 7.2 移除 `loadSkipList`、`addFindingToSkipList`、`addManualSkipItem`、`updateSkipItem`、`deleteSkipItem`、`exportSkipList`、`updateSkipDraft` 函数及 `skipGroups` memo
- [x] 7.3 移除扫描结果中"加入跳读清单"/"已加入"按钮（`renderFindingActions` 中相关 JSX）
- [x] 7.4 移除 `renderSkipTab` 函数及标签页条件渲染
- [x] 7.5 移除 `loadSkipList` 调用（`useEffect` 依赖、`onTaskTerminal` 回调等）
- [x] 7.6 移除 GuidancePanel 中"加入独立跳读清单"文本描述

## 8. 前端样式

- [x] 8.1 从 `frontend/src/styles.css` 移除 `.skip-chapter-group` 相关 CSS 规则

## 9. 测试

- [x] 9.1 从 `tests/test_project_workspace.py` 移除跳读清单 JSON 测试数据及"跳读清单"阶段断言
- [x] 9.2 从 `tests/test_trigger_scan_reporting.py` 移除 `SkipListStore`/`SkipListItem` import 及 `test_skip_list_store_add_update_remove_group_and_export` 测试
- [x] 9.3 从 `tests/test_trigger_models.py` 移除 `SkipList`/`SkipListItem` import 及 `test_scan_report_and_skip_list_round_trip` 测试
- [x] 9.4 从 `tests/test_api_app.py` 移除跳读清单 API 调用及断言
- [x] 9.5 从 `logic/trigger_scan/__init__.py` 移除 `SkipListStore` 导出

## 10. 验证

- [x] 10.1 验证雷点扫描工作台仅显示 3 个标签页（档案、扫描、结果），跳读功能已完全移除
- [x] 10.2 验证扫描配置中"生成跳读建议"开关和结果中跳读建议展示正常工作（保留，未修改）
- [x] 10.3 验证项目进度面板不再显示"跳读清单"阶段
- [x] 10.4 运行 `python -m pytest tests/test_project_workspace.py tests/test_trigger_models.py tests/test_trigger_scan_reporting.py -v` — 37 passed
