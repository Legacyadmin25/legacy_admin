"""
Tests for SchemeProduct model and the product builder views (Phase 2).
"""
from decimal import Decimal

from django.test import TestCase, override_settings
from django.urls import reverse

from branches.models import Bank, Branch
from schemes.models import Plan, Scheme
from schemes.onboarding.models import BranchSchemeOnboarding, SchemeProduct

FEATURE_ON = {'SCHEME_SELF_ONBOARDING': True}


def _make_branch():
    bank = Bank.objects.create(name='Test Bank', branch_code='632005')
    return Branch.objects.create(name='Test Branch', bank=bank)


def _make_scheme(branch):
    return Scheme.objects.create(
        branch=branch,
        name='Test Scheme',
        registration_no='REG001',
        fsp_number='FSP001',
        email='scheme@test.com',
        phone='0111234567',
        account_no='1234567890',
        debit_order_no='DO001',
    )


def _make_wholesale_plan(scheme):
    return Plan.objects.create(
        name='Wholesale Plan A',
        scheme=scheme,
        is_wholesale=True,
        premium=Decimal('250.00'),
        main_uw_cover=Decimal('20000.00'),
        main_uw_premium=Decimal('180.00'),
        admin_fee=Decimal('30.00'),
        scheme_fee=Decimal('20.00'),
    )


def _make_approved_onboarding(branch):
    from django.contrib.auth import get_user_model
    User = get_user_model()
    reviewer, _ = User.objects.get_or_create(username='reviewer', defaults={'email': 'r@r.com'})
    obj = BranchSchemeOnboarding.create_with_token(
        branch=branch,
        company_name='Alpha Funeral Services',
        email='owner@alpha.com',
        status=BranchSchemeOnboarding.STATUS_APPROVED,
    )
    obj.reviewed_by = reviewer
    obj.save(update_fields=['reviewed_by'])
    return obj


# ─────────────────────────────────────────────────────────────────────────────
# Model tests
# ─────────────────────────────────────────────────────────────────────────────

class SchemeProductModelTests(TestCase):

    def setUp(self):
        self.branch = _make_branch()
        self.scheme = _make_scheme(self.branch)
        self.plan = _make_wholesale_plan(self.scheme)
        self.onboarding = _make_approved_onboarding(self.branch)

    def test_retail_above_wholesale_not_flagged(self):
        product = SchemeProduct.objects.create(
            onboarding=self.onboarding,
            wholesale_plan=self.plan,
            product_name='Gold Cover',
            retail_premium=Decimal('300.00'),
            client_cover_amount=Decimal('20000.00'),
        )
        self.assertFalse(product.retail_below_wholesale)

    def test_retail_below_wholesale_flagged(self):
        product = SchemeProduct.objects.create(
            onboarding=self.onboarding,
            wholesale_plan=self.plan,
            product_name='Cheap Cover',
            retail_premium=Decimal('200.00'),  # below 250
            client_cover_amount=Decimal('10000.00'),
        )
        self.assertTrue(product.retail_below_wholesale)

    def test_retail_equal_to_wholesale_not_flagged(self):
        product = SchemeProduct.objects.create(
            onboarding=self.onboarding,
            wholesale_plan=self.plan,
            product_name='Break-Even Cover',
            retail_premium=Decimal('250.00'),  # equal — allowed
            client_cover_amount=Decimal('20000.00'),
        )
        self.assertFalse(product.retail_below_wholesale)

    def test_wholesale_snapshot_captured_on_create(self):
        product = SchemeProduct.objects.create(
            onboarding=self.onboarding,
            wholesale_plan=self.plan,
            product_name='Snap Cover',
            retail_premium=Decimal('280.00'),
            client_cover_amount=Decimal('20000.00'),
        )
        snap = product.wholesale_snapshot
        self.assertEqual(snap['id'], self.plan.pk)
        self.assertEqual(snap['premium'], '250.00')
        self.assertEqual(snap['admin_fee'], '30.00')
        self.assertEqual(snap['scheme_fee'], '20.00')

    def test_flag_recalculated_on_save(self):
        product = SchemeProduct.objects.create(
            onboarding=self.onboarding,
            wholesale_plan=self.plan,
            product_name='Variable Cover',
            retail_premium=Decimal('300.00'),
            client_cover_amount=Decimal('20000.00'),
        )
        self.assertFalse(product.retail_below_wholesale)
        # Lower the retail price
        product.retail_premium = Decimal('150.00')
        product.save()
        product.refresh_from_db()
        self.assertTrue(product.retail_below_wholesale)


# ─────────────────────────────────────────────────────────────────────────────
# View tests
# ─────────────────────────────────────────────────────────────────────────────

@override_settings(
    FEATURE_FLAGS=FEATURE_ON,
    ROOT_URLCONF='schemes.onboarding.tests.test_urls',
)
class ProductBuilderViewTests(TestCase):

    def setUp(self):
        self.branch = _make_branch()
        self.scheme = _make_scheme(self.branch)
        self.plan = _make_wholesale_plan(self.scheme)
        self.onboarding = _make_approved_onboarding(self.branch)
        self.token = self.onboarding.onboarding_token

    def _url(self, name, **kwargs):
        return reverse(f'scheme_onboarding:{name}', kwargs=kwargs)

    def test_product_builder_get_returns_200(self):
        url = self._url('product_builder', token=self.token)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Product Builder')

    def test_product_builder_blocked_if_not_approved(self):
        self.onboarding.status = BranchSchemeOnboarding.STATUS_SUBMITTED
        self.onboarding.save(update_fields=['status'])
        url = self._url('product_builder', token=self.token)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    def test_add_product_above_wholesale(self):
        url = self._url('product_builder', token=self.token)
        response = self.client.post(url, {
            'wholesale_plan': self.plan.pk,
            'product_name': 'Gold Cover',
            'product_description': 'Our top plan',
            'retail_premium': '300.00',
            'client_cover_amount': '20000.00',
            'policy_type': 'service',
        })
        self.assertEqual(response.status_code, 302)
        product = SchemeProduct.objects.get(product_name='Gold Cover')
        self.assertFalse(product.retail_below_wholesale)

    def test_add_product_below_wholesale_still_saves_but_is_flagged(self):
        url = self._url('product_builder', token=self.token)
        response = self.client.post(url, {
            'wholesale_plan': self.plan.pk,
            'product_name': 'Budget Cover',
            'product_description': '',
            'retail_premium': '200.00',  # below 250
            'client_cover_amount': '10000.00',
            'policy_type': 'cash',
        })
        # Should still redirect (not blocked), but flagged
        self.assertEqual(response.status_code, 302)
        product = SchemeProduct.objects.get(product_name='Budget Cover')
        self.assertTrue(product.retail_below_wholesale)

    def test_delete_product(self):
        product = SchemeProduct.objects.create(
            onboarding=self.onboarding,
            wholesale_plan=self.plan,
            product_name='To Delete',
            retail_premium=Decimal('300.00'),
            client_cover_amount=Decimal('20000.00'),
        )
        url = self._url('product_delete', token=self.token, product_pk=product.pk)
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(SchemeProduct.objects.filter(pk=product.pk).exists())
