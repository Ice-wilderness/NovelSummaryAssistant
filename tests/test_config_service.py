import os
import tempfile
import unittest
from unittest import mock

from logic.prompts import DEFAULT_PROMPTS
from logic import utils as logic_utils
from webui_backend.config_models import (
    ApiConfig,
    ArticleSummaryRequest,
    ArticleWordCounts,
    CustomSummaryRequest,
    NovelSummaryRequest,
    NovelWordCounts,
    PromptMessage,
    SplitterRequest,
    UserSettings,
)
from webui_backend.config_service import (
    load_api_configs,
    load_prompt_templates,
    load_user_settings,
    load_workflow_prompt_config,
    prepare_user_settings_for_save,
    prepare_api_configs_for_save,
    public_api_configs,
    delete_prompt_module,
    reset_workflow_prompt_node,
    resolve_api_config,
    save_api_configs,
    save_prompt_template,
    save_user_settings,
    save_workflow_prompt_config,
    update_workflow_prompt_node,
    upsert_prompt_module,
)
from webui_backend.env_loader import load_dotenv_values, merged_environment
from webui_backend.prompt_workflows import create_default_workflow_prompt_config


class ConfigModelTests(unittest.TestCase):
    def test_api_config_masks_key_and_uses_env_override(self):
        config = ApiConfig.from_dict(
            {
                "id": "api1",
                "url": "http://example.test/v1",
                "key": "local-secret",
                "model": "model",
                "key_env_var": "NSA_API_KEY",
            }
        )

        public = config.to_public_dict()
        self.assertNotEqual(public["key"], "local-secret")
        self.assertTrue(public["has_key"])
        self.assertEqual(config.effective_key({"NSA_API_KEY": "env-secret"}), "env-secret")
        self.assertEqual(config.effective_key({}), "local-secret")

    def test_word_count_models_keep_defaults(self):
        novel_counts = NovelWordCounts.from_dict({"small_plot_word_count": "1"})
        article_counts = ArticleWordCounts.from_dict({"final": "2"})

        self.assertEqual(novel_counts.small_plot_word_count, "1")
        self.assertEqual(novel_counts.small_char_word_count, "10000-12000")
        self.assertEqual(article_counts.final, "2")
        self.assertEqual(article_counts.section, "3000-4000")

    def test_task_request_validation(self):
        NovelSummaryRequest("novel", big_summary_batch_size=1, super_summary_threshold=1).validate()
        ArticleSummaryRequest("articles", selected_files=["a.txt"]).validate()
        CustomSummaryRequest(["a.txt"], "summarize", "api1").validate()
        SplitterRequest("source.txt", "out", chapters_per_file=1).validate()

        with self.assertRaises(ValueError):
            NovelSummaryRequest("", big_summary_batch_size=0).validate()
        with self.assertRaises(ValueError):
            SplitterRequest("source.txt", "out", mode="bad").validate()

    def test_prompt_message_rejects_unknown_role(self):
        self.assertEqual(PromptMessage.from_dict({"role": "SYSTEM"}).role, "system")

        with self.assertRaisesRegex(ValueError, "system, user, assistant"):
            PromptMessage.from_dict({"role": "developer"})

    def test_default_workflow_prompt_config_groups_nodes_and_modules(self):
        config = create_default_workflow_prompt_config()
        workflows = {workflow.id: workflow for workflow in config.workflows}

        self.assertIn("novel_summary", workflows)
        self.assertIn("article_summary", workflows)
        self.assertGreater(len(workflows["novel_summary"].nodes), 1)
        self.assertEqual(workflows["article_summary"].nodes[0].messages[0].role, "user")
        self.assertIn("current_chunk_text", workflows["article_summary"].nodes[0].variables)
        self.assertEqual(config.modules[0].id, "general_prepend_prompt")


