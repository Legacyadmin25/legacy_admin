from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.models import User
from branches.models import Bank, Branch
from schemes.onboarding.models import BranchSchemeOnboarding


@override_settings(ROOT_URLCONF='schemes.onboarding.tests.test_urls')
class SchemeOnboardingWorkflowTests(TestCase):
    def setUp(self):
        bank = Bank.objects.create(name='Bank A', branch_code='123456')
        self.branch = Branch.objects.create(name='Branch A', bank=bank)
        self.onboarding = BranchSchemeOnboarding.create_with_token(branch=self.branch)

    def test_full_workflow_submit(self):
        start = reverse('scheme_onboarding:start', kwargs={'token': self.onboarding.onboarding_token})
        self.assertEqual(self.client.get(start).status_code, 200)
        self.client.post(start)

        step1 = reverse('scheme_onboarding:step1', kwargs={'token': self.onboarding.onboarding_token})
        response = self.client.post(step1, {
            'company_name': 'Scheme One',
            'registration_no': 'REG-001',
            'fsp_number': 'FSP-001',
            'email': 'owner@example.com',
            'phone': '0820000000',
        })
        self.assertEqual(response.status_code, 302)

        step2 = reverse('scheme_onboarding:step2', kwargs={'token': self.onboarding.onboarding_token})
        response = self.client.post(step2, {
            'bank_account_no': '123456789',
            'debit_order_no': 'DEBIT-001',
            'account_type': 'Savings',
        })
        self.assertEqual(response.status_code, 302)

        submit = reverse('scheme_onboarding:submit', kwargs={'token': self.onboarding.onboarding_token})
        response = self.client.post(submit)
        self.assertEqual(response.status_code, 302)

        self.onboarding.refresh_from_db()
        self.assertEqual(self.onboarding.status, BranchSchemeOnboarding.STATUS_SUBMITTED)


@override_settings(ROOT_URLCONF='schemes.onboarding.tests.test_urls')
class BranchReviewPermissionTests(TestCase):
    def setUp(self):
        bank1 = Bank.objects.create(name='Bank A', branch_code='123456')
        bank2 = Bank.objects.create(name='Bank B', branch_code='654321')
        self.branch1 = Branch.objects.create(name='Branch A', bank=bank1)
        self.branch2 = Branch.objects.create(name='Branch B', bank=bank2)

        self.reviewer = User.objects.create_user(username='reviewer', password='pass1234', branch=self.branch1)
        self.other_user = User.objects.create_user(username='other', password='pass1234', branch=self.branch2)

        self.onboarding = BranchSchemeOnboarding.create_with_token(branch=self.branch1)
        self.onboarding.submit(submitted_by='owner@example.com')

    def test_branch_owner_sees_only_own_branch(self):
        self.client.login(username='reviewer', password='pass1234')
        list_url = reverse('scheme_onboarding:branch_list')
        response = self.client.get(list_url)
        self.assertContains(response, 'owner@example.com')

        self.client.logout()
        self.client.login(username='other', password='pass1234')
        response = self.client.get(list_url)
        self.assertNotContains(response, 'owner@example.com')

    def test_only_correct_branch_can_approve(self):
        approve = reverse('scheme_onboarding:branch_approve', kwargs={'pk': self.onboarding.pk})

        self.client.login(username='other', password='pass1234')
        response = self.client.post(approve)
        self.assertEqual(response.status_code, 403)

        self.client.logout()
        self.client.login(username='reviewer', password='pass1234')
        response = self.client.post(approve)
        self.assertEqual(response.status_code, 302)
        self.onboarding.refresh_from_db()
        self.assertEqual(self.onboarding.status, BranchSchemeOnboarding.STATUS_APPROVED)
