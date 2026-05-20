import tempfile
import unittest
import json
from pathlib import Path

from webui_backend.project_workspace import (
    ProjectWorkspaceService,
    sanitize_project_name,
)


class ProjectWorkspaceTests(unittest.TestCase):
    def test_sanitize_project_name_keeps_display_name_and_safe_slug(self):
        display_name, slug = sanitize_project_name(" 我的:小说/项目 ")

        self.assertEqual(display_name, "我的:小说/项目")
        self.assertEqual(slug, "我的_小说_项目")

    def test_upload_and_resolve_refs_preserves_order_and_duplicates(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            service = ProjectWorkspaceService(tmpdir)
            metadata = service.upload_text_files(
                project_name="项目一",
                workflow_type="novel_summary",
                files=[
                    {"name": "2.txt", "content": "two"},
                    {"name": "1.txt", "content": "one"},
                ],
            )
            ids = [metadata.uploads[1].id, metadata.uploads[0].id, metadata.uploads[1].id]

            resolved = service.resolve_upload_refs(metadata.project_slug, ids)

            self.assertEqual([item.original_name for item in resolved], ["1.txt", "2.txt", "1.txt"])
            self.assertTrue(Path(resolved[0].path).exists())

    def test_resolve_refs_rejects_missing_reference(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            service = ProjectWorkspaceService(tmpdir)
            metadata = service.upload_text_files(
                project_name="项目一",
                workflow_type="article_summary",
                files=[{"name": "a.txt", "content": "a"}],
            )

            with self.assertRaisesRegex(ValueError, "未知上传文件引用"):
                service.resolve_upload_refs(metadata.project_slug, ["missing"])

    def test_default_export_dir_uses_project_and_workflow(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            service = ProjectWorkspaceService(tmpdir)
            _, slug = sanitize_project_name("项目一")

            output_dir = service.default_export_dir(slug, "chapter_split", create=True)

            self.assertTrue(output_dir.exists())
            self.assertEqual(output_dir, Path(tmpdir) / "exports" / slug / "chapter-split")

    def test_project_history_marks_missing_uploads(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            service = ProjectWorkspaceService(tmpdir)
            metadata = service.upload_text_files(
                project_name="项目一",
                workflow_type="custom_summary",
                files=[{"name": "a.txt", "content": "a"}],
            )
            Path(metadata.uploads[0].path).unlink()

            loaded = service.load_project(metadata.project_slug).to_dict()

            self.assertTrue(loaded["uploads"][0]["missing"])
            self.assertIn("缺失上传文件", loaded["warnings"][0])

    def test_reusing_project_name_keeps_project_and_avoids_file_collision(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            service = ProjectWorkspaceService(tmpdir)
            first = service.upload_text_files(
                project_name="项目一",
                workflow_type="novel_summary",
                files=[{"name": "a.txt", "content": "a"}],
            )
            second = service.upload_text_files(
                project_name="项目一",
                workflow_type="novel_summary",
                files=[{"name": "a.txt", "content": "b"}],
            )

            self.assertEqual(first.project_slug, second.project_slug)
            self.assertEqual([item.stored_name for item in second.uploads], ["a.txt", "a_2.txt"])

    def test_rename_project_updates_display_name_without_changing_slug(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            service = ProjectWorkspaceService(tmpdir)
            metadata = service.upload_text_files(
                project_name="旧名称",
                workflow_type="novel_summary",
                files=[{"name": "a.txt", "content": "a"}],
            )

            renamed = service.rename_project(metadata.project_slug, "新名称")

            self.assertEqual(renamed.project_name, "新名称")
            self.assertEqual(renamed.project_slug, metadata.project_slug)

    def test_clear_project_uploads_removes_input_files_and_metadata(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            service = ProjectWorkspaceService(tmpdir)
            metadata = service.upload_text_files(
                project_name="项目一",
                workflow_type="novel_summary",
                files=[
                    {"name": "a.txt", "content": "a"},
                    {"name": "b.txt", "content": "b"},
                ],
            )
            uploaded_paths = [Path(upload.path) for upload in metadata.uploads]

            cleared = service.clear_project_uploads(metadata.project_slug)

            self.assertEqual(cleared.uploads, [])
            self.assertTrue(all(not path.exists() for path in uploaded_paths))

    def test_import_legacy_novel_project_copies_inputs_and_reads_progress(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            legacy_dir = Path(tmpdir) / "旧项目"
            cache_dir = legacy_dir / ".summarizer_cache"
            legacy_dir.mkdir()
            cache_dir.mkdir()
            (legacy_dir / "1.txt").write_text("one", encoding="utf-8")
            (legacy_dir / "2.txt").write_text("two", encoding="utf-8")
            (cache_dir / "task_id.txt").write_text("abc", encoding="utf-8")
            (cache_dir / "state_abc.json").write_text(
                json.dumps({"small_summary": {"1.txt": True}}, ensure_ascii=False),
                encoding="utf-8",
            )
            runtime_dir = Path(tmpdir) / "runtime"
            service = ProjectWorkspaceService(runtime_dir)

            metadata = service.import_project_directory(
                source_directory=legacy_dir,
                workflow_type="novel_summary",
            )
            data = metadata.to_dict()

            self.assertEqual(data["project_name"], "旧项目")
            self.assertEqual(data["upload_count"], 2)
            self.assertEqual(data["progress"]["summary"], "小总结 1/2")
            self.assertTrue(
                (Path(metadata.default_output_directory) / ".summarizer_cache" / "state_abc.json").exists()
            )

    def test_import_article_project_reads_nested_legacy_state(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            legacy_dir = Path(tmpdir) / "文章旧项目"
            cache_dir = legacy_dir / "article_output" / ".summarizer_cache"
            legacy_dir.mkdir()
            cache_dir.mkdir(parents=True)
            (legacy_dir / "a.txt").write_text("article", encoding="utf-8")
            (cache_dir / "article_summary_state.json").write_text(
                json.dumps({"processed_sections": ["summary_a.txt"]}, ensure_ascii=False),
                encoding="utf-8",
            )
            service = ProjectWorkspaceService(Path(tmpdir) / "runtime")

            metadata = service.import_project_directory(
                source_directory=legacy_dir,
                workflow_type="article_summary",
            )

            self.assertEqual(metadata.progress["summary"], "段落总结 1/1")
            self.assertTrue(
                (
                    Path(metadata.default_output_directory)
                    / ".summarizer_cache"
                    / "article_summary_state.json"
                ).exists()
            )


if __name__ == "__main__":
    unittest.main()