class ConfigServiceTests(unittest.TestCase):
    def test_load_save_api_configs_and_public_view(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "api_configs.json")
            configs = [
                ApiConfig.from_dict(
                    {
                        "id": "api1",
                        "url": "http://example.test/v1",
                        "key": "secret",
                        "model": "model",
                    }
                )
            ]

            save_api_configs(filepath, configs)
            loaded = load_api_configs(filepath)
            public = public_api_configs(loaded)
            resolved = resolve_api_config(loaded[0], {})

            self.assertEqual(loaded[0].id, "api1")
            self.assertEqual(resolved["key"], "secret")
            self.assertEqual(resolved["api_key_name"], "api1")
            self.assertEqual(resolved["display_name"], "api1")
            self.assertEqual(public[0]["display_name"], "api1")
            self.assertNotEqual(public[0]["key"], "secret")

    def test_load_api_configs_adds_friendly_default_display_names(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "api_configs.json")
            with open(filepath, "w", encoding="utf-8") as f:
                f.write('[{"id": "internal_api_id"}]')

            loaded = load_api_configs(filepath)

            self.assertEqual(loaded[0].id, "internal_api_id")
            self.assertEqual(loaded[0].display_name, "API 1")

    def test_user_settings_round_trip_normalizes_default_export_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "user_settings.json")
            export_dir = os.path.join(tmpdir, "exports-root")

            settings = prepare_user_settings_for_save(
                {"default_export_directory": export_dir}
            )
            save_user_settings(filepath, settings)
            loaded = load_user_settings(filepath)

            self.assertEqual(loaded.default_export_directory, os.path.abspath(export_dir))
            self.assertEqual(loaded.minimum_output_characters, 0)
            self.assertTrue(os.path.isdir(export_dir))

    def test_user_settings_round_trip_minimum_output_characters(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "user_settings.json")

            settings = prepare_user_settings_for_save(
                {"default_export_directory": "", "minimum_output_characters": "120"}
            )
            save_user_settings(filepath, settings)
            loaded = load_user_settings(filepath)

            self.assertEqual(loaded.minimum_output_characters, 120)

    def test_user_settings_rejects_invalid_minimum_output_characters(self):
        with self.assertRaisesRegex(ValueError, "非负整数"):
            prepare_user_settings_for_save(
                {"default_export_directory": "", "minimum_output_characters": "many"}
            )

        with self.assertRaisesRegex(ValueError, "不能小于 0"):
            prepare_user_settings_for_save(
                {"default_export_directory": "", "minimum_output_characters": -1}
            )

    def test_user_settings_rejects_file_as_default_export_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            export_file = os.path.join(tmpdir, "exports.txt")
            with open(export_file, "w", encoding="utf-8") as f:
                f.write("not a directory")

            with self.assertRaisesRegex(ValueError, "不能是文件"):
                prepare_user_settings_for_save(
                    {"default_export_directory": export_file}
                )

    def test_save_user_settings_allows_clearing_default_export_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "user_settings.json")

            save_user_settings(filepath, UserSettings(default_export_directory=""))
            loaded = load_user_settings(filepath)

            self.assertEqual(loaded.default_export_directory, "")

    def test_prepare_api_configs_rejects_duplicate_display_names(self):
        with self.assertRaisesRegex(ValueError, "不能重复"):
            prepare_api_configs_for_save(
                [
                    {"id": "api1", "display_name": "主力 API"},
                    {"id": "api2", "display_name": "主力 API"},
                ],
                [],
            )

    def test_prompt_templates_load_saved_text(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            templates = load_prompt_templates(tmpdir)
            first = templates[0]
            first.text = "custom prompt"

            save_prompt_template(tmpdir, first)
            reloaded = load_prompt_templates(tmpdir)
            match = next(template for template in reloaded if template.key == first.key)

            self.assertEqual(match.text, "custom prompt")

    def test_workflow_prompt_config_uses_defaults_without_cache(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = load_workflow_prompt_config(tmpdir)
            article_node = next(
                node
                for workflow in config.workflows
                if workflow.id == "article_summary"
                for node in workflow.nodes
                if node.prompt_key == "prompt_article_section"
            )

            self.assertEqual(config.source, "defaults")
            self.assertEqual(
                article_node.messages[0].content,
                DEFAULT_PROMPTS["prompt_article_section"]["default"],
            )

    def test_workflow_prompt_config_uses_legacy_prompt_cache(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            filename = DEFAULT_PROMPTS["prompt_article_section"]["filename"]
            with open(os.path.join(tmpdir, filename), "w", encoding="utf-8") as f:
                f.write("legacy article prompt")

            config = load_workflow_prompt_config(tmpdir)
            article_node = next(
                node
                for workflow in config.workflows
                if workflow.id == "article_summary"
                for node in workflow.nodes
                if node.prompt_key == "prompt_article_section"
            )

            self.assertEqual(config.source, "legacy")
            self.assertEqual(article_node.messages[0].content, "legacy article prompt")

    def test_workflow_prompt_config_keeps_default_for_missing_legacy_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            filename = DEFAULT_PROMPTS["prompt_article_section"]["filename"]
            with open(os.path.join(tmpdir, filename), "w", encoding="utf-8") as f:
                f.write("legacy article prompt")

            config = load_workflow_prompt_config(tmpdir)
            final_node = next(
                node
                for workflow in config.workflows
                if workflow.id == "article_summary"
                for node in workflow.nodes
                if node.prompt_key == "prompt_article_final"
            )

            self.assertEqual(
                final_node.messages[0].content,
                DEFAULT_PROMPTS["prompt_article_final"]["default"],
            )

    def test_workflow_prompt_config_round_trip_preserves_message_order_and_role(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = load_workflow_prompt_config(tmpdir)
            article_node = next(
                node
                for workflow in config.workflows
                if workflow.id == "article_summary"
                for node in workflow.nodes
                if node.prompt_key == "prompt_article_section"
            )
            article_node.messages = [
                PromptMessage(id="system-1", role="system", content="system text"),
                PromptMessage(id="user-1", role="user", content="user text"),
            ]

            save_workflow_prompt_config(tmpdir, config)
            reloaded = load_workflow_prompt_config(tmpdir)
            reloaded_node = next(
                node
                for workflow in reloaded.workflows
                if workflow.id == "article_summary"
                for node in workflow.nodes
                if node.prompt_key == "prompt_article_section"
            )

            self.assertEqual(reloaded.source, "structured")
            self.assertEqual([message.role for message in reloaded_node.messages], ["system", "user"])
            self.assertEqual([message.content for message in reloaded_node.messages], ["system text", "user text"])

    def test_update_workflow_prompt_node_and_reset(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            updated = update_workflow_prompt_node(
                tmpdir,
                "prompt_article_section",
                {
                    "messages": [
                        {"id": "assistant-1", "role": "assistant", "content": "changed"}
                    ]
                },
            )
            self.assertEqual(updated.messages[0].role, "assistant")

            reset = reset_workflow_prompt_node(tmpdir, "prompt_article_section")

            self.assertEqual(reset.messages[0].role, "user")
            self.assertEqual(
                reset.messages[0].content,
                DEFAULT_PROMPTS["prompt_article_section"]["default"],
            )

    def test_upsert_prompt_module_persists_module(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            upsert_prompt_module(
                tmpdir,
                {
                    "id": "style_module",
                    "name": "风格模块",
                    "description": "输出风格",
                    "content": "保持简洁",
                },
            )

            config = load_workflow_prompt_config(tmpdir)
            module = next(item for item in config.modules if item.id == "style_module")

            self.assertEqual(module.name, "风格模块")
            self.assertEqual(module.content, "保持简洁")

    def test_update_node_rejects_unknown_module_reference(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with self.assertRaisesRegex(ValueError, "Unknown prompt module reference"):
                update_workflow_prompt_node(
                    tmpdir,
                    "prompt_article_section",
                    {
                        "messages": [
                            {
                                "id": "user-1",
                                "role": "user",
                                "content": "{{module:missing_module}}\n正文",
                            }
                        ]
                    },
                )

    def test_delete_prompt_module_rejects_referenced_module(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            update_workflow_prompt_node(
                tmpdir,
                "prompt_article_section",
                {
                    "messages": [
                        {
                            "id": "user-1",
                            "role": "user",
                            "content": "{{module:general_prepend_prompt}}\n正文",
                        }
                    ]
                },
            )

            with self.assertRaisesRegex(ValueError, "still used"):
                delete_prompt_module(tmpdir, "general_prepend_prompt")

    def test_runtime_prompt_loader_uses_structured_workflow_config(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            update_workflow_prompt_node(
                tmpdir,
                "prompt_article_section",
                {
                    "messages": [
                        {
                            "id": "system-1",
                            "role": "system",
                            "content": "{{module:general_prepend_prompt}}",
                        },
                        {"id": "user-1", "role": "user", "content": "总结 {filename_for_context}"},
                    ]
                },
            )

            with mock.patch("logic.utils.get_global_prompt_cache_dir", return_value=tmpdir):
                prompts = logic_utils.load_all_prompts_for_run()

            node = prompts["prompt_article_section"]
            self.assertEqual([message["role"] for message in node["messages"]], ["system", "user"])
            self.assertEqual(node["modules"][0]["id"], "general_prepend_prompt")
            self.assertIn("总结 {filename_for_context}", node["text"])

    def test_prepare_api_configs_preserves_masked_key(self):
        existing = [
            ApiConfig.from_dict(
                {
                    "id": "api1",
                    "url": "http://old.example/v1",
                    "key": "real-secret",
                    "model": "old-model",
                }
            )
        ]

        prepared = prepare_api_configs_for_save(
            [
                {
                    "id": "api1",
                    "url": "http://new.example/v1",
                    "key": "********cret",
                    "has_key": True,
                    "model": "new-model",
                }
            ],
            existing,
        )

        self.assertEqual(prepared[0].key, "real-secret")
        self.assertEqual(prepared[0].url, "http://new.example/v1")

    def test_dotenv_values_are_available_for_api_keys(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            env_path = os.path.join(tmpdir, ".env")
            with open(env_path, "w", encoding="utf-8") as f:
                f.write("# local secrets\n")
                f.write("NSA_API_KEY=dotenv-secret\n")
                f.write("QUOTED=\"quoted value\" # comment\n")

            values = load_dotenv_values(env_path)
            env = merged_environment(dotenv_path=env_path, environ={})
            config = ApiConfig.from_dict(
                {
                    "id": "api1",
                    "key": "local-secret",
                    "key_env_var": "NSA_API_KEY",
                }
            )

            self.assertEqual(values["QUOTED"], "quoted value")
            self.assertEqual(config.effective_key(env), "dotenv-secret")

    def test_system_environment_overrides_dotenv(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            env_path = os.path.join(tmpdir, ".env")
            with open(env_path, "w", encoding="utf-8") as f:
                f.write("NSA_API_KEY=dotenv-secret\n")

            env = merged_environment(
                dotenv_path=env_path,
                environ={"NSA_API_KEY": "system-secret"},
            )

            self.assertEqual(env["NSA_API_KEY"], "system-secret")


if __name__ == "__main__":
    unittest.main()
