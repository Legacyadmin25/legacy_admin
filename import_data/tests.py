# import_data/tests.py
"""Tests for the Policy Amendment import pipeline."""
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
from .models import PolicyAmendmentImport, PolicyAmendmentRowLog

User = get_user_model()

UPLOAD_URL = 'import_data:policy_amendments_import'
PREVIEW_URL = 'import_data:policy_amendments_preview'


def _make_member():
    return Member.objects.create(
        first_name='Test', last_name='User',
        gender='Male', date_of_birth=date(1985, 1, 1),
        phone_number='0710001111',
    )


def _make_scheme():
    bank = Bank.objects.create(name='FNB', branch_code='250655')
    branch = Branch.objects.create(bank=bank, name='HQ', location='JHB')
    return Scheme.objects.create(
        branch=branch, name='Test Scheme', registration_no='REG1',
        fsp_number='FSP1', email='s@s.com', phone='0710000000', account_no='0001',
    )


def _make_policy(member=None, scheme=None, membership_number='M123'):
    if member is None:
        member = _make_member()
    if scheme is None:
        scheme = _make_scheme()
    return Policy.objects.create(
        member=member, scheme=scheme,
        membership_number=membership_number,
        payment_method='DEBIT_ORDER',
        start_date=date.today(),
    )


class PolicyAmendmentImportTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_superuser(
            username='amendadmin', password='pass', email='a@a.com'
        )
        cls.policy = _make_policy(membership_number='M123')

    def setUp(self):
        self.client = Client()
        self.client.login(username='amendadmin', password='pass')

    def _csv(self, rows, fields=None):
        fields = fields or ['membership_number', 'lapse_warning']
        buf = StringIO()
        writer = csv.DictWriter(buf, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
        return SimpleUploadedFile(
            'amendments.csv',
            buf.getvalue().encode('utf-8'),
            content_type='text/csv',
        )

    def test_upload_get(self):
        response = self.client.get(reverse(UPLOAD_URL))
        self.assertEqual(response.status_code, 200)

    def test_upload_post_redirects_to_preview(self):
        csv_file = self._csv([
            {'membership_number': 'M123', 'lapse_warning': 'note1'},
            {'membership_number': 'XX',   'lapse_warning': 'note2'},
        ])
        response = self.client.post(
            reverse(UPLOAD_URL), {'csv_file': csv_file}
        )
        batch = PolicyAmendmentImport.objects.first()
        self.assertIsNotNone(batch)
        self.assertRedirects(
            response, reverse(PREVIEW_URL, args=[batch.pk])
        )

    def test_preview_shows_found_and_not_found(self):
        csv_file = self._csv([
            {'membership_number': 'M123', 'lapse_warning': 'note'},
            {'membership_number': 'XX',   'lapse_warning': 'note'},
        ])
        self.client.post(reverse(UPLOAD_URL), {'csv_file': csv_file})
        batch = PolicyAmendmentImport.objects.first()
        response = self.client.get(reverse(PREVIEW_URL, args=[batch.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'M123')
        self.assertContains(response, 'Not Found')

    def test_apply_updates_policy_field(self):
        """Applying amendments with a valid Policy field should update it."""
        csv_file = self._csv([
            {'membership_number': 'M123', 'lapse_warning': 'amended'}
        ])
        self.client.post(reverse(UPLOAD_URL), {'csv_file': csv_file})
        batch = PolicyAmendmentImport.objects.first()
        self.client.post(reverse(PREVIEW_URL, args=[batch.pk]))

        self.policy.refresh_from_db()
        self.assertEqual(self.policy.lapse_warning, 'amended')

        log = PolicyAmendmentRowLog.objects.get(import_batch=batch)
        self.assertEqual(log.status, 'success')
        self.assertIn('lapse_warning', log.changes)

    def test_apply_not_found_logged(self):
        """Rows with unknown membership_number should be logged as not_found."""
        csv_file = self._csv([
            {'membership_number': 'ZZZZ', 'lapse_warning': 'note'}
        ])
        self.client.post(reverse(UPLOAD_URL), {'csv_file': csv_file})
        batch = PolicyAmendmentImport.objects.first()
        self.client.post(reverse(PREVIEW_URL, args=[batch.pk]))

        log = PolicyAmendmentRowLog.objects.get(import_batch=batch)
        self.assertEqual(log.status, 'not_found')
