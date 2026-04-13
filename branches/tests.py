from django.test import TestCase
from django.contrib.auth.models import Group
from django.urls import reverse

from accounts.models import User
from .models import Branch, Bank
from schemes.onboarding.models import BranchSchemeOnboarding

class BranchSetupTestCase(TestCase):

    def setUp(self):
        bank = Bank.objects.create(name="Test Bank", branch_code="12345")
        Branch.objects.create(
            name="Test Branch",
            bank=bank,
            location="Test Location",
            code="BR001",
            phone="1234567890",
            cell="0987654321"
        )

    def test_branch_creation(self):
        branch = Branch.objects.get(name="Test Branch")
        self.assertEqual(branch.location, "Test Location")
        self.assertEqual(branch.phone, "1234567890")
        self.assertEqual(branch.cell, "0987654321")


class BranchOnboardingLinkTests(TestCase):
    def setUp(self):
        self.bank = Bank.objects.create(name='Bank A', branch_code='12345')
        self.branch = Branch.objects.create(name='Branch A', bank=self.bank)

        self.user = User.objects.create_user(username='branchowner', password='pass1234', branch=self.branch)
        group, _ = Group.objects.get_or_create(name='Branch Owner')
        self.user.groups.add(group)

    def test_create_onboarding_link_disabled_by_flag(self):
        self.client.login(username='branchowner', password='pass1234')
        url = reverse('branches:create_scheme_onboarding_link', kwargs={'branch_id': self.branch.id})
        response = self.client.post(url, {'expires_days': 7})
        self.assertEqual(response.status_code, 403)

    def test_create_onboarding_link_enabled(self):
        self.client.login(username='branchowner', password='pass1234')
        with self.settings(FEATURE_FLAGS={'SCHEME_SELF_ONBOARDING': True}):
            url = reverse('branches:create_scheme_onboarding_link', kwargs={'branch_id': self.branch.id})
            response = self.client.post(url, {'expires_days': 7})
            self.assertEqual(response.status_code, 302)
            self.assertTrue(
                BranchSchemeOnboarding.objects.filter(branch=self.branch).exists()
            )
