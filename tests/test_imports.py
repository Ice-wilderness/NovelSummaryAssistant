import importlib
import unittest


class ImportSmokeTests(unittest.TestCase):
    def test_core_modules_import(self):
        modules = [
            "config",
            "logic.orchestrator",
            "logic.llm_api",
            "logic.state_manager",
            "logic.article_summary_logic",
            "logic.chapter_splitter",
            "logic.custom_summary_logic",
            "splitters.default_strategy",
            "splitters.regex_strategy",
            "splitters.title_list_strategy",
        ]

        for module_name in modules:
            with self.subTest(module=module_name):
                importlib.import_module(module_name)

    def test_legacy_gui_modules_import(self):
        modules = [
            "gui.main_app",
            "gui.api_manager",
            "gui.event_handlers",
            "gui.prompt_manager",
            "gui.custom_summary_manager",
            "gui.splitter_tab_ui",
            "gui.article_tab_ui",
        ]

        for module_name in modules:
            with self.subTest(module=module_name):
                importlib.import_module(module_name)


if __name__ == "__main__":
    unittest.main()
