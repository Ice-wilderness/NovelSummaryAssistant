import importlib.util
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock


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
                    "chapters_per_file": 1,
                    "handle_volumes": True,
                },
            )

        self.assertEqual(response.status_code, 200)
        request = create_runner.call_args.args[0]
        self.assertTrue(os.path.exists(request.source_txt_file_path))
        self.assertIn(os.path.join("exports", upload["project"]["project_slug"], "chapter-split"), request.output_directory_path)

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
                "chapters_per_file": 1,
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
                    "chapters_per_file": 1,
                },
            )

        self.assertEqual(response.status_code, 200)
        request = create_runner.call_args.args[0]
        self.assertSamePath(request.output_directory_path, custom_dir)

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
