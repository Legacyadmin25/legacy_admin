# import_data/tests_plan_import.py
"""
Tests for the bulk plan import pipeline.

Coverage:
  - parse_plan_import_file()   – pure parser, no DB required
  - PlanImportUploadView       – GET, invalid POST, file-error POST, success POST
  - PlanImportPreviewView      – GET (no session), GET (valid session), POST (confirm)
"""

from decimal import Decimal
from io import BytesIO

import openpyxl
from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse

from branches.models import Branch, Bank
from schemes.models import Plan, PlanTier, Scheme
from import_data.views.plan_import import parse_plan_import_file

User = get_user_model()


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _make_xlsx(plans=None, tiers=None, include_plan_setup=True, include_plan_creator=True):
    """
    Build an in-memory XLSX with the expected 2-sheet structure.

    plans  – list of dicts with keys: plan_name, description, main_premium,
             main_cover, main_uw_premium, main_uw_cover, main_age_from,
             main_age_to, waiting_period, lapse_period, underwriter,
             admin_fee, agent_commission, scheme_fee, manager_fee,
             office_fee, loyalty_programme, other_fees, cash_payout,
             service_fee, penalty_fee
    tiers  – list of dicts with keys: plan_name, user_type, age_from,
             age_to, cover_amount, premium, uw_cover, uw_premium, admin_fee
    """

    wb = openpyxl.Workbook()
    first = True

    if include_plan_setup:
        ws1 = wb.active if first else wb.create_sheet()
        ws1.title = 'Plan Setup'
        first = False
        # Header row (col indices must match _PLAN_SETUP_COLS in plan_import.py)
        header = [None] * 26
        header[0] = 'Plan Name'
        header[1] = 'Description'
        header[2] = 'Main Premium'
        header[3] = 'Main Cover'
        header[4] = 'Main UW Premium'
        header[5] = 'Main UW Cover'
        header[6] = 'Age From'
        header[7] = 'Age To'
        header[8] = 'Waiting Period'
        header[9] = 'Lapse Period'
        header[10] = 'Max Dependants'
        header[11] = 'Underwriter'
        header[16] = 'Admin Fee'
        header[17] = 'Agent Commission'
        header[18] = 'Scheme Fee'
        header[19] = 'Manager Fee'
        header[20] = 'Office Fee'
        header[21] = 'Loyalty Programme'
        header[22] = 'Other Fees'
        header[23] = 'Cash Payout'
        header[24] = 'Service Fee'
        header[25] = 'Penalty Fee'
        ws1.append(header)

        for p in (plans or []):
            row = [None] * 26
            row[0] = p.get('plan_name', '')
            row[1] = p.get('description', '')
            row[2] = p.get('main_premium', 0)
            row[3] = p.get('main_cover', 0)
            row[4] = p.get('main_uw_premium', 0)
            row[5] = p.get('main_uw_cover', 0)
            row[6] = p.get('main_age_from', 0)
            row[7] = p.get('main_age_to', 100)
            row[8] = p.get('waiting_period', 6)
            row[9] = p.get('lapse_period', 2)
            row[10] = None  # max dependants (informational)
            row[11] = p.get('underwriter', '')
            row[16] = p.get('admin_fee', 0)
            row[17] = p.get('agent_commission', 0)
            row[18] = p.get('scheme_fee', 0)
            row[19] = p.get('manager_fee', 0)
            row[20] = p.get('office_fee', 0)
            row[21] = p.get('loyalty_programme', 0)
            row[22] = p.get('other_fees', 0)
            row[23] = p.get('cash_payout', 0)
            row[24] = p.get('service_fee', 0)
            row[25] = p.get('penalty_fee', 0)
            ws1.append(row)
    else:
        # Create a dummy worksheet so the workbook is not empty
        ws_dummy = wb.active
        ws_dummy.title = 'Dummy'

    if include_plan_creator:
        ws2 = wb.create_sheet('Plan Creator') if not first else wb.active
        if first:
            ws2.title = 'Plan Creator'
        # Header row (col indices must match _TIER_COLS in plan_import.py)
        ws2.append(['Plan Name', 'User Type', 'Age From', 'Age To',
                    'Cover Amount', 'Premium', 'UW Cover', 'UW Premium', 'Admin Fee'])
        for t in (tiers or []):
            ws2.append([
                t.get('plan_name', ''),
                t.get('user_type', ''),
                t.get('age_from', 0),
                t.get('age_to', 100),
                t.get('cover_amount', 0),
                t.get('premium', 0),
                t.get('uw_cover', 0),
                t.get('uw_premium', 0),
                t.get('admin_fee', 0),
            ])

    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf


