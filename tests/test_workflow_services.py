import asyncio
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from webui_backend.config_models import (
    ApiConfig,
    ArticleSummaryRequest,
    CustomSummaryRequest,
    NovelSummaryRequest,
    SplitterRequest,
    TriggerScanRequest,
)
from webui_backend.task_runtime import TaskRuntime, TaskType
from webui_backend.trigger_models import (
    TriggerProfile,
    TriggerRule,
    TriggerRuleGroup,
    TriggerScanConfig,
)
from webui_backend.workflow_services import (
    create_article_summary_runner,
    create_custom_summary_runner,
    create_novel_summary_runner,
    create_splitter_runner,
    create_trigger_scan_runner,
    make_runtime_log_callback,
    select_api_configs,
)


def _trigger_profile():
    return TriggerProfile(
        id="profile",
        name="Profile",
        rule_groups=[TriggerRuleGroup(id="group", name="Group", rules=["rule_a"])],
        rules=[
            TriggerRule(
                id="rule_a",
                name="Rule A",
                group_id="group",
                severity_threshold=2,
            )
        ],
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
            summary_output_format="txt",
            big_summary_batch_size=3,
            super_summary_threshold=2,
            stop_after_small_summary=True,
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
        self.assertEqual(summarize.await_args.kwargs["summary_output_format"], "txt")
        self.assertTrue(summarize.await_args.kwargs["stop_after_small_summary"])

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

    async def test_summary_runners_propagate_cancellation(self):
        cases = [
            (
                TaskType.NOVEL_SUMMARY,
                create_novel_summary_runner(NovelSummaryRequest("novel"), [{"id": "api1"}]),
                "webui_backend.workflow_services.run_summarization_process",
            ),
            (
                TaskType.ARTICLE_SUMMARY,
                create_article_summary_runner(ArticleSummaryRequest("articles"), [{"id": "api1"}]),
                "webui_backend.workflow_services.run_article_summary_process",
            ),
            (
                TaskType.CUSTOM_SUMMARY,
                create_custom_summary_runner(
                    CustomSummaryRequest(["a.txt"], "summarize", "api1"),
                    {"id": "api1"},
                ),
                "webui_backend.workflow_services.run_custom_summary_process",
            ),
        ]

        for task_type, runner, patch_target in cases:
            with self.subTest(task_type=task_type.value):
                runtime = TaskRuntime()
                with mock.patch(
                    patch_target,
                    new=mock.AsyncMock(side_effect=asyncio.CancelledError()),
                ):
                    record = await runtime.start_task(task_type, runner)
                    final = await runtime.wait_for_terminal(record.task_id)

                self.assertEqual(final.status.value, "cancelled")

    async def test_splitter_runner_propagates_cancellation(self):
        runtime = TaskRuntime()
        request = SplitterRequest("source.txt", "out")

        with mock.patch(
            "webui_backend.workflow_services.split_novel_into_chapter_files",
            side_effect=asyncio.CancelledError(),
        ):
            record = await runtime.start_task(
                TaskType.CHAPTER_SPLIT,
                create_splitter_runner(request),
            )
            final = await runtime.wait_for_terminal(record.task_id)

        self.assertEqual(final.status.value, "cancelled")

    async def test_trigger_scan_runner_scans_original_chapters_without_coarse_scan(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "第001章.txt").write_text("第一章\n正文", encoding="utf-8")
            request = TriggerScanRequest(
                project_slug="project",
                source_folder_path=str(root),
                project_output_directory_path=str(root),
                profile_id="profile",
                scan_config=TriggerScanConfig(
                    scan_api_ids=["api1"],
                    verification_enabled=False,
                ),
            )
            runtime = TaskRuntime()

            with mock.patch(
                "webui_backend.workflow_services.get_llm_summary_with_config",
                new=mock.AsyncMock(return_value=json.dumps([])),
            ) as summarize:
                record = await runtime.start_task(
                    TaskType.TRIGGER_SCAN,
                    create_trigger_scan_runner(
                        request,
                        _trigger_profile(),
                        [{"id": "api1"}],
                    ),
                )
                final = await runtime.wait_for_terminal(record.task_id)

            self.assertEqual(final.status.value, "success")
            self.assertTrue(str(final.result_summary).startswith("report:"))
            self.assertTrue(
                (root / "trigger_scan" / "reports" / f"report_{record.task_id}.json").exists()
            )
            self.assertTrue(
                any(event.event_type == "progress" and event.data.get("stage") == "precise_scan" for event in final.events)
            )
            self.assertFalse(
                any(event.event_type == "progress" and event.data.get("stage") == "coarse_scan" for event in final.events)
            )
            self.assertEqual(summarize.await_args.kwargs["task_info"]["stage"], "trigger_precise_scan")

    async def test_trigger_scan_runner_propagates_cancellation(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "第001章.txt").write_text("第一章\n正文", encoding="utf-8")
            request = TriggerScanRequest(
                project_slug="project",
                source_folder_path=str(root),
                project_output_directory_path=str(root),
                profile_id="profile",
                scan_config=TriggerScanConfig(
                    scan_api_ids=["api1"],
                    verification_enabled=False,
                ),
            )
            runtime = TaskRuntime()

            with mock.patch(
                "webui_backend.workflow_services.get_llm_summary_with_config",
                new=mock.AsyncMock(side_effect=asyncio.CancelledError()),
            ):
                record = await runtime.start_task(
                    TaskType.TRIGGER_SCAN,
                    create_trigger_scan_runner(
                        request,
                        _trigger_profile(),
                        [{"id": "api1"}],
                    ),
                )
                final = await runtime.wait_for_terminal(record.task_id)

            self.assertEqual(final.status.value, "cancelled")



if __name__ == "__main__":
    unittest.main()
