import json
import tempfile
import unittest
from pathlib import Path

from logic.paragraph_index import build_chapter_paragraph_index
from logic.trigger_scan import (
    ScanStateStore,
    aggregate_findings_into_events,
    apply_verification_results,
    build_precise_chapter_batches,
    build_verification_batches,
    merge_adjacent_findings,
    parse_precise_scan_findings,
    validate_scan_startup,
)
from logic.trigger_scan.json_utils import TriggerScanJsonError
from webui_backend.trigger_models import (
    ScanFinding,
    TriggerProfile,
    TriggerRule,
    TriggerRuleGroup,
    TriggerScanConfig,
)


def _profile() -> TriggerProfile:
    return TriggerProfile(
        id="profile",
        name="Profile",
        rule_groups=[TriggerRuleGroup(id="group", name="Group", rules=["rule_a"])],
        rules=[
            TriggerRule(
                id="rule_a",
                name="Rule A",
                group_id="group",
                severity_threshold=2,
            )
        ],
    )


def _finding(
    finding_id: str,
    chapter_file: str,
    paragraph_ids,
    *,
    severity: int = 3,
    confidence: float = 0.9,
) -> ScanFinding:
    return ScanFinding.from_dict(
        {
            "finding_id": finding_id,
            "rule_id": "rule_a",
            "rule_name": "Rule A",
            "chapter_file": chapter_file,
            "paragraph_ids": list(paragraph_ids),
            "severity": severity,
            "confidence": confidence,
        }
    )


