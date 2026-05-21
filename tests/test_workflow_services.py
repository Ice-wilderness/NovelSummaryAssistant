import unittest
from unittest import mock

from webui_backend.config_models import (
    ApiConfig,
    ArticleSummaryRequest,
    NovelSummaryRequest,
    SplitterRequest,
)
from webui_backend.task_runtime import TaskRuntime, TaskType
from webui_backend.workflow_services import (
    create_article_summary_runner,
    create_novel_summary_runner,
    create_splitter_runner,
    make_runtime_log_callback,
    select_api_configs,
)


class WorkflowServicesTests(unittest.IsolatedAsyncioTestCase):
    def test_select_api_configs_resolves_env_key(self):
        configs = [
            ApiConfig.from_dict(
                {
                    "id": "api1",
                    "key": "local",
                    "key_env_var": "NSA_TEST_KEY",
                    "is_active": True,
                }
            )
        ]

        with mock.patch.dict("os.environ", {"NSA_TEST_KEY": "env"}, clear=False):
            selected = select_api_configs(configs)

        self.assertEqual(selected[0]["key"], "env")

    def test_runtime_log_callback_emits_structured_event(self):
        events = []
        callback = make_runtime_log_callback(lambda **kwargs: events.append(kwargs))

        callback(source_id="api1", message="hello", status="INFO", progress_text="Working")

        self.assertEqual(events[0]["event_type"], "log")
        self.assertEqual(events[0]["source_id"], "api1")
        self.assertEqual(events[0]["progress_text"], "Working")

    async def test_article_runner_uses_existing_workflow(self):
        runtime = TaskRuntime()
        request = ArticleSummaryRequest("folder", selected_files=["a.txt"])

        with mock.patch(
            "webui_backend.workflow_services.run_article_summary_process",
            new=mock.AsyncMock(return_value=True),
        ):
            record = await runtime.start_task(
                TaskType.ARTICLE_SUMMARY,
                create_article_summary_runner(request, [{"id": "api1"}]),
            )
            final = await runtime.wait_for_terminal(record.task_id)

        self.assertEqual(final.result_summary, "success")

    async def test_novel_runner_passes_summary_batch_size(self):
        runtime = TaskRuntime()
        request = NovelSummaryRequest(
            "novel",
            summary_batch_size=10,
            big_summary_batch_size=3,
            super_summary_threshold=2,
        )

        with mock.patch(
            "webui_backend.workflow_services.run_summarization_process",
            new=mock.AsyncMock(return_value=True),
        ) as summarize:
            record = await runtime.start_task(
                TaskType.NOVEL_SUMMARY,
                create_novel_summary_runner(request, [{"id": "api1"}]),
            )
            final = await runtime.wait_for_terminal(record.task_id)

        self.assertEqual(final.result_summary, "success")
        self.assertEqual(summarize.await_args.kwargs["summary_batch_size"], 10)

    async def test_splitter_runner_uses_existing_workflow(self):
        runtime = TaskRuntime()
        request = SplitterRequest("source.txt", "out")

        with mock.patch(
            "webui_backend.workflow_services.split_novel_into_chapter_files",
            return_value=(True, 2),
        ):
            record = await runtime.start_task(
                TaskType.CHAPTER_SPLIT,
                create_splitter_runner(request),
            )
            final = await runtime.wait_for_terminal(record.task_id)

        self.assertEqual(final.result_summary, "generated 2 files")


if __name__ == "__main__":
    unittest.main()