def _sample_plan():
    return {
        'plan_name': 'Silver Plan',
        'description': 'Test silver plan',
        'main_premium': '150.00',
        'main_cover': '20000.00',
        'main_uw_premium': '100.00',
        'main_uw_cover': '15000.00',
        'main_age_from': '18',
        'main_age_to': '64',
        'waiting_period': '6',
        'lapse_period': '2',
        'underwriter': 'TestUW',
        'admin_fee': '10.00',
        'agent_commission': '5.00',
        'scheme_fee': '3.00',
        'manager_fee': '2.00',
        'office_fee': '1.00',
        'loyalty_programme': '0.00',
        'other_fees': '0.00',
        'cash_payout': '0.00',
        'service_fee': '0.00',
        'penalty_fee': '0.00',
    }


def _sample_tier(plan_name='Silver Plan', user_type='Spouse'):
    return {
        'plan_name': plan_name,
        'user_type': user_type,
        'age_from': 18,
        'age_to': 64,
        'cover_amount': 10000,
        'premium': 75,
        'uw_cover': 8000,
        'uw_premium': 50,
        'admin_fee': 5,
    }


# ─── Parser unit tests ────────────────────────────────────────────────────────

class ParsePlanImportFileTests(TestCase):
    """Tests for parse_plan_import_file() — no DB required."""

    def test_parse_valid_single_plan_no_tiers(self):
        buf = _make_xlsx(plans=[_sample_plan()], tiers=[])
        result = parse_plan_import_file(buf)
        self.assertEqual(len(result['errors']), 0)
        self.assertEqual(len(result['plans']), 1)
        plan = result['plans'][0]
        self.assertEqual(plan['plan_name'], 'Silver Plan')
        self.assertEqual(plan['main_premium'], Decimal('150.0000'))
        self.assertEqual(plan['waiting_period'], 6)
        self.assertEqual(len(result['tiers']), 0)

    def test_parse_valid_plan_with_tiers(self):
        buf = _make_xlsx(
            plans=[_sample_plan()],
            tiers=[_sample_tier('Silver Plan', 'Spouse'),
                   _sample_tier('Silver Plan', 'Child')],
        )
        result = parse_plan_import_file(buf)
        self.assertEqual(len(result['errors']), 0)
        self.assertEqual(len(result['plans']), 1)
        self.assertEqual(len(result['tiers']), 2)
        types = {t['user_type'] for t in result['tiers']}
        self.assertIn('spouse', types)
        self.assertIn('child', types)

    def test_parse_multiple_plans(self):
        plans = [_sample_plan(), {**_sample_plan(), 'plan_name': 'Gold Plan'}]
        buf = _make_xlsx(plans=plans)
        result = parse_plan_import_file(buf)
        self.assertEqual(len(result['errors']), 0)
        self.assertEqual(len(result['plans']), 2)
        names = {p['plan_name'] for p in result['plans']}
        self.assertEqual(names, {'Silver Plan', 'Gold Plan'})

    def test_parse_missing_plan_setup_sheet(self):
        buf = _make_xlsx(plans=[], tiers=[], include_plan_setup=False)
        result = parse_plan_import_file(buf)
        self.assertTrue(any('Plan Setup' in str(e) for e in result['errors']))

    def test_parse_missing_plan_creator_sheet(self):
        buf = _make_xlsx(plans=[_sample_plan()], tiers=[], include_plan_creator=False)
        result = parse_plan_import_file(buf)
        self.assertTrue(any('Plan Creator' in str(e) for e in result['errors']))

    def test_parse_invalid_decimal_value(self):
        bad_plan = {**_sample_plan(), 'main_premium': 'NOT_A_NUMBER'}
        buf = _make_xlsx(plans=[bad_plan])
        result = parse_plan_import_file(buf)
        error_messages = [str(e) for e in result['errors']]
        self.assertTrue(any('main_premium' in msg for msg in error_messages))

    def test_parse_unknown_user_type(self):
        buf = _make_xlsx(
            plans=[_sample_plan()],
            tiers=[_sample_tier('Silver Plan', 'Goldfish')],
        )
        result = parse_plan_import_file(buf)
        error_messages = [str(e) for e in result['errors']]
        self.assertTrue(any('user_type' in msg or 'Goldfish' in msg for msg in error_messages))

    def test_parse_blank_plan_rows_skipped(self):
        """Rows with no plan_name should be silently ignored."""
        buf = _make_xlsx(plans=[_sample_plan()])
        # Manually append a blank row to the Plan Setup sheet
        wb = openpyxl.load_workbook(buf)
        ws = wb['Plan Setup']
        ws.append([None] * 26)
        out = BytesIO()
        wb.save(out)
        out.seek(0)
        result = parse_plan_import_file(out)
        self.assertEqual(len(result['plans']), 1)
        self.assertEqual(len(result['errors']), 0)

    def test_parse_unreadable_file(self):
        buf = BytesIO(b'this is not an xlsx file')
        result = parse_plan_import_file(buf)
        self.assertTrue(len(result['errors']) > 0)
        self.assertEqual(result['plans'], [])
        self.assertEqual(result['tiers'], [])

    def test_parse_user_type_case_insensitive(self):
        """User type matching should be case-insensitive ('SPOUSE' == 'spouse')."""
        tier = {**_sample_tier(), 'user_type': 'SPOUSE'}
        # Manually set user_type in sheet as upper-case
        buf = _make_xlsx(plans=[_sample_plan()], tiers=[tier])
        # Rewrite user_type cell directly
        wb = openpyxl.load_workbook(buf)
        ws = wb['Plan Creator']
        ws.cell(row=2, column=2).value = 'SPOUSE'
        out = BytesIO()
        wb.save(out)
        out.seek(0)
        result = parse_plan_import_file(out)
        self.assertEqual(len(result['tiers']), 1)
        self.assertEqual(result['tiers'][0]['user_type'], 'spouse')


