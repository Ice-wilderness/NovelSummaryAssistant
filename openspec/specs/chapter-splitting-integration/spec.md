## Purpose
Define how whole-novel source file splitting is integrated into the novel summary page while remaining distinct from already split chapter uploads.

## Requirements
### Requirement: 小说总结页面支持上传源文件进行章节分割
小说总结页面 SHALL 提供上传整本小说源文件（TXT）的入口，与已分割章节文件上传区域在 UI 上明确区分，并支持对源文件执行章节分割后直接将结果纳入项目章节列表。

#### Scenario: 用户上传源文件并执行分割
- **WHEN** 用户在小说总结页面上传一个整本小说 TXT 文件到"源文件（待分割）"区域，选择分割模式并点击"开始分割"
- **THEN** 系统执行章节分割，将生成的章节文件写入项目 inputs 目录，更新项目的 uploads 列表，并在页面上展示分割后的章节列表

#### Scenario: 分割后章节直接作为项目章节
- **WHEN** 分割完成，更新的 uploads 列表自动反映在"已分割章节"区域
- **THEN** 用户无需手动重新导入分割后的章节文件，可直接点击"开始总结"或"仅小总结"启动总结任务

#### Scenario: 小说总结入口分割不影响独立分割页行为
- **WHEN** 用户在独立的"章节分割"页面执行分割
- **THEN** 分割结果仍写入独立导出目录，不自动关联到任何小说总结项目

### Requirement: 源文件与已分割章节的 UI 区分
小说总结页面的"项目与文件"区域 SHALL 包含两个明确区分的文件管理区域：源文件（待分割）区域和已分割章节区域。

#### Scenario: 源文件区域显示
- **WHEN** 用户打开小说总结页面
- **THEN** 页面显示"源文件（待分割）"上传区域，标注为上传整本小说 TXT 用于分割，仅接受单个 TXT 文件

#### Scenario: 章节列表区域显示
- **WHEN** 页面加载项目数据
- **THEN** 页面在源文件区域下方显示"已分割章节"区域，列出当前项目的所有已上传/已分割的章节文件

#### Scenario: 源文件区域无文件时不影响章节列表
- **WHEN** 源文件区域没有上传文件但章节列表有文件
- **THEN** 开始总结按钮仍然可用（基于章节列表判断），分割按钮不可用
