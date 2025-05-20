# import_data/tests_lapsed.py

from io import StringIO
import csv
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from members.models import Policy
from .models import LapsedPolicyReactivationImport, LapsedPolicyReactivationRowLog

User = get_user_model()

class LapsedPolicyReactivationTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        """Set up test user and policies once for all tests"""
        cls.user = User.objects.create_user(username='tester', password='pass')
        cls.policy_active = Policy.objects.create(membership_number='M1', is_active=True)
        cls.policy_lapsed = Policy.objects.create(membership_number='M2', is_active=False, cover_date=None)
        cls.client = Client()
        cls.client.login(username='tester', password='pass')

    def create_csv(self, rows):
        """Helper function to create CSV for tests"""
        buffer = StringIO()
        writer = csv.DictWriter(buffer, fieldnames=['membership_number', 'new_start_date'])
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
        buffer.seek(0)
        return buffer

    def test_preview_and_apply(self):
        """Test previewing and applying lapsed policy reactivation"""
        url = reverse('import_data:policy_reactivations')
        csv_file = self.create_csv([
            {'membership_number': 'M2', 'new_start_date': '2025-05-01'},
            {'membership_number': 'MX', 'new_start_date': '2025-05-01'}
        ])
        resp = self.client.post(url, {'file': csv_file}, format='multipart')
        batch = LapsedPolicyReactivationImport.objects.first()
        
        # Preview the reactivation process
        preview_url = reverse('import_data:policy_reactivations_preview', args=[batch.pk])
        resp = self.client.get(preview_url)
        self.assertContains(resp, 'M2')
        self.assertContains(resp, 'Not Found')
        
        # Apply reactivation
        resp = self.client.post(preview_url)
        
        # Check the reactivated policy
        self.policy_lapsed.refresh_from_db()
        self.assertTrue(self.policy_lapsed.is_active)
        self.assertEqual(str(self.policy_lapsed.cover_date), '2025-05-01')

        # Check the logs
        logs = LapsedPolicyReactivationRowLog.objects.filter(import_batch=batch)
        self.assertEqual(logs.count(), 2)
