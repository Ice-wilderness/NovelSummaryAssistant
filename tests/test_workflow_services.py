import asyncio
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from logic.trigger_scan.reporting import TriggerScanReportStore
from logic.trigger_scan.scan_state import ScanStateStore
from webui_backend.config_models import (
    ApiConfig,
    ArticleSummaryRequest,
    CustomSummaryRequest,
    NovelSummaryRequest,
    SplitterRequest,
    TriggerScanRequest,
)
from webui_backend.task_runtime import PauseSignal, TaskRecord, TaskRuntime, TaskType
from webui_backend.trigger_models import (
    ScanFinding,
    ScanReport,
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


def _precise_finding_output(finding_id: str = "f1") -> str:
    return json.dumps(
        [
            {
                "finding_id": finding_id,
                "rule_id": "rule_a",
                "severity": 3,
                "confidence": 0.9,
                "paragraph_ids": ["B0_P001"],
                "is_main_plot": False,
                "spoiler_levels": {
                    "low": {"description": "low"},
                    "standard": {"description": "standard"},
                    "detailed": {
                        "description": "detailed",
                        "evidence_quote": "正文",
                    },
                },
            }
        ],
        ensure_ascii=False,
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

    async def test_trigger_scan_runner_waits_while_paused_before_api_call(self):
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
            pause_signal = PauseSignal()
            pause_signal.set()
            runner = create_trigger_scan_runner(
                request,
                _trigger_profile(),
                [{"id": "api1"}],
            )
            record = TaskRecord(task_id="paused-task", task_type=TaskType.TRIGGER_SCAN.value)
            events = []

            with mock.patch(
                "webui_backend.workflow_services.get_llm_summary_with_config",
                new=mock.AsyncMock(return_value=json.dumps([])),
            ) as summarize:
                task = asyncio.create_task(runner(record, pause_signal, lambda **kwargs: events.append(kwargs)))
                await asyncio.sleep(0.05)

                summarize.assert_not_awaited()

                pause_signal.clear()
                result = await asyncio.wait_for(task, timeout=1)

            self.assertTrue(str(result).startswith("report:"))
            self.assertTrue(any(event.get("event_type") == "progress" for event in events))

    async def test_trigger_scan_resume_progress_uses_selected_total(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            first_chapter = root / "第001章.txt"
            second_chapter = root / "第002章.txt"
            first_chapter.write_text("第一章\n正文", encoding="utf-8")
            second_chapter.write_text("第二章\n正文", encoding="utf-8")
            config = TriggerScanConfig(
                scan_api_ids=["api1"],
                verification_enabled=False,
            )
            report_store = TriggerScanReportStore(root)
            report_store.save_report(
                ScanReport(
                    report_id="report_previous",
                    project_slug="project",
                    profile_id="profile",
                    profile_name="Profile",
                    scan_mode="precise",
                    scan_range=config.scan_range,
                    scan_config=config,
                    status="partial_failed",
                )
            )
            state_store = ScanStateStore(root, "previous")
            state_store.create(config.to_dict(), "profile")
            state_store.mark_chapter_complete(str(first_chapter))
            request = TriggerScanRequest(
                project_slug="project",
                source_folder_path=str(root),
                project_output_directory_path=str(root),
                profile_id="profile",
                scan_config=config,
                resume_from_report_id="report_previous",
            )
            runner = create_trigger_scan_runner(
                request,
                _trigger_profile(),
                [{"id": "api1"}],
            )
            events = []

            with mock.patch(
                "webui_backend.workflow_services.get_llm_summary_with_config",
                new=mock.AsyncMock(return_value=json.dumps([])),
            ) as summarize:
                result = await runner(
                    TaskRecord(task_id="resume-task", task_type=TaskType.TRIGGER_SCAN.value),
                    PauseSignal(),
                    lambda **kwargs: events.append(kwargs),
                )

            precise_events = [
                event
                for event in events
                if event.get("event_type") == "progress"
                and event.get("data", {}).get("stage") == "precise_scan"
            ]
            start_event = next(
                event for event in precise_events if event.get("message", "").startswith("并发扫描启动")
            )
            completed_event = next(
                event for event in precise_events if event.get("message", "").startswith("精确扫描已完成")
            )
            precise_stage = next(
                stage
                for stage in completed_event["data"]["stages"]
                if stage["id"] == "precise_scan"
            )

            self.assertEqual(result, "report:report_previous")
            self.assertEqual(summarize.await_count, 1)
            self.assertEqual(start_event["data"]["completed"], 1)
            self.assertEqual(start_event["data"]["total"], 2)
            self.assertEqual(start_event["data"]["selected_total"], 2)
            self.assertEqual(start_event["data"]["completed_from_resume"], 1)
            self.assertEqual(start_event["data"]["pending_total"], 1)
            self.assertEqual(start_event["data"]["processed_current_run"], 0)
            self.assertEqual(completed_event["data"]["completed"], 2)
            self.assertEqual(completed_event["data"]["total"], 2)
            self.assertEqual(completed_event["data"]["processed_current_run"], 1)
            self.assertEqual(precise_stage["completed"], 2)
            self.assertEqual(precise_stage["total"], 2)

    async def test_trigger_scan_resume_marks_historical_and_current_findings(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            first_chapter = root / "第001章.txt"
            second_chapter = root / "第002章.txt"
            first_chapter.write_text("第一章\n旧发现正文", encoding="utf-8")
            second_chapter.write_text("第二章\n新发现正文", encoding="utf-8")
            config = TriggerScanConfig(
                scan_api_ids=["api1"],
                verification_enabled=False,
            )
            report_store = TriggerScanReportStore(root)
            historical_finding = ScanFinding.from_dict(
                {
                    "finding_id": "f_old",
                    "rule_id": "rule_a",
                    "rule_name": "Rule A",
                    "chapter_file": str(first_chapter),
                    "paragraph_ids": ["P001"],
                    "severity": 3,
                    "confidence": 0.9,
                    "review_status": "confirmed",
                    "verification_status": "confirmed",
                }
            )
            report_store.save_report(
                ScanReport(
                    report_id="report_previous",
                    project_slug="project",
                    profile_id="profile",
                    profile_name="Profile",
                    scan_mode="precise",
                    scan_range=config.scan_range,
                    scan_config=config,
                    status="partial_failed",
                    findings=[historical_finding],
                )
            )
            state_store = ScanStateStore(root, "previous")
            state_store.create(config.to_dict(), "profile")
            state_store.mark_chapter_complete(str(first_chapter))
            request = TriggerScanRequest(
                project_slug="project",
                source_folder_path=str(root),
                project_output_directory_path=str(root),
                profile_id="profile",
                scan_config=config,
                resume_from_report_id="report_previous",
            )
            runner = create_trigger_scan_runner(
                request,
                _trigger_profile(),
                [{"id": "api1"}],
            )
            model_output = json.dumps(
                [
                    {
                        "finding_id": "f_new",
                        "rule_id": "rule_a",
                        "severity": 3,
                        "confidence": 0.9,
                        "paragraph_ids": ["B0_P001"],
                        "is_main_plot": False,
                        "spoiler_levels": {
                            "low": {"description": "low"},
                            "standard": {"description": "standard"},
                            "detailed": {
                                "description": "detailed",
                                "evidence_quote": "新发现正文",
                            },
                        },
                    }
                ],
                ensure_ascii=False,
            )

            with mock.patch(
                "webui_backend.workflow_services.get_llm_summary_with_config",
                new=mock.AsyncMock(return_value=model_output),
            ):
                await runner(
                    TaskRecord(task_id="resume-task", task_type=TaskType.TRIGGER_SCAN.value),
                    PauseSignal(),
                    lambda **_kwargs: None,
                )

            saved = report_store.load_report("report_previous")
            findings_by_id = {finding.finding_id: finding for finding in saved.findings}
            self.assertEqual(findings_by_id["f_old"].verification_status, "confirmed")
            self.assertEqual(findings_by_id["f_old"].source_report_id, "report_previous")
            self.assertEqual(findings_by_id["f_old"].source_task_id, "previous")
            self.assertEqual(findings_by_id["f_old"].source_kind, "historical_report")
            self.assertEqual(findings_by_id["f_new"].source_report_id, "report_previous")
            self.assertEqual(findings_by_id["f_new"].source_task_id, "resume-task")
            self.assertEqual(findings_by_id["f_new"].source_kind, "current_run")

    async def test_trigger_scan_resume_reverifies_unknown_historical_findings_with_context(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            first_chapter = root / "第001章.txt"
            second_chapter = root / "第002章.txt"
            first_chapter.write_text("第一章\n可重建上下文", encoding="utf-8")
            second_chapter.write_text("第二章\n继续扫描", encoding="utf-8")
            config = TriggerScanConfig(
                scan_api_ids=["api1"],
                verification_enabled=True,
            )
            report_store = TriggerScanReportStore(root)
            report_store.save_report(
                ScanReport(
                    report_id="report_previous",
                    project_slug="project",
                    profile_id="profile",
                    profile_name="Profile",
                    scan_mode="precise",
                    scan_range=config.scan_range,
                    scan_config=config,
                    status="partial_failed",
                    findings=[
                        ScanFinding.from_dict(
                            {
                                "finding_id": "f_reverify",
                                "rule_id": "rule_a",
                                "rule_name": "Rule A",
                                "chapter_file": str(first_chapter),
                                "paragraph_ids": ["P001"],
                                "severity": 3,
                                "confidence": 0.9,
                            }
                        ),
                        ScanFinding.from_dict(
                            {
                                "finding_id": "f_missing",
                                "rule_id": "rule_a",
                                "rule_name": "Rule A",
                                "chapter_file": "missing.txt",
                                "paragraph_ids": ["P001"],
                                "severity": 3,
                                "confidence": 0.9,
                            }
                        ),
                    ],
                )
            )
            state_store = ScanStateStore(root, "previous")
            state_store.create(config.to_dict(), "profile")
            state_store.mark_chapter_complete(str(first_chapter))
            request = TriggerScanRequest(
                project_slug="project",
                source_folder_path=str(root),
                project_output_directory_path=str(root),
                profile_id="profile",
                scan_config=config,
                resume_from_report_id="report_previous",
            )
            runner = create_trigger_scan_runner(
                request,
                _trigger_profile(),
                [{"id": "api1"}],
            )

            with mock.patch(
                "webui_backend.workflow_services.get_llm_summary_with_config",
                new=mock.AsyncMock(
                    side_effect=[
                        json.dumps([]),
                        json.dumps(
                            {
                                "items": [
                                    {
                                        "finding_id": "f_reverify",
                                        "verdict": "confirmed",
                                        "reason": "context rebuilt",
                                    }
                                ]
                            }
                        ),
                    ]
                ),
            ) as summarize:
                await runner(
                    TaskRecord(task_id="resume-task", task_type=TaskType.TRIGGER_SCAN.value),
                    PauseSignal(),
                    lambda **_kwargs: None,
                )

            verification_variables = summarize.await_args_list[1].args[2]
            saved = report_store.load_report("report_previous")
            findings_by_id = {finding.finding_id: finding for finding in saved.findings}

            self.assertEqual(summarize.await_count, 2)
            self.assertIn("f_reverify", verification_variables["first_pass_findings_json"])
            self.assertNotIn("f_missing", verification_variables["first_pass_findings_json"])
            self.assertEqual(findings_by_id["f_reverify"].verification_status, "confirmed")
            self.assertEqual(findings_by_id["f_reverify"].verification_note, "context rebuilt")
            self.assertEqual(findings_by_id["f_missing"].verification_status, "unverified")
            self.assertTrue(any("unverified finding f_missing" in warning for warning in saved.warnings))

    async def test_trigger_scan_failure_with_unscanned_chapters_saves_partial_failed_report(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "第001章.txt").write_text("第一章\n正文", encoding="utf-8")
            (root / "第002章.txt").write_text("第二章\n正文", encoding="utf-8")
            config = TriggerScanConfig(
                scan_api_ids=["api1"],
                verification_enabled=False,
                precise_chapter_batch_size=1,
            )
            request = TriggerScanRequest(
                project_slug="project",
                source_folder_path=str(root),
                project_output_directory_path=str(root),
                profile_id="profile",
                scan_config=config,
            )
            runner = create_trigger_scan_runner(
                request,
                _trigger_profile(),
                [{"id": "api1"}],
            )

            with mock.patch(
                "webui_backend.workflow_services.get_llm_summary_with_config",
                new=mock.AsyncMock(
                    side_effect=[_precise_finding_output("f_first"), RuntimeError("scan boom")]
                ),
            ):
                with self.assertRaisesRegex(RuntimeError, "scan boom"):
                    await runner(
                        TaskRecord(task_id="partial-task", task_type=TaskType.TRIGGER_SCAN.value),
                        PauseSignal(),
                        lambda **_kwargs: None,
                    )

            saved = TriggerScanReportStore(root).load_report("report_partial-task")
            self.assertEqual(saved.status, "partial_failed")
            self.assertEqual(saved.failed_stage, "precise_scan")
            self.assertEqual(saved.unscanned_chapters, ["第002章.txt"])
            self.assertEqual([finding.finding_id for finding in saved.findings], ["f_first"])
            self.assertTrue(any("partial_failed at precise_scan" in warning for warning in saved.warnings))

    async def test_trigger_scan_post_scan_failure_saves_partial_failed_report(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "第001章.txt").write_text("第一章\n正文", encoding="utf-8")
            config = TriggerScanConfig(
                scan_api_ids=["api1"],
                verification_enabled=True,
            )
            request = TriggerScanRequest(
                project_slug="project",
                source_folder_path=str(root),
                project_output_directory_path=str(root),
                profile_id="profile",
                scan_config=config,
            )
            runner = create_trigger_scan_runner(
                request,
                _trigger_profile(),
                [{"id": "api1"}],
            )

            with mock.patch(
                "webui_backend.workflow_services.get_llm_summary_with_config",
                new=mock.AsyncMock(
                    side_effect=[_precise_finding_output("f_first"), RuntimeError("verify boom")]
                ),
            ):
                with self.assertRaisesRegex(RuntimeError, "verify boom"):
                    await runner(
                        TaskRecord(task_id="post-scan-task", task_type=TaskType.TRIGGER_SCAN.value),
                        PauseSignal(),
                        lambda **_kwargs: None,
                    )

            saved = TriggerScanReportStore(root).load_report("report_post-scan-task")
            self.assertEqual(saved.status, "partial_failed")
            self.assertEqual(saved.failed_stage, "verification")
            self.assertEqual(saved.unscanned_chapters, [])
            self.assertEqual([finding.finding_id for finding in saved.findings], ["f_first"])


if __name__ == "__main__":
    unittest.main()
