## 1. 响应解析实现

- [ ] 1.1 在 `logic/llm_api.py` 增加共享的顶层错误与首个 choice 结构校验，并接入非流式分支；在 `tests/test_llm_api.py` 覆盖空 choices、非列表 choices、非对象首项和非对象 error，运行 `python -m unittest tests.test_llm_api.LlmApiErrorJudgmentTests` 验证均产生受控结果且正常响应不回归
- [ ] 1.2 将共享校验接入流式分支，使 `choices: []` 分块跳过且保留已收集内容，并在顶层 error 或无效结构时进入现有重试；增加可迭代 SSE 测试响应及内容—空 choices—内容、仅空 choices、流式 error 用例，运行对应的 `tests.test_llm_api` 流式测试验证无 `IndexError` 且上游错误可诊断
- [ ] 1.3 核对有效 choice 的 delta/message/content 提取仍使用首候选项并继续经过现有内容校验链，运行 `python -m unittest tests.test_llm_api` 验证 LLM API 全部单元测试通过

## 2. 集成验证

- [ ] 2.1 运行 `python -m unittest discover -s tests` 验证完整测试套件通过，并检查失败日志与 API 配置格式未发生非预期变化
- [ ] 2.2 运行 `openspec validate fix-empty-llm-stream-choices --strict` 验证实施后的规格与任务状态有效，并通过 `git diff --check` 确认没有空白错误
