import os
import tempfile
import unittest
from pathlib import Path

from logic.paragraph_index import (
    build_chapter_paragraph_index,
    extract_paragraph_context,
)


class ParagraphIndexTests(unittest.TestCase):
    def test_build_index_assigns_stable_paragraph_ids_and_title(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            chapter = Path(tmpdir) / "chapter-1.txt"
            chapter.write_text("Chapter One\n\nFirst paragraph.\nSecond paragraph.\n", encoding="utf-8")

            index = build_chapter_paragraph_index(chapter)

            self.assertEqual(index.chapter_title, "Chapter One")
            self.assertEqual([paragraph.id for paragraph in index.paragraphs], ["P001", "P002", "P003"])
            self.assertEqual(index.paragraphs[1].text, "First paragraph.")
            self.assertFalse(index.cache_hit)

    def test_build_index_reuses_unchanged_cache(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            chapter = Path(tmpdir) / "chapter-1.txt"
            chapter.write_text("Title\nBody\n", encoding="utf-8")

            first = build_chapter_paragraph_index(chapter)
            second = build_chapter_paragraph_index(chapter)

            self.assertFalse(first.cache_hit)
            self.assertTrue(second.cache_hit)
            self.assertEqual(second.content_hash, first.content_hash)

    def test_build_index_invalidates_cache_when_content_changes(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            chapter = Path(tmpdir) / "chapter-1.txt"
            chapter.write_text("Title\nOld body\n", encoding="utf-8")
            first = build_chapter_paragraph_index(chapter)

            chapter.write_text("Title\nNew body\n", encoding="utf-8")
            os.utime(chapter, None)
            second = build_chapter_paragraph_index(chapter)

            self.assertFalse(second.cache_hit)
            self.assertNotEqual(second.content_hash, first.content_hash)
            self.assertEqual(second.paragraphs[1].text, "New body")

    def test_build_index_splits_long_chapter_into_chunks(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            chapter = Path(tmpdir) / "chapter-1.txt"
            chapter.write_text(
                "\n".join(["Title", "a" * 10, "b" * 10, "c" * 10, "d" * 10]),
                encoding="utf-8",
            )

            index = build_chapter_paragraph_index(chapter, max_chunk_chars=21)

            self.assertGreater(len(index.chunks), 1)
            self.assertEqual(index.chunks[0].id, "C001")
            self.assertEqual(
                [paragraph_id for chunk in index.chunks for paragraph_id in chunk.paragraph_ids],
                [paragraph.id for paragraph in index.paragraphs],
            )

    def test_extract_paragraph_context_includes_neighbors_and_missing_ids(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            chapter = Path(tmpdir) / "chapter-1.txt"
            chapter.write_text(
                "Title\nFirst paragraph.\nSecond paragraph.\nThird paragraph.\nFourth paragraph.",
                encoding="utf-8",
            )
            index = build_chapter_paragraph_index(chapter)

            context = extract_paragraph_context(index, ["P003", "P999"], before=1, after=1)

            self.assertEqual(context.paragraph_ids, ["P002", "P003", "P004"])
            self.assertEqual(context.matched_paragraph_ids, ["P003"])
            self.assertEqual(context.missing_paragraph_ids, ["P999"])
            self.assertIn("P003 Second paragraph.", context.text)


if __name__ == "__main__":
    unittest.main()
