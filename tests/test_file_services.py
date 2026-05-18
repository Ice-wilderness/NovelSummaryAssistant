import os
import tempfile
import unittest
from pathlib import Path

from webui_backend import file_services


class FileServicesTests(unittest.TestCase):
    def test_cache_paths_support_chinese_and_space_paths(self):
        with tempfile.TemporaryDirectory(prefix="小说 项目_") as tmpdir:
            source = Path(tmpdir) / "中文 路径"
            source.mkdir()

            cache_dir = file_services.get_summarizer_cache_dir(str(source))
            task_id_path = file_services.get_task_id_path(str(source))
            article_state_path = file_services.get_article_state_path(str(source))

            self.assertTrue(cache_dir.exists())
            self.assertEqual(task_id_path.parent, cache_dir)
            self.assertEqual(article_state_path.parent, cache_dir)

    def test_prompt_cache_dir_uses_project_root(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = file_services.ensure_prompt_cache_dir(Path(tmpdir))

            self.assertEqual(cache_dir, Path(tmpdir) / "prompt_cache")
            self.assertTrue(cache_dir.exists())

    def test_read_text_file_handles_utf8_bom(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "bom.txt")
            with open(filepath, "w", encoding="utf-8-sig") as f:
                f.write("hello")

            self.assertEqual(file_services.read_text_file(filepath).lstrip("\ufeff"), "hello")

    def test_safe_filename_and_natural_sort(self):
        safe = file_services.safe_filename('bad<>:"/\\|?*name.txt')
        sorted_names = file_services.sort_naturally(["第十章.txt", "第二章.txt", "第一章.txt"])

        self.assertNotIn("<", safe)
        self.assertEqual(sorted_names, ["第一章.txt", "第二章.txt", "第十章.txt"])

    def test_long_filename_is_limited(self):
        long_name = "a" * 240 + ".txt"
        safe = file_services.safe_filename(long_name, max_length=80)

        self.assertLessEqual(len(safe), 80)
        self.assertTrue(safe.endswith(".txt"))


if __name__ == "__main__":
    unittest.main()
