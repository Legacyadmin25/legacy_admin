from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.models import User
from branches.models import Bank, Branch
from schemes.onboarding.models import BranchSchemeOnboarding


@override_settings(ROOT_URLCONF='schemes.onboarding.tests.test_urls')
class BranchReviewActionsTests(TestCase):
    def setUp(self):
        bank = Bank.objects.create(name='Bank A', branch_code='123456')
        self.branch = Branch.objects.create(name='Branch A', bank=bank)
        self.reviewer = User.objects.create_user(username='reviewer', password='pass1234', branch=self.branch)

        self.onboarding = BranchSchemeOnboarding.create_with_token(branch=self.branch)
        self.onboarding.submit(submitted_by='owner@example.com')

    def test_reopen_requires_notes(self):
        self.client.login(username='reviewer', password='pass1234')
        reopen = reverse('scheme_onboarding:branch_reopen', kwargs={'pk': self.onboarding.pk})
        response = self.client.post(reopen, {'action': 'reopen', 'notes': ''})
        self.assertEqual(response.status_code, 302)

        self.onboarding.refresh_from_db()
        self.assertEqual(self.onboarding.status, BranchSchemeOnboarding.STATUS_SUBMITTED)

    def test_reopen_with_notes(self):
        self.client.login(username='reviewer', password='pass1234')
        reopen = reverse('scheme_onboarding:branch_reopen', kwargs={'pk': self.onboarding.pk})
        response = self.client.post(reopen, {'action': 'reopen', 'notes': 'Please fix FSP number'})
        self.assertEqual(response.status_code, 302)

        self.onboarding.refresh_from_db()
        self.assertEqual(self.onboarding.status, BranchSchemeOnboarding.STATUS_REOPENED)
        self.assertEqual(self.onboarding.reopened_notes, 'Please fix FSP number')
