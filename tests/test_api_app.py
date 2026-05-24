import importlib.util
import asyncio
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from logic.prompts import USER_FACING_SMALL_CHAR_SUBDIR, USER_FACING_SMALL_PLOT_SUBDIR
from logic.trigger_scan.reporting import TriggerScanReportStore
from webui_backend.trigger_models import (
    ScanFinding,
    ScanReport,
    ScanReportSummary,
    TriggerScanConfig,
)
from webui_backend.project_workspace import (
    OUTPUT_OWNERSHIP_FILENAME,
    OUTPUT_OWNERSHIP_OWNER,
    OUTPUT_OWNERSHIP_PURPOSE,
)


FASTAPI_AVAILABLE = importlib.util.find_spec("fastapi") is not None


@unittest.skipUnless(FASTAPI_AVAILABLE, "FastAPI is not installed")
class ApiAppTests(unittest.TestCase):
    def setUp(self):
        from fastapi.testclient import TestClient
        from webui_backend.api_app import create_app

        self.tmpdir = tempfile.TemporaryDirectory()
        self.client = TestClient(
            create_app(
                api_config_path=os.path.join(self.tmpdir.name, "api_configs.json"),
                prompt_cache_dir=os.path.join(self.tmpdir.name, "prompt_cache"),
                runtime_base_path=os.path.join(self.tmpdir.name, "runtime"),
            )
        )

    def tearDown(self):
        self.tmpdir.cleanup()

    def assertSamePath(self, actual, expected):
        self.assertEqual(
            os.path.normcase(os.path.normpath(actual)),
            os.path.normcase(os.path.normpath(expected)),
        )

    def test_health(self):
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    def test_api_config_round_trip_masks_key(self):
        response = self.client.post(
            "/api/config/api",
            json=[
                {
                    "id": "api1",
                    "url": "http://example.test/v1",
                    "key": "secret",
                    "model": "model",
                }
            ],
        )
        self.assertEqual(response.status_code, 200)
        item = response.json()["items"][0]
        self.assertNotEqual(item["key"], "secret")
        self.assertTrue(item["has_key"])
        self.assertEqual(item["display_name"], "api1")

    def test_api_config_rejects_duplicate_display_names(self):
        response = self.client.post(
            "/api/config/api",
            json=[
                {"id": "api1", "display_name": "主力 API"},
                {"id": "api2", "display_name": "主力 API"},
            ],
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("不能重复", response.json()["detail"])

    def test_user_settings_save_load_and_clear_default_export_directory(self):
        export_dir = os.path.join(self.tmpdir.name, "user-exports")

        save_response = self.client.post(
            "/api/settings",
            json={"default_export_directory": export_dir, "minimum_output_characters": 120},
        )
        load_response = self.client.get("/api/settings")
        clear_response = self.client.delete("/api/settings/default-export-directory")

        self.assertEqual(save_response.status_code, 200)
        self.assertSamePath(save_response.json()["default_export_directory"], export_dir)
        self.assertEqual(save_response.json()["minimum_output_characters"], 120)
        self.assertTrue(os.path.isdir(export_dir))
        self.assertSamePath(load_response.json()["default_export_directory"], export_dir)
        self.assertEqual(load_response.json()["minimum_output_characters"], 120)
        self.assertEqual(clear_response.json()["default_export_directory"], "")
        self.assertEqual(clear_response.json()["minimum_output_characters"], 120)

    def test_user_settings_rejects_file_default_export_directory(self):
        export_file = os.path.join(self.tmpdir.name, "exports.txt")
        Path(export_file).write_text("not a directory", encoding="utf-8")

        response = self.client.post(
            "/api/settings",
            json={"default_export_directory": export_file},
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("不能是文件", response.json()["detail"])

    def test_user_settings_rejects_invalid_minimum_output_characters(self):
        response = self.client.post(
            "/api/settings",
            json={"default_export_directory": "", "minimum_output_characters": -1},
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("不能小于 0", response.json()["detail"])

    def test_prompts_load_and_save(self):
        prompt_response = self.client.get("/api/prompts").json()
        prompts = prompt_response["items"]
        key = prompts[0]["key"]

        response = self.client.post(f"/api/prompts/{key}", json={"text": "changed"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["text"], "changed")
        self.assertIn("workflow_config", prompt_response)
        self.assertIn("workflows", prompt_response["workflow_config"])

    def test_prompt_node_save_and_reset(self):
        save_response = self.client.post(
            "/api/prompts/nodes/prompt_article_section",
            json={
                "messages": [
                    {"id": "system-1", "role": "system", "content": "system text"},
                    {"id": "user-1", "role": "user", "content": "user text"},
                ]
            },
        )

        self.assertEqual(save_response.status_code, 200)
        self.assertEqual(
            [message["role"] for message in save_response.json()["messages"]],
            ["system", "user"],
        )

        reset_response = self.client.post("/api/prompts/nodes/prompt_article_section/reset")

        self.assertEqual(reset_response.status_code, 200)
        self.assertEqual(reset_response.json()["messages"][0]["role"], "user")

    def test_prompt_node_save_returns_clear_module_reference_error(self):
        response = self.client.post(
            "/api/prompts/nodes/prompt_article_section",
            json={
                "messages": [
                    {
                        "id": "user-1",
                        "role": "user",
                        "content": "{{module:missing_module}}\n正文",
                    }
                ]
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("Unknown prompt module reference", response.json()["detail"])

    def test_prompt_module_save_and_delete(self):
        save_response = self.client.post(
            "/api/prompts/modules",
            json={"id": "style_module", "name": "风格模块", "content": "保持简洁"},
        )
        self.assertEqual(save_response.status_code, 200)
        self.assertIn(
            "style_module",
            [module["id"] for module in save_response.json()["modules"]],
        )

        delete_response = self.client.delete("/api/prompts/modules/style_module")

        self.assertEqual(delete_response.status_code, 200)
        self.assertNotIn(
            "style_module",
            [module["id"] for module in delete_response.json()["modules"]],
        )

    def test_start_and_query_task(self):
        self.client.post(
            "/api/config/api",
            json=[
                {
                    "id": "api1",
                    "url": "http://example.test/v1",
                    "key": "secret",
                    "model": "model",
                }
            ],
        )
        response = self.client.post(
            "/api/tasks/article",
            json={"source_folder_path": "folder", "selected_files": ["a.txt"]},
        )
        self.assertEqual(response.status_code, 200)
        task_id = response.json()["task_id"]

        status_response = self.client.get(f"/api/tasks/{task_id}")
        self.assertEqual(status_response.status_code, 200)
        self.assertEqual(status_response.json()["task_id"], task_id)

    def test_list_tasks_returns_existing_records(self):
        self.client.post(
            "/api/config/api",
            json=[
                {
                    "id": "api1",
                    "url": "http://example.test/v1",
                    "key": "secret",
                    "model": "model",
                }
            ],
        )
        task_response = self.client.post(
            "/api/tasks/article",
            json={"source_folder_path": "folder", "selected_files": ["a.txt"]},
        )
        task_id = task_response.json()["task_id"]

        response = self.client.get("/api/tasks")

        self.assertEqual(response.status_code, 200)
        task_ids = [item["task_id"] for item in response.json()["items"]]
        self.assertIn(task_id, task_ids)

    def test_task_events_stream_ends_after_terminal_event(self):
        from webui_backend.task_runtime import TaskType

        async def runner(record, pause_signal, emit):
            return "done"

        runtime = self.client.app.state.runtime
        record = asyncio.run(runtime.start_task(TaskType.MODEL_FETCH, runner))
        asyncio.run(runtime.wait_for_terminal(record.task_id))

        with self.client.stream("GET", f"/api/tasks/{record.task_id}/events") as response:
            lines = list(response.iter_lines())

        self.assertEqual(response.status_code, 200)
        data_lines = [line for line in lines if line.startswith("data: ")]
        self.assertEqual(len(data_lines), 1)
        event = json.loads(data_lines[0].removeprefix("data: "))
        self.assertEqual(event["status"], "success")

    def test_invalid_task_request_returns_422_or_500_free_error(self):
        response = self.client.post("/api/tasks/splitter", json={"mode": "bad"})
        self.assertIn(response.status_code, {400, 422})

    def test_model_fetch_uses_saved_key_for_masked_public_config(self):
        self.client.post(
            "/api/config/api",
            json=[
                {
                    "id": "api1",
                    "url": "http://example.test/v1",
                    "key": "secret",
                    "model": "model",
                }
            ],
        )
        public_config = self.client.get("/api/config/api").json()["items"][0]

        with mock.patch(
            "webui_backend.api_app.fetch_available_models",
            new=mock.AsyncMock(return_value=(["model-a"], None)),
        ) as fetch_models:
            response = self.client.post("/api/models", json=public_config)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["items"], ["model-a"])
        self.assertEqual(fetch_models.await_args.args[1], "secret")

    def test_trigger_profiles_default_and_create(self):
        list_response = self.client.get("/api/trigger-profiles")
        create_response = self.client.post(
            "/api/trigger-profiles",
            json={"name": "我的避雷档案", "description": "测试", "from_template": False},
        )
        created = create_response.json()
        load_response = self.client.get(f"/api/trigger-profiles/{created['id']}")

        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(list_response.json()["items"][0]["id"], "profile_builtin_default")
        self.assertEqual(create_response.status_code, 200)
        self.assertEqual(created["name"], "我的避雷档案")
        self.assertEqual(created["rule_groups"], [])
        self.assertEqual(load_response.json()["id"], created["id"])

    def test_trigger_profile_rule_group_and_rule_endpoints(self):
        profile = self.client.post(
            "/api/trigger-profiles",
            json={"name": "空档案", "from_template": False},
        ).json()
        profile_id = profile["id"]
        group_response = self.client.post(
            f"/api/trigger-profiles/{profile_id}/groups",
            json={"name": "感情类"},
        )
        group_id = group_response.json()["rule_groups"][0]["id"]
        rule_response = self.client.post(
            f"/api/trigger-profiles/{profile_id}/rules",
            json={
                "name": "感情线虐恋",
                "group_id": group_id,
                "severity_threshold": 2,
            },
        )
        rule_id = rule_response.json()["rules"][0]["id"]
        guarded_delete = self.client.delete(
            f"/api/trigger-profiles/{profile_id}/groups/{group_id}"
        )
        updated_rule = self.client.patch(
            f"/api/trigger-profiles/{profile_id}/rules/{rule_id}",
            json={"enabled": False},
        )
        delete_rule = self.client.delete(
            f"/api/trigger-profiles/{profile_id}/rules/{rule_id}"
        )
        delete_group = self.client.delete(
            f"/api/trigger-profiles/{profile_id}/groups/{group_id}"
        )

        self.assertEqual(group_response.status_code, 200)
        self.assertEqual(rule_response.status_code, 200)
        self.assertEqual(guarded_delete.status_code, 400)
        self.assertFalse(updated_rule.json()["rules"][0]["enabled"])
        self.assertEqual(delete_rule.json()["rules"], [])
        self.assertEqual(delete_group.json()["rule_groups"], [])

    def test_trigger_scan_precheck_and_start_endpoint(self):
        self.client.post(
            "/api/config/api",
            json=[{"id": "api1", "url": "http://example.test/v1", "key": "secret", "model": "model"}],
        )
        upload = self.client.post(
            "/api/uploads",
            json={
                "project_name": "雷点项目",
                "workflow_type": "novel_summary",
                "files": [{"name": "第001章.txt", "content": "第一章\n正文"}],
            },
        ).json()
        output_dir = Path(upload["workflow_output_directory"])
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "第001章.txt").write_text("第一章\n正文", encoding="utf-8")
        payload = {
            "project_slug": upload["project"]["project_slug"],
            "profile_id": "profile_builtin_default",
            "scan_config": {
                "scan_mode": "precise",
                "scan_api_ids": ["api1"],
                "verification_enabled": False,
                "precise_chapter_batch_size": 5,
                "verification_chapter_batch_size": 5,
            },
        }

        precheck = self.client.post("/api/trigger-scan/precheck", json=payload)
        with mock.patch("webui_backend.api_app.create_trigger_scan_runner") as create_runner:
            async def runner(record, pause_signal, emit):
                return "report:fake"

            create_runner.return_value = runner
            start = self.client.post("/api/tasks/trigger-scan", json=payload)

        self.assertEqual(precheck.status_code, 200)
        self.assertTrue(precheck.json()["ready"])
        self.assertEqual(start.status_code, 200)
        self.assertEqual(start.json()["task_type"], "trigger_scan")
        request = create_runner.call_args.args[0]
        self.assertEqual(request.scan_config.precise_chapter_batch_size, 5)
        self.assertNotIn("coarse_summary_batch_size", request.scan_config.to_dict())

    def test_trigger_scan_uses_project_custom_output_directory(self):
        self.client.post(
            "/api/config/api",
            json=[{"id": "api1", "url": "http://example.test/v1", "key": "secret", "model": "model"}],
        )
        upload = self.client.post(
            "/api/uploads",
            json={
                "project_name": "自定义扫描输出项目",
                "workflow_type": "novel_summary",
                "files": [{"name": "第001章.txt", "content": "第一章\n正文"}],
            },
        ).json()
        project_slug = upload["project"]["project_slug"]
        custom_dir = Path(self.tmpdir.name) / "custom-trigger-output"
        custom_dir.mkdir()
        (custom_dir / "第001章.txt").write_text("第一章\n正文", encoding="utf-8")
        self.client.patch(
            f"/api/projects/{project_slug}",
            json={
                "project_name": upload["project"]["project_name"],
                "custom_output_directory_path": str(custom_dir),
            },
        )
        payload = {
            "project_slug": project_slug,
            "profile_id": "profile_builtin_default",
            "scan_config": {
                "scan_mode": "precise",
                "scan_api_ids": ["api1"],
                "verification_enabled": False,
                "precise_chapter_batch_size": 5,
                "verification_chapter_batch_size": 5,
            },
        }

        with mock.patch("webui_backend.api_app.create_trigger_scan_runner") as create_runner:
            async def runner(record, pause_signal, emit):
                return "report:fake"

            create_runner.return_value = runner
            response = self.client.post("/api/tasks/trigger-scan", json=payload)

        self.assertEqual(response.status_code, 200)
        request = create_runner.call_args.args[0]
        self.assertSamePath(request.source_folder_path, custom_dir)
        self.assertSamePath(request.project_output_directory_path, custom_dir)

    def test_trigger_scan_precheck_rejects_hybrid_mode_without_summary_decisions(self):
        self.client.post(
            "/api/config/api",
            json=[{"id": "api1", "url": "http://example.test/v1", "key": "secret", "model": "model"}],
        )
        upload = self.client.post(
            "/api/uploads",
            json={
                "project_name": "旧混合扫描项目",
                "workflow_type": "novel_summary",
                "files": [{"name": "第001章.txt", "content": "第一章\n正文"}],
            },
        ).json()
        output_dir = Path(upload["workflow_output_directory"])
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "第001章.txt").write_text("第一章\n正文", encoding="utf-8")

        response = self.client.post(
            "/api/trigger-scan/precheck",
            json={
                "project_slug": upload["project"]["project_slug"],
                "profile_id": "profile_builtin_default",
                "scan_config": {
                    "scan_mode": "hybrid",
                    "scan_api_ids": ["api1"],
                    "precise_chapter_batch_size": 5,
                    "verification_chapter_batch_size": 5,
                },
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["ready"])
        self.assertIn("hybrid scan mode has been removed", "; ".join(response.json()["errors"]))
        self.assertNotIn("generate_small_summaries", response.json()["decisions"])
        self.assertNotIn("switch_to_precise", response.json()["decisions"])
        self.assertEqual(response.json()["selected_chapter_count"], 1)

    def test_trigger_scan_report_context_skip_list_and_exports(self):
        upload = self.client.post(
            "/api/uploads",
            json={
                "project_name": "报告项目",
                "workflow_type": "novel_summary",
                "files": [{"name": "第001章.txt", "content": "第一章\n第一段\n第二段"}],
            },
        ).json()
        project_slug = upload["project"]["project_slug"]
        output_dir = Path(upload["workflow_output_directory"])
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "第001章.txt").write_text("第一章\n第一段\n第二段", encoding="utf-8")
        finding = ScanFinding.from_dict(
            {
                "finding_id": "finding1",
                "rule_id": "rule_character_death",
                "rule_name": "主要角色死亡",
                "chapter_file": "第001章.txt",
                "chapter_title": "第一章",
                "paragraph_ids": ["P002"],
                "severity": 3,
                "confidence": 0.9,
                "spoiler_levels": {
                    "low": {"description": "低剧透"},
                    "standard": {"description": "标准"},
                    "detailed": {"description": "详细", "evidence_quote": "第一段"},
                },
            }
        )
        report = ScanReport(
            report_id="report1",
            project_slug=project_slug,
            profile_id="profile_builtin_default",
            profile_name="默认避雷档案",
            scan_config=TriggerScanConfig(scan_mode="precise", scan_api_ids=["api1"]),
            status="completed",
            summary=ScanReportSummary(total_findings=1, pending_review=1),
            findings=[finding],
        )
        TriggerScanReportStore(output_dir).save_report(report)

        history = self.client.get(f"/api/trigger-scan/projects/{project_slug}/reports")
        loaded = self.client.get(f"/api/trigger-scan/projects/{project_slug}/reports/report1")
        context = self.client.get(
            f"/api/trigger-scan/projects/{project_slug}/reports/report1/findings/finding1/context"
        )
        updated = self.client.patch(
            f"/api/trigger-scan/projects/{project_slug}/reports/report1/findings/finding1",
            json={"review_status": "confirmed", "user_note": "确认"},
        )
        report_export = self.client.post(
            f"/api/trigger-scan/projects/{project_slug}/reports/report1/export",
            json={"format": "md"},
        )
        self.assertEqual(history.status_code, 200)
        self.assertEqual(history.json()["items"][0]["report_id"], "report1")
        self.assertEqual(loaded.json()["findings"][0]["finding_id"], "finding1")
        self.assertTrue(context.json()["ok"])
        self.assertTrue(context.json()["paragraphs"][1]["matched"])
        self.assertEqual(updated.json()["review_status"], "confirmed")
        self.assertTrue(Path(report_export.json()["path"]).exists())

    def test_imported_project_exposes_trigger_scan_history_and_artifacts(self):
        legacy_dir = Path(self.tmpdir.name) / "imported-trigger-project"
        legacy_dir.mkdir()
        (legacy_dir / "第001章.txt").write_text("第一章\n正文", encoding="utf-8")
        (legacy_dir / ".summarizer_cache" / "paragraph_index").mkdir(parents=True)
        (legacy_dir / ".summarizer_cache" / "paragraph_index" / "chapter.json").write_text("{}", encoding="utf-8")
        report = ScanReport(
            report_id="report_imported",
            project_slug="legacy-project",
            profile_id="profile_builtin_default",
            profile_name="默认避雷档案",
            scan_config=TriggerScanConfig(scan_mode="precise", scan_api_ids=["api1"]),
            status="completed",
            summary=ScanReportSummary(total_findings=0),
        )
        TriggerScanReportStore(legacy_dir).save_report(report)

        imported = self.client.post(
            "/api/projects/import",
            json={"path": str(legacy_dir), "workflow_type": "novel_summary"},
        )
        project = imported.json()
        history = self.client.get(
            f"/api/trigger-scan/projects/{project['project_slug']}/reports"
        )
        stages = {stage["label"]: stage for stage in project["progress"]["stages"]}

        self.assertEqual(imported.status_code, 200)
        self.assertEqual(history.status_code, 200)
        self.assertEqual(history.json()["items"][0]["report_id"], "report_imported")
        self.assertEqual(stages["雷点报告"]["completed"], 1)
        self.assertEqual(stages["段落缓存"]["completed"], 1)

    def test_trigger_scan_start_blocks_while_summary_task_is_active(self):
        with mock.patch.object(
            self.client.app.state.runtime,
            "has_active_task",
            return_value=True,
        ):
            blocked = self.client.post("/api/tasks/trigger-scan", json={})

        self.assertEqual(blocked.status_code, 409)
        self.assertIn("正在运行", blocked.json()["detail"])

    def test_browse_directory_returns_selected_path(self):
        with mock.patch(
            "webui_backend.api_app.pick_directory",
            return_value="C:/Novels",
        ) as picker:
            response = self.client.post("/api/browse/directory", json={"title": "选择小说目录"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["path"], "C:/Novels")
        picker.assert_called_once_with("选择小说目录")

    def test_upload_text_files_creates_project_workspace(self):
        response = self.client.post(
            "/api/uploads",
            json={
                "project_name": "测试项目",
                "workflow_type": "novel_summary",
                "files": [{"name": "第1章.txt", "content": "正文"}],
            },
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        project = data["project"]
        self.assertEqual(project["project_name"], "测试项目")
        self.assertEqual(project["upload_count"], 1)
        self.assertTrue(os.path.exists(data["items"][0]["path"]))
        self.assertIn("exports", data["workflow_output_directory"])

    def test_upload_text_files_rejects_unsupported_type(self):
        response = self.client.post(
            "/api/uploads",
            json={
                "project_name": "测试项目",
                "workflow_type": "novel_summary",
                "files": [{"name": "cover.png", "content": "not text"}],
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("不是受支持", response.json()["detail"])

    def test_upload_text_files_preserves_multiple_file_order(self):
        response = self.client.post(
            "/api/uploads",
            json={
                "project_name": "批量项目",
                "workflow_type": "article_summary",
                "files": [
                    {"name": "2.txt", "content": "two"},
                    {"name": "1.txt", "content": "one"},
                ],
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [item["original_name"] for item in response.json()["items"]],
            ["2.txt", "1.txt"],
        )

    def test_upload_text_files_rejects_oversized_file(self):
        from webui_backend.project_workspace import MAX_UPLOAD_FILE_BYTES

        response = self.client.post(
            "/api/uploads",
            json={
                "project_name": "大文件项目",
                "workflow_type": "novel_summary",
                "files": [{"name": "big.txt", "content": "x" * (MAX_UPLOAD_FILE_BYTES + 1)}],
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("大小限制", response.json()["detail"])

    def test_project_history_sorted_and_filterable(self):
        self.client.post(
            "/api/uploads",
            json={
                "project_name": "文章项目",
                "workflow_type": "article_summary",
                "files": [{"name": "a.txt", "content": "a"}],
            },
        )
        self.client.post(
            "/api/uploads",
            json={
                "project_name": "小说项目",
                "workflow_type": "novel_summary",
                "files": [{"name": "n.txt", "content": "n"}],
            },
        )

        response = self.client.get("/api/projects", params={"workflow_type": "novel_summary"})

        self.assertEqual(response.status_code, 200)
        items = response.json()["items"]
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["project_name"], "小说项目")

    def test_delete_project_removes_it_from_history_and_preserves_custom_output(self):
        upload_response = self.client.post(
            "/api/uploads",
            json={
                "project_name": "删除项目",
                "workflow_type": "chapter_split",
                "files": [{"name": "source.txt", "content": "text"}],
            },
        ).json()
        project = upload_response["project"]
        managed_project_dir = (
            Path(self.tmpdir.name)
            / "runtime"
            / "exports"
            / project["project_slug"]
        )
        managed_project_dir.mkdir(parents=True, exist_ok=True)
        (managed_project_dir / OUTPUT_OWNERSHIP_FILENAME).write_text(
            json.dumps(
                {
                    "owner": OUTPUT_OWNERSHIP_OWNER,
                    "project_slug": project["project_slug"],
                    "purpose": OUTPUT_OWNERSHIP_PURPOSE,
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        custom_output = Path(self.tmpdir.name) / "custom-output"
        custom_output.mkdir()
        with mock.patch("webui_backend.api_app.create_splitter_runner") as create_runner:
            async def runner(record, pause_signal, emit):
                return "ok"

            create_runner.return_value = runner
            self.client.post(
                "/api/tasks/splitter",
                json={
                    "project_slug": project["project_slug"],
                    "uploaded_file_ids": [upload_response["items"][0]["id"]],
                    "custom_output_directory_path": str(custom_output),
                    "mode": "default",
                },
            )

        response = self.client.delete(f"/api/projects/{project['project_slug']}")
        history = self.client.get("/api/projects").json()["items"]

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["deleted_project_directory"])
        self.assertEqual(payload["deleted_output_directories"], [str(managed_project_dir)])
        self.assertEqual(payload["preserved_output_directories"][0]["path"], str(custom_output))
        self.assertEqual(
            payload["preserved_output_directories"][0]["reason"],
            "custom_output_directory",
        )
        self.assertFalse(
            os.path.exists(
                os.path.join(
                    self.tmpdir.name,
                    "runtime",
                    "workspace",
                    "projects",
                    project["project_slug"],
                )
            )
        )
        self.assertFalse(managed_project_dir.exists())
        self.assertTrue(custom_output.exists())
        self.assertNotIn(project["project_slug"], [item["project_slug"] for item in history])

    def test_delete_missing_project_returns_clear_error(self):
        response = self.client.delete("/api/projects/missing")

        self.assertEqual(response.status_code, 404)
        self.assertIn("项目不存在", response.json()["detail"])

    def test_project_detail_returns_missing_file_warning(self):
        upload_response = self.client.post(
            "/api/uploads",
            json={
                "project_name": "缺失项目",
                "workflow_type": "custom_summary",
                "files": [{"name": "a.txt", "content": "a"}],
            },
        ).json()
        item = upload_response["items"][0]
        os.remove(item["path"])

        response = self.client.get(f"/api/projects/{item['project_slug']}")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["uploads"][0]["missing"])

    def test_update_project_name_persists_display_name(self):
        upload_response = self.client.post(
            "/api/uploads",
            json={
                "project_name": "旧名称",
                "workflow_type": "novel_summary",
                "files": [{"name": "a.txt", "content": "a"}],
            },
        ).json()

        response = self.client.patch(
            f"/api/projects/{upload_response['project']['project_slug']}",
            json={"project_name": "新名称"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["project_name"], "新名称")
        self.assertEqual(response.json()["project_slug"], upload_response["project"]["project_slug"])

    def test_clear_project_uploads_removes_files_from_project(self):
        upload_response = self.client.post(
            "/api/uploads",
            json={
                "project_name": "清空项目",
                "workflow_type": "novel_summary",
                "files": [{"name": "a.txt", "content": "a"}],
            },
        ).json()
        uploaded_path = upload_response["items"][0]["path"]

        response = self.client.delete(
            f"/api/projects/{upload_response['project']['project_slug']}/uploads"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["upload_count"], 0)
        self.assertFalse(os.path.exists(uploaded_path))

    def test_import_project_reads_legacy_progress(self):
        legacy_dir = Path(self.tmpdir.name) / "legacy-novel"
        cache_dir = legacy_dir / ".summarizer_cache"
        legacy_dir.mkdir()
        cache_dir.mkdir()
        (legacy_dir / "1.txt").write_text("one", encoding="utf-8")
        (legacy_dir / "2.txt").write_text("two", encoding="utf-8")
        (cache_dir / "task_id.txt").write_text("task", encoding="utf-8")
        (cache_dir / "state_task.json").write_text(
            json.dumps({"small_summary": {"1.txt": True}}, ensure_ascii=False),
            encoding="utf-8",
        )
        (cache_dir / USER_FACING_SMALL_PLOT_SUBDIR).mkdir(parents=True)
        (cache_dir / USER_FACING_SMALL_CHAR_SUBDIR).mkdir(parents=True)
        (cache_dir / USER_FACING_SMALL_PLOT_SUBDIR / "1.txt").write_text("plot", encoding="utf-8")
        (cache_dir / USER_FACING_SMALL_CHAR_SUBDIR / "1.txt").write_text("char", encoding="utf-8")

        response = self.client.post(
            "/api/projects/import",
            json={"path": str(legacy_dir), "workflow_type": "novel_summary"},
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["upload_count"], 2)
        self.assertEqual(data["progress"]["summary"], "小总结 1/2")
        self.assertEqual(data["custom_output_directory"], str(legacy_dir))
        self.assertEqual(data["latest_task_status"], "partial")
        self.assertTrue(os.path.exists(data["uploads"][0]["path"]))

    def test_grouped_chapter_names_no_longer_block_summary_or_expose_migration_api(self):
        self.client.post(
            "/api/config/api",
            json=[{"id": "api1", "url": "http://example.test/v1", "key": "secret", "model": "model"}],
        )
        legacy_dir = Path(self.tmpdir.name) / "legacy-granularity"
        legacy_dir.mkdir()
        (legacy_dir / "第001章-第002章.txt").write_text(
            "第一章 开始\n正文一\n第二章 继续\n正文二",
            encoding="utf-8",
        )
        imported = self.client.post(
            "/api/projects/import",
            json={"path": str(legacy_dir), "workflow_type": "novel_summary"},
        ).json()
        project_slug = imported["project_slug"]

        self.assertFalse(imported["requires_granularity_migration"])
        self.assertEqual(imported["legacy_grouped_file_count"], 0)
        self.assertEqual(imported["summary_batch_size"], 10)

        with mock.patch("webui_backend.api_app.create_novel_summary_runner") as create_runner:
            async def runner(record, pause_signal, emit):
                return "ok"

            create_runner.return_value = runner
            started = self.client.post(
                "/api/tasks/novel",
                json={
                    "project_slug": project_slug,
                    "uploaded_file_ids": [item["id"] for item in imported["uploads"]],
                    "active_api_ids": ["api1"],
                },
            )
        check = self.client.get(f"/api/projects/{project_slug}/chapter-granularity-migration")
        migrate = self.client.post(
            f"/api/projects/{project_slug}/chapter-granularity-migration",
            json={},
        )

        self.assertEqual(started.status_code, 200)
        self.assertEqual(check.status_code, 404)
        self.assertEqual(migrate.status_code, 404)

    def test_save_project_persists_name_uploads_and_output_directory(self):
        upload = self.client.post(
            "/api/uploads",
            json={
                "project_name": "草稿项目",
                "workflow_type": "novel_summary",
                "files": [
                    {"name": "a.txt", "content": "a"},
                    {"name": "b.txt", "content": "b"},
                ],
            },
        ).json()
        removed_path = upload["items"][1]["path"]
        custom_dir = os.path.join(self.tmpdir.name, "custom-output")

        response = self.client.patch(
            f"/api/projects/{upload['project']['project_slug']}",
            json={
                "project_name": "保存后的项目",
                "uploaded_file_ids": [upload["items"][0]["id"]],
                "custom_output_directory_path": custom_dir,
            },
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["project_name"], "保存后的项目")
        self.assertEqual(data["upload_count"], 1)
        self.assertSamePath(data["custom_output_directory"], custom_dir)
        self.assertFalse(os.path.exists(removed_path))

    def test_output_migration_check_and_save_with_migration(self):
        upload = self.client.post(
            "/api/uploads",
            json={
                "project_name": "迁移项目",
                "workflow_type": "chapter_split",
                "files": [{"name": "a.txt", "content": "a"}],
            },
        ).json()
        old_output = Path(upload["project"]["default_output_directory"])
        old_output.mkdir(parents=True, exist_ok=True)
        (old_output / "result.txt").write_text("ok", encoding="utf-8")
        new_output = Path(self.tmpdir.name) / "new-output"

        check_response = self.client.post(
            f"/api/projects/{upload['project']['project_slug']}/output-migration-check",
            json={"custom_output_directory_path": str(new_output)},
        )
        save_response = self.client.patch(
            f"/api/projects/{upload['project']['project_slug']}",
            json={
                "project_name": upload["project"]["project_name"],
                "uploaded_file_ids": [upload["items"][0]["id"]],
                "custom_output_directory_path": str(new_output),
                "migrate_existing_output": True,
            },
        )

        self.assertEqual(check_response.status_code, 200)
        self.assertTrue(check_response.json()["requires_migration"])
        self.assertEqual(check_response.json()["file_count"], 1)
        self.assertEqual(save_response.status_code, 200)
        self.assertTrue((new_output / "result.txt").exists())
        self.assertFalse((old_output / "result.txt").exists())

    def test_output_directory_change_can_decline_migration(self):
        upload = self.client.post(
            "/api/uploads",
            json={
                "project_name": "不迁移项目",
                "workflow_type": "chapter_split",
                "files": [{"name": "a.txt", "content": "a"}],
            },
        ).json()
        old_output = Path(upload["project"]["default_output_directory"])
        old_output.mkdir(parents=True, exist_ok=True)
        (old_output / "result.txt").write_text("ok", encoding="utf-8")
        new_output = Path(self.tmpdir.name) / "new-output-no-migrate"

        response = self.client.patch(
            f"/api/projects/{upload['project']['project_slug']}",
            json={
                "project_name": upload["project"]["project_name"],
                "uploaded_file_ids": [upload["items"][0]["id"]],
                "custom_output_directory_path": str(new_output),
                "migrate_existing_output": False,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue((old_output / "result.txt").exists())
        self.assertSamePath(response.json()["custom_output_directory"], str(new_output))

    def test_splitter_task_accepts_uploaded_reference_and_managed_output(self):
        upload = self.client.post(
            "/api/uploads",
            json={
                "project_name": "拆章项目",
                "workflow_type": "chapter_split",
                "files": [{"name": "source.txt", "content": "第一章 开始"}],
            },
        ).json()

        with mock.patch("webui_backend.api_app.create_splitter_runner") as create_runner:
            async def runner(record, pause_signal, emit):
                return "ok"

            create_runner.return_value = runner
            response = self.client.post(
                "/api/tasks/splitter",
                json={
                    "project_slug": upload["project"]["project_slug"],
                    "uploaded_file_ids": [upload["items"][0]["id"]],
                    "mode": "default",
                    "handle_volumes": True,
                },
            )

        self.assertEqual(response.status_code, 200)
        request = create_runner.call_args.args[0]
        self.assertTrue(os.path.exists(request.source_txt_file_path))
        self.assertIn(os.path.join("exports", upload["project"]["project_slug"], "chapter-split"), request.output_directory_path)

    def test_task_uses_user_default_output_directory_when_no_project_custom_output(self):
        user_export_dir = os.path.join(self.tmpdir.name, "user-exports")
        self.client.post(
            "/api/settings",
            json={"default_export_directory": user_export_dir},
        )
        upload = self.client.post(
            "/api/uploads",
            json={
                "project_name": "用户默认导出项目",
                "workflow_type": "chapter_split",
                "files": [{"name": "source.txt", "content": "text"}],
            },
        ).json()

        with mock.patch("webui_backend.api_app.create_splitter_runner") as create_runner:
            async def runner(record, pause_signal, emit):
                return "ok"

            create_runner.return_value = runner
            response = self.client.post(
                "/api/tasks/splitter",
                json={
                    "project_slug": upload["project"]["project_slug"],
                    "uploaded_file_ids": [upload["items"][0]["id"]],
                    "mode": "default",
                },
            )

        self.assertEqual(response.status_code, 200)
        request = create_runner.call_args.args[0]
        self.assertIn(
            os.path.join("user-exports", upload["project"]["project_slug"], "chapter-split"),
            request.output_directory_path,
        )

    def test_article_task_accepts_uploaded_references_and_preserves_order(self):
        self.client.post(
            "/api/config/api",
            json=[{"id": "api1", "url": "http://example.test/v1", "key": "secret", "model": "model"}],
        )
        upload = self.client.post(
            "/api/uploads",
            json={
                "project_name": "文章项目",
                "workflow_type": "article_summary",
                "files": [
                    {"name": "2.txt", "content": "two"},
                    {"name": "1.txt", "content": "one"},
                ],
            },
        ).json()

        with mock.patch("webui_backend.api_app.create_article_summary_runner") as create_runner:
            async def runner(record, pause_signal, emit):
                return "ok"

            create_runner.return_value = runner
            response = self.client.post(
                "/api/tasks/article",
                json={
                    "project_slug": upload["project"]["project_slug"],
                    "uploaded_file_ids": [item["id"] for item in upload["items"]],
                },
            )

        self.assertEqual(response.status_code, 200)
        request = create_runner.call_args.args[0]
        self.assertEqual(request.selected_files, ["2.txt", "1.txt"])
        self.assertEqual(request.output_subfolder, "")
        self.assertIn(os.path.join("exports", upload["project"]["project_slug"], "article-summary"), request.source_folder_path)

    def test_task_rejects_unknown_uploaded_reference(self):
        upload = self.client.post(
            "/api/uploads",
            json={
                "project_name": "错误项目",
                "workflow_type": "chapter_split",
                "files": [{"name": "source.txt", "content": "text"}],
            },
        ).json()

        response = self.client.post(
            "/api/tasks/splitter",
            json={
                "project_slug": upload["project"]["project_slug"],
                "uploaded_file_ids": ["missing"],
                "mode": "default",
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("未知上传文件引用", response.json()["detail"])

    def test_task_uses_custom_output_directory_override(self):
        upload = self.client.post(
            "/api/uploads",
            json={
                "project_name": "自定义输出项目",
                "workflow_type": "chapter_split",
                "files": [{"name": "source.txt", "content": "text"}],
            },
        ).json()
        custom_dir = os.path.join(self.tmpdir.name, "custom-output")

        with mock.patch("webui_backend.api_app.create_splitter_runner") as create_runner:
            async def runner(record, pause_signal, emit):
                return "ok"

            create_runner.return_value = runner
            response = self.client.post(
                "/api/tasks/splitter",
                json={
                    "project_slug": upload["project"]["project_slug"],
                    "uploaded_file_ids": [upload["items"][0]["id"]],
                    "custom_output_directory_path": custom_dir,
                    "mode": "default",
                },
            )

        self.assertEqual(response.status_code, 200)
        request = create_runner.call_args.args[0]
        self.assertSamePath(request.output_directory_path, custom_dir)

    def test_task_falls_back_to_default_output_when_custom_path_is_file(self):
        upload = self.client.post(
            "/api/uploads",
            json={
                "project_name": "坏输出目录项目",
                "workflow_type": "chapter_split",
                "files": [{"name": "source.txt", "content": "text"}],
            },
        ).json()
        invalid_output = os.path.join(self.tmpdir.name, "not-a-directory.txt")
        Path(invalid_output).write_text("file", encoding="utf-8")

        with mock.patch("webui_backend.api_app.create_splitter_runner") as create_runner:
            async def runner(record, pause_signal, emit):
                return "ok"

            create_runner.return_value = runner
            response = self.client.post(
                "/api/tasks/splitter",
                json={
                    "project_slug": upload["project"]["project_slug"],
                    "uploaded_file_ids": [upload["items"][0]["id"]],
                    "custom_output_directory_path": invalid_output,
                    "mode": "default",
                },
            )

        self.assertEqual(response.status_code, 200)
        request = create_runner.call_args.args[0]
        self.assertIn(
            os.path.join("exports", upload["project"]["project_slug"], "chapter-split"),
            request.output_directory_path,
        )

    def test_restarting_same_project_keeps_managed_source_path_stable(self):
        self.client.post(
            "/api/config/api",
            json=[{"id": "api1", "url": "http://example.test/v1", "key": "secret", "model": "model"}],
        )
        upload = self.client.post(
            "/api/uploads",
            json={
                "project_name": "续跑项目",
                "workflow_type": "novel_summary",
                "files": [{"name": "1.txt", "content": "one"}],
            },
        ).json()

        with mock.patch("webui_backend.api_app.create_novel_summary_runner") as create_runner:
            async def runner(record, pause_signal, emit):
                return "ok"

            create_runner.return_value = runner
            payload = {
                "project_slug": upload["project"]["project_slug"],
                "uploaded_file_ids": [upload["items"][0]["id"]],
                "active_api_ids": ["api1"],
                "big_summary_batch_size": 1,
                "super_summary_threshold": 1,
            }
            first = self.client.post("/api/tasks/novel", json=payload)
            first_path = create_runner.call_args.args[0].source_folder_path
            second = self.client.post("/api/tasks/novel", json=payload)
            second_path = create_runner.call_args.args[0].source_folder_path

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertSamePath(first_path, second_path)

    def test_novel_project_persists_summary_output_format(self):
        self.client.post(
            "/api/config/api",
            json=[{"id": "api1", "url": "http://example.test/v1", "key": "secret", "model": "model"}],
        )
        upload = self.client.post(
            "/api/uploads",
            json={
                "project_name": "格式项目",
                "workflow_type": "novel_summary",
                "files": [{"name": "1.txt", "content": "one"}],
            },
        ).json()
        project_slug = upload["project"]["project_slug"]

        self.assertEqual(upload["project"]["summary_output_format"], "md")
        save_response = self.client.patch(
            f"/api/projects/{project_slug}",
            json={
                "project_name": "格式项目",
                "summary_output_format": "txt",
            },
        )

        self.assertEqual(save_response.status_code, 200)
        self.assertEqual(save_response.json()["summary_output_format"], "txt")

        with mock.patch("webui_backend.api_app.create_novel_summary_runner") as create_runner:
            async def runner(record, pause_signal, emit):
                return "ok"

            create_runner.return_value = runner
            response = self.client.post(
                "/api/tasks/novel",
                json={
                    "project_slug": project_slug,
                    "uploaded_file_ids": [upload["items"][0]["id"]],
                    "active_api_ids": ["api1"],
                },
            )

        self.assertEqual(response.status_code, 200)
        request = create_runner.call_args.args[0]
        self.assertEqual(request.summary_output_format, "txt")

    def test_small_summary_preparation_endpoint_sets_stop_flag(self):
        self.client.post(
            "/api/config/api",
            json=[{"id": "api1", "url": "http://example.test/v1", "key": "secret", "model": "model"}],
        )
        upload = self.client.post(
            "/api/uploads",
            json={
                "project_name": "小总结准备项目",
                "workflow_type": "novel_summary",
                "files": [{"name": "第001章.txt", "content": "one"}],
            },
        ).json()

        with mock.patch("webui_backend.api_app.create_novel_summary_runner") as create_runner:
            async def runner(record, pause_signal, emit):
                return "ok"

            create_runner.return_value = runner
            response = self.client.post(
                "/api/tasks/novel/small-summary",
                json={
                    "project_slug": upload["project"]["project_slug"],
                    "uploaded_file_ids": [upload["items"][0]["id"]],
                    "active_api_ids": ["api1"],
                    "summary_batch_size": 1,
                    "summary_output_format": "txt",
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["task_type"], "small_summary_preparation")
        request = create_runner.call_args.args[0]
        self.assertTrue(request.stop_after_small_summary)
        self.assertEqual(request.summary_batch_size, 1)
        self.assertEqual(request.summary_output_format, "txt")

    def test_open_managed_directory_creates_and_invokes_os_open(self):
        upload = self.client.post(
            "/api/uploads",
            json={
                "project_name": "打开目录项目",
                "workflow_type": "chapter_split",
                "files": [{"name": "source.txt", "content": "text"}],
            },
        ).json()

        with mock.patch("webui_backend.project_workspace._open_directory_with_os") as open_dir:
            response = self.client.post(
                "/api/projects/open-directory",
                json={
                    "project_slug": upload["project"]["project_slug"],
                    "workflow_type": "chapter_split",
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(os.path.isdir(response.json()["path"]))
        open_dir.assert_called_once()

    def test_open_project_directory_falls_back_when_custom_path_is_invalid(self):
        upload = self.client.post(
            "/api/uploads",
            json={
                "project_name": "打开回退项目",
                "workflow_type": "chapter_split",
                "files": [{"name": "source.txt", "content": "text"}],
            },
        ).json()
        invalid_output = os.path.join(self.tmpdir.name, "bad-output.txt")
        Path(invalid_output).write_text("file", encoding="utf-8")

        with mock.patch("webui_backend.project_workspace._open_directory_with_os") as open_dir:
            response = self.client.post(
                "/api/projects/open-directory",
                json={
                    "project_slug": upload["project"]["project_slug"],
                    "workflow_type": "chapter_split",
                    "custom_output_directory_path": invalid_output,
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertIn(
            os.path.join("exports", upload["project"]["project_slug"], "chapter-split"),
            response.json()["path"],
        )
        open_dir.assert_called_once()

    def test_open_custom_directory_rejects_missing_path(self):
        missing = os.path.join(self.tmpdir.name, "missing-custom-output")

        response = self.client.post(
            "/api/projects/open-directory",
            json={"path": missing},
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("目录不存在", response.json()["detail"])

    def test_resolve_path_validates_existing_directory(self):
        source_dir = os.path.join(self.tmpdir.name, "articles")
        os.makedirs(source_dir)

        response = self.client.post(
            "/api/utils/resolve-path",
            json={"path": source_dir},
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["resolved"])
        self.assertTrue(data["is_directory"])
        self.assertSamePath(data["path"], source_dir)

    def test_resolve_path_accepts_directory_file_uri(self):
        source_dir = os.path.join(self.tmpdir.name, "uris")
        os.makedirs(source_dir)

        response = self.client.post(
            "/api/utils/resolve-path",
            json={"path": Path(source_dir).resolve().as_uri()},
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["resolved"])
        self.assertSamePath(data["path"], source_dir)

    def test_resolve_path_rejects_existing_file_as_directory(self):
        source_dir = os.path.join(self.tmpdir.name, "novels")
        os.makedirs(source_dir)
        source_file = os.path.join(source_dir, "chapter.txt")
        Path(source_file).write_text("chapter", encoding="utf-8")

        response = self.client.post(
            "/api/utils/resolve-path",
            json={"path": source_file},
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(data["resolved"])
        self.assertFalse(data["is_directory"])
        self.assertSamePath(data["path"], source_file)

    def test_resolve_path_marks_missing_path_unresolved(self):
        missing_path = os.path.join(self.tmpdir.name, "missing", "chapter.txt")

        response = self.client.post(
            "/api/utils/resolve-path",
            json={"path": missing_path},
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(data["resolved"])
        self.assertSamePath(data["path"], missing_path)

    def test_resolve_path_keeps_missing_relative_path_unexpanded(self):
        response = self.client.post(
            "/api/utils/resolve-path",
            json={"path": "chapter.txt"},
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(data["resolved"])
        self.assertEqual(data["path"], "chapter.txt")


if __name__ == "__main__":
    unittest.main()
