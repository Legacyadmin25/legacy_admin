# import_data/tests_lapsed.py
"""Tests for the Lapsed Policy Reactivation import pipeline."""
from datetime import date
from io import StringIO
import csv

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse

from branches.models import Bank, Branch
from members.models import Member, Policy
from schemes.models import Scheme
from .models import LapsedPolicyReactivationImport, LapsedPolicyReactivationRowLog

User = get_user_model()

UPLOAD_URL = 'import_data:lapsed_policy_reactivation_import'
PREVIEW_URL = 'import_data:lapsed_policy_reactivation_preview'


def _make_policy(membership_number, cover_date=None):
    bank = Bank.objects.create(name=f'Bank-{membership_number}', branch_code='250655')
    branch = Branch.objects.create(bank=bank, name=f'Br-{membership_number}', location='JHB')
    scheme = Scheme.objects.create(
        branch=branch, name=f'Scheme-{membership_number}',
        registration_no=f'R{membership_number}', fsp_number=f'F{membership_number}',
        email='s@s.com', phone='0710000000', account_no='0001',
    )
    member = Member.objects.create(
        first_name='Test', last_name='User',
        gender='Male', date_of_birth=date(1985, 1, 1),
        phone_number='0710001111',
    )
    return Policy.objects.create(
        member=member, scheme=scheme,
        membership_number=membership_number,
        payment_method='DEBIT_ORDER',
        start_date=date(2023, 1, 1),
        cover_date=cover_date,
    )


class LapsedPolicyReactivationTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_superuser(
            username='reactadmin', password='pass', email='r@r.com'
        )
        # policy_lapsed has no cover_date (represents a lapsed/pending policy)
        cls.policy_lapsed = _make_policy('M2', cover_date=None)

    def setUp(self):
        self.client = Client()
        self.client.login(username='reactadmin', password='pass')

    def _csv(self, rows):
        buf = StringIO()
        writer = csv.DictWriter(buf, fieldnames=['membership_number', 'new_start_date'])
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
        return SimpleUploadedFile(
            'reactivations.csv',
            buf.getvalue().encode('utf-8'),
            content_type='text/csv',
        )

    def test_upload_get(self):
        response = self.client.get(reverse(UPLOAD_URL))
        self.assertEqual(response.status_code, 200)

    def test_upload_post_redirects_to_preview(self):
        csv_file = self._csv([{'membership_number': 'M2', 'new_start_date': '2025-05-01'}])
        response = self.client.post(reverse(UPLOAD_URL), {'csv_file': csv_file})
        batch = LapsedPolicyReactivationImport.objects.first()
        self.assertIsNotNone(batch)
        self.assertRedirects(response, reverse(PREVIEW_URL, args=[batch.pk]))

    def test_preview_shows_found_and_not_found(self):
        csv_file = self._csv([
            {'membership_number': 'M2',  'new_start_date': '2025-05-01'},
            {'membership_number': 'MX',  'new_start_date': '2025-05-01'},
        ])
        self.client.post(reverse(UPLOAD_URL), {'csv_file': csv_file})
        batch = LapsedPolicyReactivationImport.objects.first()
        response = self.client.get(reverse(PREVIEW_URL, args=[batch.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'M2')
        self.assertContains(response, 'Not Found')

    def test_apply_sets_cover_date(self):
        """Applying reactivation should set the policy's cover_date."""
        csv_file = self._csv([{'membership_number': 'M2', 'new_start_date': '2025-06-01'}])
        self.client.post(reverse(UPLOAD_URL), {'csv_file': csv_file})
        batch = LapsedPolicyReactivationImport.objects.first()
        self.client.post(reverse(PREVIEW_URL, args=[batch.pk]))

        self.policy_lapsed.refresh_from_db()
        self.assertEqual(str(self.policy_lapsed.cover_date), '2025-06-01')

    def test_apply_logs_success_and_not_found(self):
        csv_file = self._csv([
            {'membership_number': 'M2',  'new_start_date': '2025-06-01'},
            {'membership_number': 'ZZZZ', 'new_start_date': '2025-06-01'},
        ])
        self.client.post(reverse(UPLOAD_URL), {'csv_file': csv_file})
        batch = LapsedPolicyReactivationImport.objects.first()
        self.client.post(reverse(PREVIEW_URL, args=[batch.pk]))

        logs = LapsedPolicyReactivationRowLog.objects.filter(import_batch=batch)
        self.assertEqual(logs.count(), 2)
        statuses = set(logs.values_list('status', flat=True))
        self.assertIn('success', statuses)
        self.assertIn('not_found', statuses)

    def test_apply_invalid_date_logs_error(self):
        csv_file = self._csv([{'membership_number': 'M2', 'new_start_date': 'bad-date'}])
        self.client.post(reverse(UPLOAD_URL), {'csv_file': csv_file})
        batch = LapsedPolicyReactivationImport.objects.first()
        self.client.post(reverse(PREVIEW_URL, args=[batch.pk]))

        log = LapsedPolicyReactivationRowLog.objects.get(import_batch=batch)
        self.assertEqual(log.status, 'error')
