from django.test import TestCase
from django.utils import timezone

from branches.models import Bank, Branch
from schemes.onboarding.models import BranchSchemeOnboarding


class BranchSchemeOnboardingModelTests(TestCase):
    def setUp(self):
        bank = Bank.objects.create(name='Bank A', branch_code='123456')
        self.branch = Branch.objects.create(name='Branch A', bank=bank)

    def test_create_with_token_generates_valid_token(self):
        onboarding = BranchSchemeOnboarding.create_with_token(branch=self.branch)
        self.assertTrue(onboarding.onboarding_token)
        self.assertLessEqual(len(onboarding.onboarding_token), 48)
        self.assertTrue(onboarding.is_token_valid())

    def test_expired_token_is_invalid(self):
        onboarding = BranchSchemeOnboarding.create_with_token(
            branch=self.branch,
            expires_at=timezone.now() - timezone.timedelta(days=1),
        )
        self.assertFalse(onboarding.is_token_valid())

    def test_status_transitions(self):
        onboarding = BranchSchemeOnboarding.create_with_token(branch=self.branch)
        onboarding.submit(submitted_by='owner@example.com')
        self.assertEqual(onboarding.status, BranchSchemeOnboarding.STATUS_SUBMITTED)
        self.assertIsNotNone(onboarding.submitted_at)
        onboarding.reopen(reviewer=None, notes='Fix registration number')
        self.assertEqual(onboarding.status, BranchSchemeOnboarding.STATUS_REOPENED)
        self.assertEqual(onboarding.reopened_notes, 'Fix registration number')
