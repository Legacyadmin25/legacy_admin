from datetime import date

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase

from branches.models import Bank, Branch
from members.models import Member, Policy
from payments.models import Payment, PaymentAllocation
from schemes.models import Plan, Scheme
from settings_app.models import Agent


class PaymentAllocationBackfillCommandTests(TestCase):
	def setUp(self):
		self.user = get_user_model().objects.create_user(username='capturer', password='pass1234')
		bank = Bank.objects.create(name='Bank', branch_code='123456')
		branch = Branch.objects.create(name='Main Branch', bank=bank, code='MB01')
		scheme = Scheme.objects.create(
			branch=branch,
			name='Test Scheme',
			prefix='TS',
			registration_no='REG1',
			fsp_number='FSP1',
			email='scheme@example.com',
			phone='0123456789',
			debit_order_no='DEB1',
			account_no='12345',
		)
		plan = Plan.objects.create(
			name='Gold Plan',
			scheme=scheme,
			premium='150.00',
			policy_type='cash',
			main_cover='10000.00',
		)
		agent = Agent.objects.create(
			full_name='Agent Smith',
			surname='Smith',
			contact_number='0821111111',
			email='agent@example.com',
			address1='1 Main',
			address2='Town',
			address3='Province',
			code='AG01',
			scheme=scheme,
			commission_rand_value='15.00',
		)
		member = Member.objects.create(
			first_name='Jane',
			last_name='Doe',
			gender='Female',
			date_of_birth=date(1990, 1, 1),
			phone_number='0820000000',
		)
		self.policy = Policy.objects.create(
			member=member,
			scheme=scheme,
			plan=plan,
			membership_number='M123',
			cover_date=date(2026, 5, 1),
			inception_date=date(2026, 4, 1),
			start_date=date(2026, 4, 1),
			payment_method='EASYPAY',
			underwritten_by=agent,
			cover_amount='10000.00',
			premium_amount='150.00',
		)

	def test_backfill_payment_allocations_creates_missing_rows(self):
		payment = Payment.objects.create(
			member=self.policy.member,
			policy=self.policy,
			amount='150.00',
			date=date(2026, 4, 15),
			payment_method='EASYPAY',
			status='COMPLETED',
			created_by=self.user,
		)

		call_command('backfill_payment_allocations')

		allocation = PaymentAllocation.objects.get(payment=payment)
		self.assertEqual(allocation.coverage_month, date(2026, 5, 1))

	def test_backfill_payment_allocations_dry_run_does_not_write(self):
		Payment.objects.create(
			member=self.policy.member,
			policy=self.policy,
			amount='150.00',
			date=date(2026, 4, 15),
			payment_method='EASYPAY',
			status='COMPLETED',
			created_by=self.user,
		)

		call_command('backfill_payment_allocations', '--dry-run')

		self.assertEqual(PaymentAllocation.objects.count(), 0)
