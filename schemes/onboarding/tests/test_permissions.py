from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.models import User
from branches.models import Bank, Branch
from schemes.onboarding.models import BranchSchemeOnboarding


@override_settings(ROOT_URLCONF='schemes.onboarding.tests.test_urls')
class PermissionBoundaryTests(TestCase):
    def setUp(self):
        bank = Bank.objects.create(name='Bank A', branch_code='123456')
        self.branch = Branch.objects.create(name='Branch A', bank=bank)
        self.user = User.objects.create_user(username='plain', password='pass1234')
        self.onboarding = BranchSchemeOnboarding.create_with_token(branch=self.branch)
        self.onboarding.submit(submitted_by='owner@example.com')

    def test_anonymous_user_cannot_access_branch_review(self):
        url = reverse('scheme_onboarding:branch_list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)

    def test_logged_user_without_branch_cannot_review(self):
        self.client.login(username='plain', password='pass1234')
        detail = reverse('scheme_onboarding:branch_detail', kwargs={'pk': self.onboarding.pk})
        response = self.client.get(detail)
        self.assertEqual(response.status_code, 403)
