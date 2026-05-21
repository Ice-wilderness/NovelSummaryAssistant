import importlib.util
import json
import os
import tempfile
import time
import unittest
from unittest import mock


FASTAPI_AVAILABLE = importlib.util.find_spec("fastapi") is not None


@unittest.skipUnless(FASTAPI_AVAILABLE, "FastAPI is not installed")
class WebuiEndToEndTests(unittest.TestCase):
    def setUp(self):
        from fastapi.testclient import TestClient
        from webui_backend.api_app import create_app

        self.tmpdir = tempfile.TemporaryDirectory()
        self.client_context = TestClient(
            create_app(
                api_config_path=os.path.join(self.tmpdir.name, "api_configs.json"),
                prompt_cache_dir=os.path.join(self.tmpdir.name, "prompt_cache"),
                frontend_dist_dir=os.path.join(self.tmpdir.name, "frontend_dist"),
            )
        )
        self.client = self.client_context.__enter__()

    def tearDown(self):
        self.client_context.__exit__(None, None, None)
        self.tmpdir.cleanup()

    def _wait_for_terminal(self, task_id, timeout=5):
        deadline = time.time() + timeout
        terminal = {"cancelled", "success", "failed"}
        last_payload = None
        while time.time() < deadline:
            response = self.client.get(f"/api/tasks/{task_id}")
            self.assertEqual(response.status_code, 200)
            last_payload = response.json()
            if last_payload["status"] in terminal:
                return last_payload
            time.sleep(0.05)
        self.fail(f"Task {task_id} did not finish. Last payload: {last_payload}")

    def test_splitter_task_splits_small_sample(self):
        source_path = os.path.join(self.tmpdir.name, "novel.txt")
        output_dir = os.path.join(self.tmpdir.name, "chapters")
        with open(source_path, "w", encoding="utf-8") as f:
            f.write("第一章 开始\n内容一\n第二章 继续\n内容二\n")

        response = self.client.post(
            "/api/tasks/splitter",
            json={
                "source_txt_file_path": source_path,
                "output_directory_path": output_dir,
                "mode": "default",
                "handle_volumes": False,
            },
        )
        self.assertEqual(response.status_code, 200)
        final = self._wait_for_terminal(response.json()["task_id"])

        self.assertEqual(final["status"], "success")
        self.assertIn("generated 2 files", final["result_summary"])
        generated_files = [name for name in os.listdir(output_dir) if name.endswith(".txt")]
        self.assertEqual(len(generated_files), 2)

    def test_article_task_e2e_uses_selected_files_env_key_and_keeps_key_private(self):
        source_dir = os.path.join(self.tmpdir.name, "articles")
        os.makedirs(source_dir, exist_ok=True)
        with open(os.path.join(source_dir, "1.txt"), "w", encoding="utf-8") as f:
            f.write("article one")
        with open(os.path.join(source_dir, "2.txt"), "w", encoding="utf-8") as f:
            f.write("article two")

        self.client.post(
            "/api/config/api",
            json=[
                {
                    "id": "api1",
                    "url": "http://example.test/v1",
                    "key": "local-secret",
                    "key_env_var": "NSA_E2E_KEY",
                    "model": "model",
                }
            ],
        )

        captured = []

        async def fake_summary(api_config, prompt_config, format_args, log_callback, **kwargs):
            captured.append((api_config, prompt_config, kwargs))
            if prompt_config.get("filename") == "prompt_article_section.txt":
                return f"section:{format_args['filename_for_context']}"
            return "final-summary"

        with mock.patch.dict("os.environ", {"NSA_E2E_KEY": "env-secret"}, clear=False):
            with mock.patch(
                "logic.article_summary_logic.get_llm_summary_with_config",
                side_effect=fake_summary,
            ):
                response = self.client.post(
                    "/api/tasks/article",
                    json={
                        "source_folder_path": source_dir,
                        "selected_files": ["1.txt"],
                        "output_subfolder": "article_output",
                        "word_counts": {"section": "11", "final": "22"},
                    },
                )
                self.assertEqual(response.status_code, 200)
                task_id = response.json()["task_id"]
                final = self._wait_for_terminal(task_id)

        self.assertEqual(final["status"], "success")
        self.assertTrue(captured)
        self.assertTrue(all(item[0]["key"] == "env-secret" for item in captured))
        self.assertEqual(captured[0][2]["section_word_count"], "11")
        self.assertEqual(captured[-1][2]["final_word_count"], "22")

        output_cache = os.path.join(source_dir, "article_output", ".summarizer_cache")
        final_path = os.path.join(output_cache, "2_文章最终总结", "最终总结_全文.txt")
        skipped_path = os.path.join(output_cache, "1_文章段落总结", "summary_2.txt")
        self.assertTrue(os.path.exists(final_path))
        self.assertFalse(os.path.exists(skipped_path))

        config_payload = self.client.get("/api/config/api").text
        task_payload = json.dumps(final, ensure_ascii=False)
        self.assertNotIn("local-secret", config_payload)
        self.assertNotIn("env-secret", config_payload)
        self.assertNotIn("local-secret", task_payload)
        self.assertNotIn("env-secret", task_payload)


if __name__ == "__main__":
    unittest.main()
