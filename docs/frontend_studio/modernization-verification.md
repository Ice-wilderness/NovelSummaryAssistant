# Studio WebUI 现代化验证记录

日期：2026-05-30

## 验证命令

在 `frontend/` 下执行：

```bash
npm run typecheck
npm run test
npm run build
npm run check:desktop
```

在仓库根目录执行：

```bash
openspec validate --changes modernize-studio-webui
```

当前验证结果：

- TypeScript typecheck：通过。
- Vitest：19 个测试文件、64 个测试通过。
- Vite production build：通过。
- PC 桌面视觉检查：7 个场景通过并输出截图到 `.codex_tmp/studio-desktop-checks/`。
- OpenSpec validate：通过。

## 功能完整性核对

| 工作流 | 已核对能力 |
| --- | --- |
| 全局工作台 | Studio 导航、当前任务状态、暂停/恢复/取消、阶段流、当前步骤 inspector、全局/API 日志切换、配置提示、项目署名。 |
| 小说总结 | 项目历史/导入/保存、新建项目、源 TXT 上传、分割模式、预览、章节导入、输出目录、API 选择、任务参数、字数设置、阶段进度、修复提示、任务启动。 |
| 文章总结 | 项目历史/导入/保存、文章上传、输出目录、项目进度、段落/最终总结字数、任务启动、partial_failed 可用结果与失败详情。 |
| 自定义总结 | 项目历史/导入/保存、参考材料上传、输出目录、API 选择、自定义指令、结果显示、partial_failed 可用结果与失败详情。 |
| 章节分割 | 源文件选择/拖拽、默认/正则/标题列表模式、分卷处理、预览、确认分割、输出目录选择、错误展示。 |
| 雷点扫描 | 档案管理、扫描配置、预检、启动/续扫、live findings、报告历史/详情、过滤、分页、剧透、复核、备注、上下文、导出、删除、警告状态。 |
| 提示词 | 工作流选择、节点列表、消息角色/顺序/内容编辑、模块引用、模块管理、未保存状态、保存/重置节点、保存/删除模块。 |
| API 配置 | 配置恢复警告、预设增删改、模型列表拉取、Key 显示/隐藏、环境变量、流式/启用状态、默认导出目录、最少输出字数、保存/重载。 |

## 清理记录

- 移除了 `styles.css` 中旧三栏工作台壳的过渡样式：`.workbench`、`.sidebar`、`.brand-block`、`.side-nav`、`.nav-button`、`.topbar`、`.task-controls` 等。
- 保留仍被业务页面使用的共享样式：表单、上传、日志、提示词编辑器、雷点扫描、fallback workspace surface 等。
- 新的工作台壳样式集中在 `studio.css` 的 `.studio-*` 与页面级 Studio 区块中。
