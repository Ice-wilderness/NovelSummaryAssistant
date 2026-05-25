# AGENTS.md

本文件为本仓库内 AI 编码助手的工作约定。

## 默认语言

- 与用户沟通时默认使用简体中文，除非用户明确要求使用其他语言。
- 面向用户的计划、文档、报告、说明、提案等内容默认使用简体中文。

## Git 提交要求

- 执行任务时，将工作按功能块拆分。
- 每完成一个独立、可验证的功能块，都应提交到 Git 仓库一次。
- 提交前应确认工作区只包含本功能块相关改动。
- 提交信息必须使用 Conventional Commits 风格。
- 提交信息必须使用英文。

推荐格式：

```text
<type>(<scope>): <summary>
```

常用类型：

- `feat`: 新功能
- `fix`: 缺陷修复
- `docs`: 文档变更
- `test`: 测试相关
- `refactor`: 不改变行为的重构
- `style`: 代码格式或样式调整
- `chore`: 构建、配置、维护类变更

示例：

```text
feat(workspace): add output directory opener
fix(api): handle missing project progress file
docs(openspec): update implementation tasks
```

## 执行原则

- 修改前先检查相关文件和当前 Git 状态。
- 保持改动小而聚焦，不做无关重构。
- 每个功能块完成后运行最相关的验证命令。
- 如果无法运行验证，应说明原因和已完成的替代检查。
- 不要重写历史、强推、删除分支或执行破坏性操作，除非用户明确要求。
