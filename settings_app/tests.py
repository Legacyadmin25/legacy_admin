from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase

from branches.models import Bank, Branch
from members.models import Member, Policy
from payments.models import Payment
from schemes.models import Plan, Scheme
from settings_app.models import Agent
from settings_app.views.agent_dashboard import AgentDashboardView


class AgentDashboardViewTests(TestCase):
	def setUp(self):
		self.factory = RequestFactory()
		self.user = get_user_model().objects.create_user(
			username='agentuser',
			password='pass1234',
			is_staff=True,
		)
		self.bank = Bank.objects.create(name='Bank', branch_code='123456')
		self.branch = Branch.objects.create(name='Main Branch', bank=self.bank, code='MB01')
		self.scheme = Scheme.objects.create(
			branch=self.branch,
			name='Test Scheme',
			prefix='TS',
			registration_no='REG1',
			fsp_number='FSP1',
			email='scheme@example.com',
			phone='0123456789',
			debit_order_no='DEB1',
			account_no='12345',
		)
		self.plan = Plan.objects.create(
			name='Gold Plan',
			scheme=self.scheme,
			premium='150.00',
			policy_type='cash',
			main_cover='10000.00',
			main_uw_cover='9000.00',
			main_uw_premium='80.00',
			admin_fee='20.00',
			scheme_fee='10.00',
			office_fee='5.00',
			manager_fee='3.00',
			agent_commission='12.00',
		)
		self.agent = Agent.objects.create(
			user=self.user,
			full_name='Agent Smith',
			surname='Smith',
			contact_number='0821111111',
			email='agent@example.com',
			address1='1 Main',
			address2='Town',
			address3='Province',
			code='AG01',
			scheme=self.scheme,
			commission_rand_value='15.00',
		)
		self.member = Member.objects.create(
			first_name='Jane',
			last_name='Doe',
			gender='Female',
			date_of_birth=date(1990, 1, 1),
			phone_number='0820000000',
		)
		self.policy = Policy.objects.create(
			member=self.member,
			scheme=self.scheme,
			plan=self.plan,
			start_date=date.today().replace(day=1),
			cover_date=date.today().replace(day=28),
			inception_date=date.today().replace(day=1),
			payment_method='EASYPAY',
			underwritten_by=self.agent,
			cover_amount='10000.00',
			premium_amount='150.00',
		)

	def test_agent_dashboard_uses_payment_allocations(self):
		payment = Payment.objects.create(
			member=self.member,
			policy=self.policy,
			amount='150.00',
			date=date.today(),
			payment_method='EASYPAY',
			status='COMPLETED',
			created_by=self.user,
		)
		payment.create_default_allocation(date.today().replace(day=1), created_by=self.user)

		request = self.factory.get('/settings/agent-dashboard/')
		request.user = self.user
		view = AgentDashboardView()
		view.setup(request)
		context = view.get_context_data()

		self.assertEqual(context['agent'].active_policies, 1)
		self.assertEqual(context['agent'].referral_count, 1)
		self.assertEqual(Decimal(str(context['agent'].commission_earned)), Decimal('15.00'))
		self.assertTrue(context['diy_share_url'].endswith(f'/members/s/{self.agent.pk}/'))
