### import_data/tests.py
from io import StringIO
import csv
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from members.models import Policy, Member
from .models import PolicyAmendmentImport, PolicyAmendmentRowLog

User = get_user_model()

class PolicyAmendmentImportTests(TestCase):
    def setUp(self):
        # create test user and policy
        self.user = User.objects.create_user(username='tester', password='pass')
        self.policy = Policy.objects.create(
            membership_number='M123',
            # add required policy fields here:
        )
        self.client = Client()
        self.client.login(username='tester', password='pass')

    def create_csv(self, rows):
        buffer = StringIO()
        writer = csv.DictWriter(buffer, fieldnames=['membership_number', 'contact_number', 'address'])
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
        buffer.seek(0)
        return buffer

    def test_upload_and_preview(self):
        url = reverse('import_data:policy_amendments')
        csv_file = self.create_csv([
            {'membership_number': 'M123', 'contact_number': '0812345678', 'address': 'New Address'},
            {'membership_number': 'XX', 'contact_number': '000', 'address': 'No Policy'}
        ])
        response = self.client.post(url, {'file': csv_file}, format='multipart')
        batch = PolicyAmendmentImport.objects.first()
        self.assertRedirects(response, reverse('import_data:policy_amendments_preview', args=[batch.pk]))

        preview_url = reverse('import_data:policy_amendments_preview', args=[batch.pk])
        response = self.client.get(preview_url)
        self.assertContains(response, 'M123')
        self.assertContains(response, 'Not Found')

    def test_apply_amendments(self):
        # upload
        url = reverse('import_data:policy_amendments')
        csv_file = self.create_csv([
            {'membership_number': 'M123', 'contact_number': '0812345678', 'address': 'New Address'}
        ])
        resp = self.client.post(url, {'file': csv_file}, format='multipart')
        batch = PolicyAmendmentImport.objects.first()
        # apply
        preview_url = reverse('import_data:policy_amendments_preview', args=[batch.pk])
        resp = self.client.post(preview_url)
        # reload policy
        self.policy.refresh_from_db()
        self.assertEqual(self.policy.contact_number, '0812345678')
        self.assertEqual(self.policy.address, 'New Address')
        # log entry
        log = PolicyAmendmentRowLog.objects.get(import_batch=batch)
        self.assertEqual(log.status, 'success')
        self.assertIn('address', log.changes)
        self.assertIn('contact_number', log.changes)

### import_data/tests_lapsed.py
from io import StringIO
import csv
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from members.models import Policy
from .models import LapsedPolicyReactivationImport, LapsedPolicyReactivationRowLog

User = get_user_model()

class LapsedPolicyReactivationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='tester', password='pass')
        self.policy_active = Policy.objects.create(membership_number='M1', is_active=True)
        self.policy_lapsed = Policy.objects.create(membership_number='M2', is_active=False, cover_date=None)
        self.client = Client()
        self.client.login(username='tester', password='pass')

    def create_csv(self, rows):
        buffer = StringIO()
        writer = csv.DictWriter(buffer, fieldnames=['membership_number', 'new_start_date'])
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
        buffer.seek(0)
        return buffer

    def test_preview_and_apply(self):
        url = reverse('import_data:policy_reactivations')
        csv_file = self.create_csv([
            {'membership_number': 'M2', 'new_start_date': '2025-05-01'},
            {'membership_number': 'MX', 'new_start_date': '2025-05-01'}
        ])
        resp = self.client.post(url, {'file': csv_file}, format='multipart')
        batch = LapsedPolicyReactivationImport.objects.first()
        preview_url = reverse('import_data:policy_reactivations_preview', args=[batch.pk])
        resp = self.client.get(preview_url)
        self.assertContains(resp, 'M2')
        self.assertContains(resp, 'Not Found')
        # apply
        resp = self.client.post(preview_url)
        self.policy_lapsed.refresh_from_db()
        self.assertTrue(self.policy_lapsed.is_active)
        self.assertEqual(str(self.policy_lapsed.cover_date), '2025-05-01')
        logs = LapsedPolicyReactivationRowLog.objects.filter(import_batch=batch)
        self.assertEqual(logs.count(), 2)