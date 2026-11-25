import unittest

from backend.main import _can_advance_stage


class OwnerStageGateTests(unittest.TestCase):
    def test_distribution_disabled_without_owner_does_not_advance(self):
        self.assertFalse(_can_advance_stage(True, ""))

    def test_no_eligible_owner_does_not_advance(self):
        self.assertFalse(_can_advance_stage(True, None))

    def test_assignment_failure_does_not_advance(self):
        self.assertFalse(_can_advance_stage(True, ""))

    def test_existing_or_new_owner_allows_advance(self):
        self.assertTrue(_can_advance_stage(True, 2602))

    def test_incomplete_requirements_block_even_with_owner(self):
        self.assertFalse(_can_advance_stage(False, 2602))


if __name__ == "__main__":
    unittest.main()
