import unittest

from webui_backend.trigger_models import (
    BUILTIN_RULE_GROUPS,
    BUILTIN_RULES,
    ScanFinding,
    ScanRange,
    ScanReport,
    SkipList,
    SkipListItem,
    TriggerProfile,
    TriggerRule,
    TriggerScanConfig,
    builtin_trigger_profile,
    default_trigger_scan_config,
)


class TriggerModelTests(unittest.TestCase):
    def test_trigger_rule_round_trip_and_validation(self):
        rule = TriggerRule.from_dict(
            {
                "id": "rule_abuse_romance",
                "name": "感情线虐恋",
                "group_id": "group_romance",
                "matching_policy": "explicit_or_strongly_implied",
                "severity_threshold": 2,
                "examples": ["长期精神虐待"],
                "negative_examples": ["普通争吵"],
            }
        )

        stored = rule.to_dict()

        self.assertEqual(stored["id"], "rule_abuse_romance")
        self.assertEqual(stored["matching_policy"], "explicit_or_strongly_implied")
        self.assertEqual(stored["severity_threshold"], 2)

    def test_trigger_rule_rejects_invalid_matching_policy(self):
        with self.assertRaisesRegex(ValueError, "matching_policy"):
            TriggerRule.from_dict(
                {
                    "id": "rule_bad",
                    "name": "坏规则",
                    "group_id": "group_romance",
                    "matching_policy": "anything",
                }
            )

    def test_trigger_rule_rejects_invalid_severity_threshold(self):
        rule = TriggerRule(
            id="rule_bad",
            name="坏规则",
            group_id="group_romance",
            severity_threshold=6,
        )

        with self.assertRaisesRegex(ValueError, "severity_threshold"):
            rule.to_dict()

    def test_trigger_profile_requires_existing_rule_group(self):
        profile = TriggerProfile.from_dict(
            {
                "id": "profile_1",
                "name": "测试档案",
                "rule_groups": [{"id": "group_a", "name": "A"}],
                "rules": [
                    {
                        "id": "rule_1",
                        "name": "规则 1",
                        "group_id": "missing",
                    }
                ],
            }
        )

        with self.assertRaisesRegex(ValueError, "group_id"):
            profile.to_dict()

    def test_default_trigger_scan_config_values(self):
        hybrid = default_trigger_scan_config()
        precise = default_trigger_scan_config("precise")

        self.assertEqual(hybrid.scan_mode, "hybrid")
        self.assertTrue(hybrid.verification_enabled)
        self.assertEqual(hybrid.min_confidence, 0.65)
        self.assertEqual(hybrid.coarse_batch_size, 3)
        self.assertEqual(hybrid.max_quote_chars, 80)
        self.assertFalse(precise.verification_enabled)

    def test_trigger_scan_config_validation(self):
        TriggerScanConfig.from_dict(
            {
                "scan_mode": "hybrid",
                "scan_range": {"start": 5, "end": 10},
                "min_confidence": 0.75,
                "coarse_batch_size": 2,
                "max_quote_chars": 60,
            }
        ).to_dict()

        invalid_cases = [
            ({"scan_mode": "fast"}, "scan_mode"),
            ({"min_confidence": 1.5}, "min_confidence"),
            ({"coarse_batch_size": 0}, "coarse_batch_size"),
            ({"max_quote_chars": 0}, "max_quote_chars"),
            ({"scan_range": {"start": 10, "end": 2}}, "scan range end"),
        ]
        for payload, message in invalid_cases:
            with self.subTest(payload=payload):
                with self.assertRaisesRegex(ValueError, message):
                    TriggerScanConfig.from_dict(payload).to_dict()

    def test_scan_finding_validates_required_fields(self):
        finding = ScanFinding.from_dict(
            {
                "finding_id": "f_1",
                "rule_id": "rule_character_death",
                "rule_name": "主要角色死亡",
                "chapter_file": "第001章.txt",
                "paragraph_ids": ["P001"],
                "severity": 4,
                "confidence": 0.9,
            }
        )

        self.assertEqual(finding.to_dict()["review_status"], "unreviewed")

        with self.assertRaisesRegex(ValueError, "paragraph_ids"):
            ScanFinding.from_dict(
                {
                    "finding_id": "f_2",
                    "rule_id": "rule_character_death",
                    "rule_name": "主要角色死亡",
                    "chapter_file": "第001章.txt",
                    "severity": 4,
                    "confidence": 0.9,
                }
            ).to_dict()

    def test_scan_report_and_skip_list_round_trip(self):
        report = ScanReport.from_dict(
            {
                "report_id": "rpt_1",
                "project_slug": "novel",
                "profile_id": "profile_1",
                "profile_name": "测试档案",
                "scan_mode": "hybrid",
                "scan_range": {"start": 1, "end": 5},
                "scan_config": {"scan_mode": "hybrid"},
                "status": "completed",
                "findings": [
                    {
                        "finding_id": "f_1",
                        "rule_id": "rule_ntr",
                        "rule_name": "NTR / 感情背叛",
                        "chapter_file": "第001章.txt",
                        "paragraph_ids": ["P001"],
                        "severity": 3,
                        "confidence": 0.8,
                    }
                ],
            }
        )
        skip_list = SkipList(
            skip_list_id="skip_1",
            project_slug="novel",
            items=[
                SkipListItem(
                    chapter_file="第001章.txt",
                    paragraph_range="P001-P002",
                    rule_name="NTR / 感情背叛",
                    severity=3,
                    source_finding_id="f_1",
                )
            ],
        )

        self.assertEqual(report.to_dict()["findings"][0]["finding_id"], "f_1")
        self.assertEqual(skip_list.to_dict()["items"][0]["source_finding_id"], "f_1")

    def test_builtin_trigger_profile_contains_expected_groups_and_rules(self):
        profile = builtin_trigger_profile(timestamp=123)
        stored = profile.to_dict()

        self.assertEqual(len(BUILTIN_RULE_GROUPS), 5)
        self.assertEqual(len(BUILTIN_RULES), 16)
        self.assertEqual(len(stored["rule_groups"]), 5)
        self.assertEqual(len(stored["rules"]), 16)
        self.assertEqual(stored["created_at"], 123)
        self.assertIn("感情类", {group["name"] for group in stored["rule_groups"]})
        self.assertIn("主要角色死亡", {rule["name"] for rule in stored["rules"]})

    def test_scan_range_rejects_invalid_bounds(self):
        with self.assertRaisesRegex(ValueError, "start"):
            ScanRange(start=0).to_dict()

        with self.assertRaisesRegex(ValueError, "end"):
            ScanRange(start=3, end=2).to_dict()


if __name__ == "__main__":
    unittest.main()
