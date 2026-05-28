# 实施记录

## 已落地范围

- 配置损坏恢复：API 配置、用户设置和章节模式配置损坏时备份为同级 `.bak` 或非覆盖 `.bak.N`，再恢复默认值并返回配置域 warning。
- 输出目录验证：主动保存、任务启动、输出迁移和 workflow task 创建使用 strict 验证；历史项目、导入项目和项目详情读取使用 compat fallback warning。
- 默认目录回退：前端保留无效自定义输出目录供用户编辑，并提供“使用默认输出目录”的显式操作。
- 本地路径边界：`open_directory` 仅允许打开当前项目有效输出目录；本地 picker/open 失败在触发控件附近展示。
- 文档同步：稳定性审计 backlog、配置/工作区审计、总览和测试质量记录已更新。

## 验证命令

```text
python -m pytest tests/test_config_service.py
34 passed
```

```text
python -m pytest tests/test_project_workspace.py
43 passed
```

```text
python -m pytest tests/test_api_app.py
81 passed
```

```text
npm run test -- --run src/hooks/useManagedProject.test.tsx src/components/forms/FormControls.test.tsx src/views/ApiConfigPage.test.tsx src/components/patterns/PatternSelector.test.tsx
4 test files passed; 10 tests passed
```

```text
python -m pytest
287 passed in 8.14s
```

```text
npm run test
17 test files passed; 51 tests passed
```

```text
npm run build
TypeScript checks passed; Vite production build completed
```

```text
openspec validate --all
21 passed; 0 failed
```

## 刻意延后

- 不新增远程多人部署安全模型。
- 不新增通用任意本地路径打开 API。
- 不实现配置恢复历史、配置 diff 或损坏配置自动合并。
- 不移除本地文件/目录选择器。
- frozen 打包态本地 picker/open 仍建议后续做人工冒烟验证。