class TriggerScanPipelineTests(unittest.TestCase):
    def test_startup_does_not_require_small_summary_coverage(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "001.txt").write_text("Title 1\nBody", encoding="utf-8")
            (root / "002.txt").write_text("Title 2\nBody", encoding="utf-8")

            config = TriggerScanConfig(scan_api_ids=["api1"])
            result = validate_scan_startup(
                novel_folder_path=root,
                profile=_profile(),
                config=config,
                available_api_ids=["api1"],
            )

            self.assertTrue(result.ready)
            self.assertEqual([Path(item).name for item in result.selected_chapter_files], ["001.txt", "002.txt"])

    def test_startup_rejects_hybrid_scan_mode(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "001.txt").write_text("Title 1\nBody", encoding="utf-8")

            result = validate_scan_startup(
                novel_folder_path=root,
                profile=_profile(),
                config=TriggerScanConfig(scan_mode="hybrid"),
            )

            self.assertFalse(result.ready)
            self.assertIn("scan_mode must be precise; hybrid scan mode has been removed", result.errors)

    def test_startup_reports_legacy_granularity_and_resumable_state(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "第001章-第002章.txt").write_text(
                "第一章 Start\nBody\n第二章 Next\nBody",
                encoding="utf-8",
            )
            config = TriggerScanConfig(scan_mode="precise")
            state = ScanStateStore(root, "task-1").create(config.to_dict(), "profile-v1")

            result = validate_scan_startup(
                novel_folder_path=root,
                profile=_profile(),
                config=config,
                scan_state=state,
                profile_version="profile-v1",
            )

            self.assertFalse(result.ready)
            self.assertIn("chapter granularity migration is required", result.errors)
            self.assertTrue(any("可续扫" in w for w in result.warnings), f"expected resumable warning, got: {result.warnings}")

    def test_batch_builders_use_scan_batch_defaults(self):
        config = TriggerScanConfig()

        self.assertEqual(
            build_precise_chapter_batches(["1", "2", "3", "4", "5", "6"], config),
            [["1", "2", "3", "4", "5"], ["6"]],
        )

    def test_parse_precise_findings_validates_schema_and_filters_thresholds(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            chapter = Path(tmpdir) / "001.txt"
            chapter.write_text("Title\nFirst paragraph.\nSecond paragraph.", encoding="utf-8")
            chapter_index = build_chapter_paragraph_index(chapter)
            config = TriggerScanConfig(min_confidence=0.8, keep_low_confidence=False)
            output = json.dumps(
                {
                    "findings": [
                        {
                            "rule_id": "rule_a",
                            "paragraph_ids": ["P002"],
                            "severity": 3,
                            "confidence": 0.9,
                            "is_main_plot": False,
                            "spoiler_levels": {
                                "low": {"description": "low"},
                                "standard": {"description": "standard"},
                                "detailed": {
                                    "description": "detailed",
                                    "evidence_quote": "First paragraph.",
                                },
                            },
                        },
                        {
                            "rule_id": "rule_a",
                            "paragraph_ids": ["P003"],
                            "severity": 1,
                            "confidence": 0.9,
                            "is_main_plot": False,
                            "spoiler_levels": {
                                "low": {"description": "low"},
                                "standard": {"description": "standard"},
                                "detailed": {
                                    "description": "detailed",
                                    "evidence_quote": "Second paragraph.",
                                },
                            },
                        },
                    ]
                }
            )

            findings = parse_precise_scan_findings(
                output,
                chapter_index=chapter_index,
                profile=_profile(),
                config=config,
            )

            self.assertEqual(len(findings), 1)
            self.assertEqual(findings[0].paragraph_ids, ["P002"])

            with self.assertRaisesRegex(TriggerScanJsonError, "paragraph_ids"):
                parse_precise_scan_findings(
                    json.dumps(
                        {
                            "findings": [
                                {
                                    "rule_id": "rule_a",
                                    "paragraph_ids": ["P999"],
                                    "severity": 3,
                                    "confidence": 0.9,
                                    "is_main_plot": False,
                                    "spoiler_levels": {
                                        "low": {"description": "low"},
                                        "standard": {"description": "standard"},
                                        "detailed": {
                                            "description": "detailed",
                                            "evidence_quote": "Bad paragraph.",
                                        },
                                    },
                                }
                            ]
                        }
                    ),
                    chapter_index=chapter_index,
                    profile=_profile(),
                    config=config,
                )

            with self.assertRaisesRegex(TriggerScanJsonError, "is_main_plot"):
                parse_precise_scan_findings(
                    json.dumps(
                        {
                            "findings": [
                                {
                                    "rule_id": "rule_a",
                                    "paragraph_ids": ["P002"],
                                    "severity": 3,
                                    "confidence": 0.9,
                                    "spoiler_levels": {
                                        "low": {"description": "low"},
                                        "standard": {"description": "standard"},
                                        "detailed": {
                                            "description": "detailed",
                                            "evidence_quote": "First paragraph.",
                                        },
                                    },
                                }
                            ]
                        }
                    ),
                    chapter_index=chapter_index,
                    profile=_profile(),
                    config=config,
                )

    def test_verification_batches_and_results_preserve_chapter_groups(self):
        findings = [
            _finding("f1", "001.txt", ["P001"]),
            _finding("f2", "001.txt", ["P002"]),
            _finding("f3", "002.txt", ["P001"]),
            _finding("f4", "003.txt", ["P001"]),
            _finding("f5", "004.txt", ["P001"]),
            _finding("f6", "005.txt", ["P001"]),
            _finding("f7", "006.txt", ["P001"]),
        ]

        batches = build_verification_batches(findings, TriggerScanConfig())
        verified = apply_verification_results(
            findings,
            json.dumps(
                {
                    "items": [
                        {"finding_id": "f1", "verdict": "confirmed"},
                        {"finding_id": "f2", "verdict": "false_positive", "reason": "not enough context"},
                    ]
                }
            ),
        )
        retained_false_positive = apply_verification_results(
            [_finding("f2", "001.txt", ["P002"])],
            json.dumps(
                {
                    "items": [
                        {"finding_id": "f2", "verdict": "false_positive", "reason": "not enough context"},
                    ]
                }
            ),
            retain_false_positives=True,
        )

        self.assertEqual(len(batches), 2)
        self.assertEqual([finding.finding_id for finding in batches[0][:2]], ["f1", "f2"])
        self.assertNotIn("f2", [finding.finding_id for finding in verified])
        self.assertEqual(verified[0].review_status, "confirmed")
        self.assertEqual(verified[0].verification_status, "confirmed")
        self.assertEqual(retained_false_positive[0].review_status, "false_positive")
        self.assertEqual(retained_false_positive[0].verification_status, "false_positive")
        self.assertEqual(retained_false_positive[0].verification_note, "not enough context")

    def test_merge_adjacent_findings_and_aggregate_events(self):
        findings = [
            _finding("f1", "001.txt", ["P001"]),
            _finding("f2", "001.txt", ["P002"]),
            _finding("f3", "002.txt", ["P001"], confidence=0.7),
        ]

        merged = merge_adjacent_findings(findings)
        events = aggregate_findings_into_events(merged)

        self.assertEqual(len(merged), 2)
        self.assertEqual(merged[0].paragraph_ids, ["P001", "P002"])
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].related_chapters, ["001.txt", "002.txt"])
        self.assertEqual(events[0].max_confidence, 0.9)

    def test_scan_state_tracks_resume_compatibility(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_snapshot = TriggerScanConfig().to_dict()
            store = ScanStateStore(tmpdir, "task-1")
            state = store.create(config_snapshot, "profile-v1")
            state = store.mark_chapter_complete("001.txt")

            pending = ScanStateStore.pending_chapters(
                ["001.txt", "002.txt"],
                state,
                config_snapshot=config_snapshot,
                profile_version="profile-v1",
            )
            incompatible = ScanStateStore.pending_chapters(
                ["001.txt", "002.txt"],
                state,
                config_snapshot={**config_snapshot, "precise_chapter_batch_size": 7},
                profile_version="profile-v1",
            )

            self.assertEqual(pending, ["002.txt"])
            self.assertEqual(incompatible, ["001.txt", "002.txt"])

    def test_invalid_model_json_raises_clear_error(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            chapter = Path(tmpdir) / "001.txt"
            chapter.write_text("Title\nFirst paragraph.", encoding="utf-8")
            chapter_index = build_chapter_paragraph_index(chapter)
            with self.assertRaises(TriggerScanJsonError):
                parse_precise_scan_findings(
                    "not json",
                    chapter_index=chapter_index,
                    profile=_profile(),
                    config=TriggerScanConfig(),
                )


if __name__ == "__main__":
    unittest.main()
