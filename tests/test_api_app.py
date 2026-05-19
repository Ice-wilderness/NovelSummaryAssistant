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

    def test_browse_file_returns_selected_path(self):
        filetypes = [["文本文件", "*.txt"]]
        with mock.patch(
            "webui_backend.api_app.pick_file",
            return_value="C:/Novels/source.txt",
        ) as picker:
            response = self.client.post(
                "/api/browse/file",
                json={"title": "选择源 TXT", "filetypes": filetypes},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["path"], "C:/Novels/source.txt")
        picker.assert_called_once_with("选择源 TXT", [("文本文件", "*.txt")])

    def test_resolve_path_prefers_parent_for_existing_file(self):
        source_dir = os.path.join(self.tmpdir.name, "novels")
        os.makedirs(source_dir)
        source_file = os.path.join(source_dir, "chapter.txt")
        Path(source_file).write_text("chapter", encoding="utf-8")

        response = self.client.post(
            "/api/utils/resolve-path",
            json={"path": source_file, "prefer_directory": True},
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["resolved"])
        self.assertSamePath(data["path"], source_dir)

    def test_resolve_path_keeps_existing_directory_when_preferred(self):
        source_dir = os.path.join(self.tmpdir.name, "articles")
        os.makedirs(source_dir)

        response = self.client.post(
            "/api/utils/resolve-path",
            json={"path": source_dir, "prefer_directory": True},
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["resolved"])
        self.assertSamePath(data["path"], source_dir)

    def test_resolve_path_accepts_file_uri(self):
        source_dir = os.path.join(self.tmpdir.name, "uris")
        os.makedirs(source_dir)
        source_file = os.path.join(source_dir, "chapter.txt")
        Path(source_file).write_text("chapter", encoding="utf-8")

        response = self.client.post(
            "/api/utils/resolve-path",
            json={"path": Path(source_file).resolve().as_uri(), "prefer_directory": True},
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["resolved"])
        self.assertSamePath(data["path"], source_dir)

    def test_resolve_path_marks_missing_path_unresolved(self):
        missing_path = os.path.join(self.tmpdir.name, "missing", "chapter.txt")

        response = self.client.post(
            "/api/utils/resolve-path",
            json={"path": missing_path, "prefer_directory": True},
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(data["resolved"])
        self.assertSamePath(data["path"], missing_path)


if __name__ == "__main__":
    unittest.main()