# ─── View tests ───────────────────────────────────────────────────────────────

class PlanImportViewTestBase(TestCase):
    """Shared setup for upload/preview view tests."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_superuser(
            username='importadmin', password='pass', email='a@a.com'
        )
        bank = Bank.objects.create(name='FNB', branch_code='250655')
        branch = Branch.objects.create(bank=bank, name='HQ Branch', location='Joburg')
        cls.scheme = Scheme.objects.create(
            branch=branch,
            name='Funeral Scheme',
            registration_no='REG999',
            fsp_number='FSP999',
            email='scheme@test.com',
            phone='0710001234',
            account_no='0000000001',
        )

    def setUp(self):
        self.client = Client()
        self.client.login(username='importadmin', password='pass')


class PlanImportUploadViewTests(PlanImportViewTestBase):
    upload_url = None

    def setUp(self):
        super().setUp()
        self.upload_url = reverse('import_data:plan_import_upload')

    def test_get_renders_form(self):
        response = self.client.get(self.upload_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<form', msg_prefix='Expected a form on the page')

    def test_unauthenticated_redirects(self):
        self.client.logout()
        response = self.client.get(self.upload_url)
        self.assertEqual(response.status_code, 302)

    def test_post_no_file_invalid(self):
        response = self.client.post(self.upload_url, {
            'scheme': self.scheme.pk,
            'is_wholesale': False,
            'update_existing': False,
        })
        self.assertEqual(response.status_code, 200)  # re-rendered with errors

    def test_post_valid_file_redirects_to_preview(self):
        xlsx = _make_xlsx(plans=[_sample_plan()], tiers=[_sample_tier()])
        xlsx.name = 'plans.xlsx'
        response = self.client.post(self.upload_url, {
            'scheme': self.scheme.pk,
            'import_file': xlsx,
            'is_wholesale': False,
            'update_existing': False,
        })
        self.assertRedirects(response, reverse('import_data:plan_import_preview'))

    def test_post_valid_file_stores_session(self):
        xlsx = _make_xlsx(plans=[_sample_plan()], tiers=[_sample_tier()])
        xlsx.name = 'plans.xlsx'
        self.client.post(self.upload_url, {
            'scheme': self.scheme.pk,
            'import_file': xlsx,
            'is_wholesale': False,
            'update_existing': False,
        })
        session = self.client.session
        self.assertIn('plan_import_preview', session)
        data = session['plan_import_preview']
        self.assertEqual(data['scheme_id'], self.scheme.pk)
        self.assertEqual(len(data['plans']), 1)
        self.assertEqual(data['plans'][0]['plan_name'], 'Silver Plan')

    def test_post_file_parse_errors_stays_on_page(self):
        """Fatal parse error (bad file) should stay on upload page, not redirect."""
        bad_file = BytesIO(b'not an xlsx')
        bad_file.name = 'bad.xlsx'
        response = self.client.post(self.upload_url, {
            'scheme': self.scheme.pk,
            'import_file': bad_file,
            'is_wholesale': False,
            'update_existing': False,
        })
        self.assertEqual(response.status_code, 200)


class PlanImportPreviewViewTests(PlanImportViewTestBase):
    preview_url = None

    def setUp(self):
        super().setUp()
        self.preview_url = reverse('import_data:plan_import_preview')
        self.upload_url = reverse('import_data:plan_import_upload')

    def _upload_and_get_session(self, plans=None, tiers=None, is_wholesale=False, update_existing=False):
        """Helper: do an upload POST and return the session preview data."""
        xlsx = _make_xlsx(plans=plans or [_sample_plan()], tiers=tiers or [])
        xlsx.name = 'plans.xlsx'
        self.client.post(self.upload_url, {
            'scheme': self.scheme.pk,
            'import_file': xlsx,
            'is_wholesale': is_wholesale,
            'update_existing': update_existing,
        })

    def test_get_no_session_redirects(self):
        response = self.client.get(self.preview_url)
        self.assertRedirects(response, self.upload_url)

    def test_get_with_session_renders_preview(self):
        self._upload_and_get_session()
        response = self.client.get(self.preview_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Silver Plan')

    def test_post_creates_plan_and_tier(self):
        self._upload_and_get_session(tiers=[_sample_tier('Silver Plan', 'Child')])
        self.client.post(self.preview_url)
        self.assertTrue(Plan.objects.filter(name='Silver Plan', scheme=self.scheme).exists())
        plan = Plan.objects.get(name='Silver Plan', scheme=self.scheme)
        self.assertTrue(PlanTier.objects.filter(plan=plan, user_type='child').exists())

    def test_post_creates_plan_values(self):
        self._upload_and_get_session()
        self.client.post(self.preview_url)
        plan = Plan.objects.get(name='Silver Plan', scheme=self.scheme)
        self.assertEqual(plan.main_premium, Decimal('150.0000'))
        self.assertEqual(plan.main_cover, Decimal('20000.0000'))
        self.assertEqual(plan.waiting_period, 6)
        self.assertFalse(plan.is_wholesale)

    def test_post_wholesale_flag(self):
        self._upload_and_get_session(is_wholesale=True)
        self.client.post(self.preview_url)
        plan = Plan.objects.get(name='Silver Plan', scheme=self.scheme)
        self.assertTrue(plan.is_wholesale)

    def test_post_update_existing(self):
        """update_existing=True should update the premium on a pre-existing plan."""
        Plan.objects.create(
            name='Silver Plan',
            scheme=self.scheme,
            premium=Decimal('1.00'),
            main_premium=Decimal('1.00'),
        )
        self._upload_and_get_session(update_existing=True)
        self.client.post(self.preview_url)
        plan = Plan.objects.get(name='Silver Plan', scheme=self.scheme)
        self.assertEqual(plan.main_premium, Decimal('150.0000'))

    def test_post_no_session_redirects(self):
        response = self.client.post(self.preview_url)
        self.assertRedirects(response, self.upload_url)

    def test_post_clears_session(self):
        self._upload_and_get_session()
        self.client.post(self.preview_url)
        session = self.client.session
        self.assertNotIn('plan_import_preview', session)

    def test_post_tier_for_unknown_plan_skipped(self):
        """Tiers referencing a plan not in the upload and not in DB should be skipped."""
        self._upload_and_get_session(
            plans=[_sample_plan()],
            tiers=[_sample_tier('Nonexistent Plan', 'Spouse')],
        )
        self.client.post(self.preview_url)
        self.assertEqual(PlanTier.objects.count(), 0)
