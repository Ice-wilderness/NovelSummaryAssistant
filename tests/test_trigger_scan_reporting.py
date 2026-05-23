import tempfile
import unittest
from pathlib import Path

from logic.trigger_scan.reporting import (
    AI_AUXILIARY_WARNING,
    TriggerScanReportStore,
)
from webui_backend.trigger_models import (
    EventSummary,
    ScanEvent,
    ScanFinding,
    ScanRange,
    ScanReport,
    ScanReportSummary,
    SpoilerDescription,
    SpoilerLevels,
    TriggerScanConfig,
)


def _report(status: str = "completed") -> ScanReport:
    finding = ScanFinding(
        finding_id="f1",
        rule_id="rule_a",
        rule_name="Rule A",
        chapter_file="001.txt",
        chapter_title="Title",
        paragraph_ids=["P001"],
        severity=3,
        confidence=0.9,
        spoiler_levels=SpoilerLevels(
            low=SpoilerDescription(description="low"),
            standard=SpoilerDescription(description="standard"),
            detailed=SpoilerDescription(
                description="detailed",
                evidence_quote="x" * 120,
            ),
        ),
    )
    return ScanReport(
        report_id="report-1",
        project_slug="novel",
        profile_id="profile",
        profile_name="Profile",
        scan_mode="precise",
        scan_range=ScanRange(start=1, end=3),
        scan_config=TriggerScanConfig(max_quote_chars=20),
        created_at=10,
        completed_at=20,
        status=status,
        summary=ScanReportSummary(total_findings=1, pending_review=1),
        events=[
            ScanEvent(
                event_id="event-1",
                rule_id="rule_a",
                rule_name="Rule A",
                first_chapter="001.txt",
                related_chapters=["001.txt"],
                max_severity=3,
                max_confidence=0.9,
                finding_ids=["f1"],
                event_summary=EventSummary(standard="event"),
            )
        ],
        findings=[finding],
    )


class TriggerScanReportingTests(unittest.TestCase):
    def test_report_store_persists_history_and_loads_report(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = TriggerScanReportStore(tmpdir)

            store.save_report(_report())
            history = store.list_reports()
            loaded = store.load_report("report-1")

            self.assertEqual(history[0].report_id, "report-1")
            self.assertEqual(history[0].finding_count, 1)
            self.assertEqual(loaded.findings[0].finding_id, "f1")

    def test_report_store_rebuilds_history_for_imported_reports(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = TriggerScanReportStore(tmpdir)
            store.save_report(_report())
            store.index_path.unlink()

            rebuilt = store.list_reports()

            self.assertEqual([entry.report_id for entry in rebuilt], ["report-1"])

    def test_report_store_preserves_failed_partial_report(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = TriggerScanReportStore(tmpdir)

            report = store.save_partial_report(_report(status="running"))

            self.assertEqual(report.status, "failed")
            loaded = store.load_report("report-1")
            self.assertEqual(loaded.status, "completed")
            self.assertEqual(len(loaded.findings), 1)

    def test_update_finding_review_and_exports_report(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = TriggerScanReportStore(tmpdir)
            store.save_report(_report())

            finding = store.update_finding_review(
                "report-1",
                "f1",
                review_status="confirmed",
                user_note="checked",
            )
            json_path = store.export_report_json("report-1")
            markdown_path = store.export_report_markdown("report-1")
            markdown = markdown_path.read_text(encoding="utf-8")

            self.assertEqual(finding.review_status, "confirmed")
            self.assertTrue(json_path.exists())
            self.assertIn(AI_AUXILIARY_WARNING, markdown)
            self.assertIn("证据摘录：" + "x" * 20, markdown)
            self.assertNotIn("x" * 21, markdown)

    def test_delete_report_updates_history(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = TriggerScanReportStore(tmpdir)
            store.save_report(_report())

            store.delete_report("report-1")

            self.assertEqual(store.list_reports(), [])
            self.assertFalse(store.report_path("report-1").exists())


if __name__ == "__main__":
    unittest.main()
