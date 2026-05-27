## ADDED Requirements

### Requirement: 小说总结源文件分割失败保持项目不变
小说总结页面的源文件分割入库流程 SHALL 在分割失败时展示可操作错误，并保持项目已有章节列表不变。

#### Scenario: 源文件分割校验失败
- **WHEN** 用户在小说总结页面上传源文件并使用无效或高风险分割模式确认分割
- **THEN** 后端 MUST 返回 400 错误，说明分割失败原因
- **AND** 项目的既有 uploads 列表 MUST 保持不变

#### Scenario: 源文件分割成功后替换章节列表
- **WHEN** 用户在小说总结页面使用有效分割模式确认分割
- **THEN** 后端 SHALL 将生成的单章文件写入项目 inputs 目录
- **AND** 后端 SHALL 用生成的章节文件更新项目 uploads 列表
