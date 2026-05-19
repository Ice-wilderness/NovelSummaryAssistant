import tempfile
import unittest
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


if __name__ == "__main__":
    unittest.main()
