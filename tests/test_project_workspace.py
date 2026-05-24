import json
import tempfile
import unittest
from pathlib import Path

from logic.prompts import (
    USER_FACING_BIG_PLOT_SUBDIR,
    USER_FACING_SMALL_CHAR_SUBDIR,
    USER_FACING_SMALL_PLOT_SUBDIR,
)
from webui_backend.project_workspace import (
    OUTPUT_OWNERSHIP_FILENAME,
    OUTPUT_OWNERSHIP_OWNER,
    OUTPUT_OWNERSHIP_PURPOSE,
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

    def test_project_novel_options_default_and_persist(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            service = ProjectWorkspaceService(tmpdir)
            metadata = service.upload_text_files(
                project_name="项目一",
                workflow_type="novel_summary",
                files=[{"name": "1.txt", "content": "one"}],
            )

            self.assertEqual(metadata.summary_output_format, "md")
            self.assertFalse(metadata.use_fine_grained_flow)

            saved = service.save_project_draft(
                metadata.project_slug,
                project_name=metadata.project_name,
                summary_output_format="txt",
                use_fine_grained_flow=True,
            )
            reloaded = service.load_project(metadata.project_slug)

            self.assertEqual(saved.summary_output_format, "txt")
            self.assertTrue(saved.use_fine_grained_flow)
            self.assertEqual(reloaded.summary_output_format, "txt")
            self.assertTrue(reloaded.use_fine_grained_flow)

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

    def test_default_export_dir_writes_output_ownership_metadata(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            service = ProjectWorkspaceService(tmpdir)
            _, slug = sanitize_project_name("项目一")

            service.default_export_dir(slug, "chapter_split", create=True)
            ownership_path = Path(tmpdir) / "exports" / slug / OUTPUT_OWNERSHIP_FILENAME
            ownership = json.loads(ownership_path.read_text(encoding="utf-8"))

            self.assertEqual(ownership["owner"], OUTPUT_OWNERSHIP_OWNER)
            self.assertEqual(ownership["project_slug"], slug)
            self.assertEqual(ownership["purpose"], OUTPUT_OWNERSHIP_PURPOSE)

    def test_default_export_dir_uses_user_default_root_when_configured(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            export_root = Path(tmpdir) / "user-exports"
            service = ProjectWorkspaceService(
                Path(tmpdir) / "runtime",
                default_export_directory=str(export_root),
            )
            _, slug = sanitize_project_name("项目一")

            output_dir = service.default_export_dir(slug, "article_summary", create=True)

            self.assertTrue(output_dir.exists())
            self.assertEqual(output_dir, export_root / slug / "article-summary")

    def test_default_export_dir_falls_back_when_user_default_is_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            runtime_dir = Path(tmpdir) / "runtime"
            invalid_root = Path(tmpdir) / "exports.txt"
            invalid_root.write_text("not a directory", encoding="utf-8")
            service = ProjectWorkspaceService(
                runtime_dir,
                default_export_directory=str(invalid_root),
            )
            _, slug = sanitize_project_name("项目一")

            output_dir = service.default_export_dir(slug, "chapter_split", create=True)

            self.assertEqual(output_dir, runtime_dir / "exports" / slug / "chapter-split")

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

    def test_loads_legacy_project_metadata_without_output_ownership(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            service = ProjectWorkspaceService(tmpdir)
            project_slug = "legacy-project"
            project_dir = service.project_dir(project_slug)
            project_dir.mkdir(parents=True)
            service.metadata_path(project_slug).write_text(
                json.dumps(
                    {
                        "project_name": "旧项目",
                        "project_slug": project_slug,
                        "workflow_type": "novel_summary",
                        "default_output_directory": str(Path(tmpdir) / "exports" / project_slug),
                        "custom_output_directory": "",
                        "uploads": [],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            loaded = service.load_project(project_slug).to_dict()

            self.assertEqual(loaded["project_slug"], project_slug)
            self.assertEqual(loaded["warnings"], [])

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

    def test_delete_project_removes_workspace_and_managed_export_only(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            service = ProjectWorkspaceService(tmpdir)
            metadata = service.upload_text_files(
                project_name="删除项目",
                workflow_type="chapter_split",
                files=[{"name": "a.txt", "content": "a"}],
            )
            managed_output = service.default_export_dir(
                metadata.project_slug,
                metadata.workflow_type,
                create=True,
            )
            (managed_output / "result.txt").write_text("ok", encoding="utf-8")
            managed_trigger_reports = managed_output / "trigger_scan" / "reports"
            managed_trigger_reports.mkdir(parents=True)
            (managed_trigger_reports / "report1.json").write_text("{}", encoding="utf-8")
            custom_output = Path(tmpdir) / "custom-output"
            custom_output.mkdir()
            custom_trigger_reports = custom_output / "trigger_scan" / "reports"
            custom_trigger_reports.mkdir(parents=True)
            (custom_trigger_reports / "report2.json").write_text("{}", encoding="utf-8")
            metadata.custom_output_directory = str(custom_output)
            service.save_project(metadata)

            result = service.delete_project(metadata.project_slug)

            self.assertFalse(service.project_dir(metadata.project_slug).exists())
            self.assertFalse((Path(tmpdir) / "exports" / metadata.project_slug).exists())
            self.assertTrue(custom_output.exists())
            self.assertTrue((custom_trigger_reports / "report2.json").exists())
            self.assertTrue(result["deleted_project_directory"])
            self.assertEqual(
                result["deleted_output_directories"],
                [str(Path(tmpdir) / "exports" / metadata.project_slug)],
            )
            self.assertEqual(
                result["preserved_output_directories"],
                [
                    {
                        "path": str(custom_output),
                        "reason": "custom_output_directory",
                        "message": "自定义输出目录不会随项目历史自动删除，已保留。",
                    }
                ],
            )

    def test_delete_project_preserves_output_with_mismatched_ownership(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            service = ProjectWorkspaceService(tmpdir)
            metadata = service.upload_text_files(
                project_name="删除项目",
                workflow_type="chapter_split",
                files=[{"name": "a.txt", "content": "a"}],
            )
            managed_output = service.default_export_dir(
                metadata.project_slug,
                metadata.workflow_type,
                create=True,
            )
            project_export_dir = managed_output.parent
            (managed_output / "result.txt").write_text("ok", encoding="utf-8")
            (project_export_dir / OUTPUT_OWNERSHIP_FILENAME).write_text(
                json.dumps(
                    {
                        "owner": OUTPUT_OWNERSHIP_OWNER,
                        "project_slug": "other-project",
                        "purpose": OUTPUT_OWNERSHIP_PURPOSE,
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            result = service.delete_project(metadata.project_slug)

            self.assertFalse(service.project_dir(metadata.project_slug).exists())
            self.assertTrue(project_export_dir.exists())
            self.assertTrue((managed_output / "result.txt").exists())
            self.assertEqual(result["deleted_output_directories"], [])
            self.assertEqual(result["preserved_output_directories"][0]["path"], str(project_export_dir))
            self.assertEqual(result["preserved_output_directories"][0]["reason"], "ownership_mismatch")

    def test_delete_project_reports_preserved_output_without_ownership(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            service = ProjectWorkspaceService(tmpdir)
            metadata = service.upload_text_files(
                project_name="删除项目",
                workflow_type="chapter_split",
                files=[{"name": "a.txt", "content": "a"}],
            )
            project_export_dir = Path(tmpdir) / "exports" / metadata.project_slug
            workflow_output = project_export_dir / "chapter-split"
            workflow_output.mkdir(parents=True)
            (workflow_output / "result.txt").write_text("ok", encoding="utf-8")

            result = service.delete_project(metadata.project_slug)

            self.assertFalse(service.project_dir(metadata.project_slug).exists())
            self.assertTrue(project_export_dir.exists())
            self.assertTrue((workflow_output / "result.txt").exists())
            self.assertEqual(result["deleted_output_directories"], [])
            self.assertEqual(result["preserved_output_directories"][0]["path"], str(project_export_dir))
            self.assertEqual(
                result["preserved_output_directories"][0]["reason"],
                "missing_ownership_metadata",
            )

    def test_delete_project_reports_preserved_imported_output(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            source_dir = Path(tmpdir) / "legacy-project"
            source_dir.mkdir()
            (source_dir / "chapter1.txt").write_text("text", encoding="utf-8")
            service = ProjectWorkspaceService(Path(tmpdir) / "runtime")
            metadata = service.import_project_directory(
                source_directory=source_dir,
                workflow_type="novel_summary",
            )

            result = service.delete_project(metadata.project_slug)

            self.assertFalse(service.project_dir(metadata.project_slug).exists())
            self.assertTrue(source_dir.exists())
            self.assertEqual(result["preserved_output_directories"][0]["path"], str(source_dir))
            self.assertEqual(
                result["preserved_output_directories"][0]["reason"],
                "imported_output_directory",
            )

    def test_delete_project_rejects_missing_project(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            service = ProjectWorkspaceService(tmpdir)

            with self.assertRaisesRegex(ValueError, "项目不存在"):
                service.delete_project("missing")

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
            (cache_dir / USER_FACING_SMALL_PLOT_SUBDIR).mkdir(parents=True)
            (cache_dir / USER_FACING_SMALL_CHAR_SUBDIR).mkdir(parents=True)
            (cache_dir / USER_FACING_SMALL_PLOT_SUBDIR / "1.txt").write_text("plot", encoding="utf-8")
            (cache_dir / USER_FACING_SMALL_CHAR_SUBDIR / "1.txt").write_text("char", encoding="utf-8")
            runtime_dir = Path(tmpdir) / "runtime"
            service = ProjectWorkspaceService(runtime_dir)

            metadata = service.import_project_directory(
                source_directory=legacy_dir,
                workflow_type="novel_summary",
            )
            data = metadata.to_dict()

            self.assertEqual(data["project_name"], "旧项目")
            self.assertEqual(data["upload_count"], 2)
            self.assertEqual(data["custom_output_directory"], str(legacy_dir))
            self.assertEqual(data["latest_task_status"], "partial")
            self.assertEqual(data["progress"]["summary"], "小总结 1/2")
            self.assertTrue((legacy_dir / ".summarizer_cache" / "state_abc.json").exists())

    def test_novel_progress_counts_batched_small_summary_coverage(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / "novel"
            cache_dir = root / ".summarizer_cache"
            (cache_dir / USER_FACING_SMALL_PLOT_SUBDIR).mkdir(parents=True)
            (cache_dir / USER_FACING_SMALL_CHAR_SUBDIR).mkdir(parents=True)
            for name in ["第001章.txt", "第002章.txt", "第003章.txt"]:
                (root / name).write_text("chapter", encoding="utf-8")
            batch_name = "small_batch_第001章_to_第002章.txt"
            (cache_dir / USER_FACING_SMALL_PLOT_SUBDIR / batch_name).write_text("plot", encoding="utf-8")
            (cache_dir / USER_FACING_SMALL_CHAR_SUBDIR / batch_name).write_text("char", encoding="utf-8")
            service = ProjectWorkspaceService(Path(tmpdir) / "runtime")

            progress = service._scan_novel_progress(root)

            self.assertEqual(progress["summary"], "小总结 2/3")
            self.assertEqual(progress["stages"][0]["completed"], 2)

    def test_novel_progress_recognizes_markdown_summaries_and_trigger_artifacts(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / "novel"
            cache_dir = root / ".summarizer_cache"
            (cache_dir / USER_FACING_SMALL_PLOT_SUBDIR).mkdir(parents=True)
            (cache_dir / USER_FACING_SMALL_CHAR_SUBDIR).mkdir(parents=True)
            (cache_dir / USER_FACING_BIG_PLOT_SUBDIR).mkdir(parents=True)
            paragraph_cache = cache_dir / "paragraph_index"
            paragraph_cache.mkdir(parents=True)
            for name in ["第001章.txt", "第002章.txt"]:
                (root / name).write_text("chapter", encoding="utf-8")
            (cache_dir / USER_FACING_SMALL_PLOT_SUBDIR / "small_batch_第001章_to_第002章.md").write_text("plot", encoding="utf-8")
            (cache_dir / USER_FACING_SMALL_CHAR_SUBDIR / "small_batch_第001章_to_第002章.txt").write_text("char", encoding="utf-8")
            (cache_dir / USER_FACING_BIG_PLOT_SUBDIR / "big.md").write_text("big", encoding="utf-8")
            (paragraph_cache / "chapter.json").write_text("{}", encoding="utf-8")
            reports_dir = root / "trigger_scan" / "reports"
            reports_dir.mkdir(parents=True)
            (reports_dir / "report1.json").write_text("{}", encoding="utf-8")
            service = ProjectWorkspaceService(Path(tmpdir) / "runtime")

            progress = service._scan_novel_progress(root)
            stages = {stage["label"]: stage for stage in progress["stages"]}

            self.assertEqual(progress["summary"], "大总结已完成 剧情 1 / 角色 0")
            self.assertEqual(stages["小总结"]["completed"], 2)
            self.assertEqual(stages["大总结-剧情"]["completed"], 1)
            self.assertEqual(stages["雷点报告"]["completed"], 1)
            self.assertEqual(stages["段落缓存"]["completed"], 1)

    def test_import_legacy_grouped_names_no_longer_require_migration(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            legacy_dir = Path(tmpdir) / "legacy"
            legacy_dir.mkdir()
            (legacy_dir / "第001章-第002章.txt").write_text(
                "第一章 开始\n正文一\n第二章 继续\n正文二",
                encoding="utf-8",
            )
            (legacy_dir / "第003章.txt").write_text("第三章 结束\n正文三", encoding="utf-8")
            service = ProjectWorkspaceService(Path(tmpdir) / "runtime")
            metadata = service.import_project_directory(
                source_directory=legacy_dir,
                workflow_type="novel_summary",
            )
            data = metadata.to_dict()

            self.assertFalse(metadata.requires_granularity_migration)
            self.assertEqual(metadata.legacy_grouped_file_count, 0)
            self.assertEqual(metadata.summary_batch_size, 10)
            self.assertEqual(data["warnings"], [])
            self.assertEqual(
                sorted(path.name for path in legacy_dir.glob("*.txt")),
                ["第001章-第002章.txt", "第003章.txt"],
            )

    def test_import_chapter_split_grouped_names_no_longer_require_migration(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            legacy_dir = Path(tmpdir) / "chapter-split-legacy"
            legacy_dir.mkdir()
            (legacy_dir / "第001章-第002章.txt").write_text(
                "第一章 开始\n正文一\n第二章 继续\n正文二",
                encoding="utf-8",
            )
            service = ProjectWorkspaceService(Path(tmpdir) / "runtime")

            metadata = service.import_project_directory(
                source_directory=legacy_dir,
                workflow_type="chapter_split",
            )

            self.assertFalse(metadata.requires_granularity_migration)
            self.assertEqual(metadata.legacy_grouped_file_count, 0)
            self.assertEqual(
                sorted(path.name for path in legacy_dir.glob("*.txt")),
                ["第001章-第002章.txt"],
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
            self.assertEqual(metadata.custom_output_directory, str(legacy_dir))
            self.assertTrue(
                (
                    legacy_dir
                    / ".summarizer_cache"
                    / "article_summary_state.json"
                ).exists()
            )

    def test_save_project_draft_removes_deselected_uploads_on_save(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            service = ProjectWorkspaceService(tmpdir)
            metadata = service.upload_text_files(
                project_name="草稿项目",
                workflow_type="novel_summary",
                files=[
                    {"name": "a.txt", "content": "a"},
                    {"name": "b.txt", "content": "b"},
                ],
            )
            removed_path = Path(metadata.uploads[1].path)

            saved = service.save_project_draft(
                metadata.project_slug,
                project_name="已保存项目",
                uploaded_file_ids=[metadata.uploads[0].id],
            )

            self.assertEqual(saved.project_name, "已保存项目")
            self.assertEqual([upload.original_name for upload in saved.uploads], ["a.txt"])
            self.assertFalse(removed_path.exists())

    def test_output_migration_info_and_migrate_project_output(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            service = ProjectWorkspaceService(tmpdir)
            metadata = service.upload_text_files(
                project_name="迁移项目",
                workflow_type="chapter_split",
                files=[{"name": "a.txt", "content": "a"}],
            )
            old_output = Path(metadata.default_output_directory)
            old_output.mkdir(parents=True, exist_ok=True)
            (old_output / "result.txt").write_text("ok", encoding="utf-8")
            new_output = Path(tmpdir) / "new-output"

            info = service.output_migration_info(
                metadata.project_slug,
                custom_output_directory=str(new_output),
            )
            saved = service.save_project_draft(
                metadata.project_slug,
                project_name=metadata.project_name,
                custom_output_directory=str(new_output),
                migrate_existing_output=True,
            )

            self.assertTrue(info["requires_migration"])
            self.assertEqual(info["file_count"], 1)
            self.assertEqual(saved.custom_output_directory, str(new_output))
            self.assertTrue((new_output / "result.txt").exists())
            self.assertFalse((old_output / "result.txt").exists())

    def test_output_migration_failure_leaves_metadata_unchanged(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            service = ProjectWorkspaceService(tmpdir)
            metadata = service.upload_text_files(
                project_name="迁移失败项目",
                workflow_type="chapter_split",
                files=[{"name": "a.txt", "content": "a"}],
            )
            old_output = Path(metadata.default_output_directory)
            old_output.mkdir(parents=True, exist_ok=True)
            (old_output / "result.txt").write_text("old", encoding="utf-8")
            new_output = Path(tmpdir) / "new-output"
            new_output.mkdir()
            (new_output / "result.txt").write_text("conflict", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "同名"):
                service.save_project_draft(
                    metadata.project_slug,
                    custom_output_directory=str(new_output),
                    migrate_existing_output=True,
                )

            loaded = service.load_project(metadata.project_slug)
            self.assertEqual(loaded.custom_output_directory, "")
            self.assertTrue((old_output / "result.txt").exists())


if __name__ == "__main__":
    unittest.main()
