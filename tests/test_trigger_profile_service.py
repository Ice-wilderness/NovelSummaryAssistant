import tempfile
import unittest

from webui_backend.trigger_profile_service import TriggerProfileService


class TriggerProfileServiceTests(unittest.TestCase):
    def test_list_profiles_initializes_default_profile(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            service = TriggerProfileService(runtime_base_path=tmpdir)

            profiles = service.list_profiles()

            self.assertTrue(service.profile_dir.is_dir())
            self.assertEqual(len(profiles), 1)
            self.assertEqual(profiles[0].id, "profile_builtin_default")
            self.assertEqual(len(profiles[0].rule_groups), 5)
            self.assertEqual(len(profiles[0].rules), 16)

    def test_create_update_duplicate_and_delete_profile(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            service = TriggerProfileService(runtime_base_path=tmpdir)

            created = service.create_profile({"name": "感情线档案", "description": "只看感情线"})
            updated = service.update_profile(created.id, {"name": "新版档案"})
            duplicate = service.duplicate_profile(updated.id, {"name": "复制档案"})
            service.delete_profile(updated.id)
            remaining_ids = {profile.id for profile in service.list_profiles()}

            self.assertEqual(created.name, "感情线档案")
            self.assertEqual(updated.name, "新版档案")
            self.assertEqual(duplicate.name, "复制档案")
            self.assertNotEqual(duplicate.id, updated.id)
            self.assertNotIn(updated.id, remaining_ids)
            self.assertIn(duplicate.id, remaining_ids)

    def test_rule_group_guarded_delete(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            service = TriggerProfileService(runtime_base_path=tmpdir)
            profile = service.create_profile({"name": "空档案", "from_template": False})
            profile = service.add_rule_group(profile.id, {"name": "感情类"})
            group_id = profile.rule_groups[0].id
            profile = service.add_rule(
                profile.id,
                {
                    "name": "感情线虐恋",
                    "group_id": group_id,
                    "severity_threshold": 2,
                },
            )

            with self.assertRaisesRegex(ValueError, "still contains rules"):
                service.delete_rule_group(profile.id, group_id)

            rule_id = profile.rules[0].id
            profile = service.delete_rule(profile.id, rule_id)
            profile = service.delete_rule_group(profile.id, group_id)

            self.assertEqual(profile.rule_groups, [])
            self.assertEqual(profile.rules, [])

    def test_rule_update_moves_between_groups_and_updates_version(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            service = TriggerProfileService(runtime_base_path=tmpdir)
            profile = service.create_profile({"name": "空档案", "from_template": False})
            profile = service.add_rule_group(profile.id, {"name": "A"})
            profile = service.add_rule_group(profile.id, {"name": "B"})
            group_a = profile.rule_groups[0].id
            group_b = profile.rule_groups[1].id
            profile = service.add_rule(profile.id, {"name": "规则", "group_id": group_a})
            rule_id = profile.rules[0].id
            version_before = service.profile_version(profile)

            updated = service.update_rule(
                profile.id,
                rule_id,
                {"group_id": group_b, "enabled": False},
            )
            snapshot = service.profile_snapshot(profile.id)

            self.assertFalse(updated.rules[0].enabled)
            self.assertNotIn(rule_id, updated.rule_groups[0].rules)
            self.assertIn(rule_id, updated.rule_groups[1].rules)
            self.assertNotEqual(version_before, service.profile_version(updated))
            self.assertEqual(snapshot["version"], service.profile_version(updated))

    def test_rejects_invalid_profile_id_path(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            service = TriggerProfileService(runtime_base_path=tmpdir)

            with self.assertRaisesRegex(ValueError, "invalid characters"):
                service.load_profile("../secret")


if __name__ == "__main__":
    unittest.main()
