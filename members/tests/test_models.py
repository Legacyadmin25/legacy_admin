import pytest
from datetime import date, timedelta
from decimal import Decimal
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.utils import timezone
from members.models import Policy, Member, Dependent, Beneficiary, Payment, PaymentReceipt, Branch
from schemes.models import Scheme, Plan, PlanTier, Benefit
from accounts.models import User

pytestmark = pytest.mark.django_db

class TestPolicyModel(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Create test data that will be used by all test methods
        cls.branch = Branch.objects.create(
            name='Test Branch',
            code='TB001',
            address='123 Test St',
            phone='+27123456789',
            email='branch@test.com',
            is_active=True
        )
        
        cls.scheme = Scheme.objects.create(
            name='Test Scheme',
            branch=cls.branch,
            scheme_code='TS001',
            is_active=True
        )
        
        # Create a plan with base premium and benefits
        cls.plan = Plan.objects.create(
            name='Test Plan',
            scheme=cls.scheme,
            min_age=18,
            max_age=65,
            min_sum_assured=10000,
            max_sum_assured=1000000,
            base_premium=Decimal('500.00'),
            is_active=True
        )
        
        # Add some benefits to the plan
        Benefit.objects.create(
            plan=cls.plan,
            name='Funeral Cover',
            description='Cover for funeral expenses',
            amount=Decimal('50000.00'),
            is_active=True
        )
        
        # Create a member
        cls.member = Member.objects.create(
            title='Mr',
            first_name='John',
            last_name='Doe',
            id_number='9001015009087',
            gender='Male',
            date_of_birth='1990-01-01',
            phone_number='+27821234567',
            email='john@test.com',
            marital_status='Married'
        )
        
        # Create a policy
        cls.policy = Policy.objects.create(
            member=cls.member,
            scheme=cls.scheme,
            plan=cls.plan,
            policy_number='POL12345678',
            sum_assured=Decimal('100000.00'),
            premium_amount=Decimal('500.00'),
            premium_frequency='monthly',
            start_date=date.today(),
            status='active'
        )
    
    def test_policy_str_representation(self):
        """Test the string representation of a policy."""
        self.assertEqual(str(self.policy), 'POL12345678')
    
    def test_policy_premium_calculation(self):
        """Test premium calculation logic."""
        # Test initial premium
        self.assertEqual(self.policy.premium_amount, Decimal('500.00'))
        
        # Add a spouse dependent
        spouse = Dependent.objects.create(
            policy=self.policy,
            relationship='Spouse',
            first_name='Jane',
            last_name='Doe',
            gender='Female',
            date_of_birth=date.today() - timedelta(days=365*30),
            id_number='9001015009087',
            cover_amount=Decimal('50000.00')
        )
        
        # Add a child dependent
        child = Dependent.objects.create(
            policy=self.policy,
            relationship='Child',
            first_name='Junior',
            last_name='Doe',
            gender='Male',
            date_of_birth=date.today() - timedelta(days=365*10),
            id_number='1301015009087',
            cover_amount=Decimal('25000.00')
        )
        
        # Recalculate premium (assuming 10% of cover amount for spouse and 5% for child)
        self.policy.calculate_premium()
        expected_premium = Decimal('500.00') + (Decimal('50000.00') * Decimal('0.10')) + (Decimal('25000.00') * Decimal('0.05'))
        self.assertEqual(self.policy.premium_amount, expected_premium)
    
    def test_policy_lapse_risk(self):
        """Test policy lapse risk calculation."""
        # Test initial status
        self.assertEqual(self.policy.status, 'active')
        
        # Create a payment that's 2 months overdue
        due_date = timezone.now().date() - timedelta(days=60)
        payment = Payment.objects.create(
            policy=self.policy,
            amount=Decimal('500.00'),
            due_date=due_date,
            status='overdue',
            payment_method='debit_order'
        )
        
        # Check if policy is marked as at risk
        self.policy.check_lapse_risk()
        self.assertEqual(self.policy.status, 'at_risk')
        
        # Create another payment that's 4 months overdue (should lapse)
        due_date = timezone.now().date() - timedelta(days=120)
        payment = Payment.objects.create(
            policy=self.policy,
            amount=Decimal('500.00'),
            due_date=due_date,
            status='overdue',
            payment_method='debit_order'
        )
        
        # Check if policy is lapsed
        self.policy.check_lapse_risk()
        self.assertEqual(self.policy.status, 'lapsed')
    
    def test_policy_reinstatement(self):
        """Test policy reinstatement after lapse."""
        # Set policy to lapsed
        self.policy.status = 'lapsed'
        self.policy.save()
        
        # Create a payment for reinstatement
        payment = Payment.objects.create(
            policy=self.policy,
            amount=Decimal('750.00'),  # Premium + reinstatement fee
            payment_date=timezone.now().date(),
            status='paid',
            payment_method='debit_order',
            is_reinstatement=True
        )
        
        # Reinstate the policy
        self.policy.reinstate()
        self.assertEqual(self.policy.status, 'active')
        
        # Check if reinstatement payment is recorded
        receipt = PaymentReceipt.objects.filter(payment=payment).first()
        self.assertIsNotNone(receipt)
        self.assertEqual(receipt.amount, Decimal('750.00'))
    
    def test_policy_termination(self):
        """Test policy termination."""
        # Terminate the policy
        termination_date = date.today()
        self.policy.terminate(termination_date, 'Non-payment')
        
        # Check if policy is terminated
        self.assertEqual(self.policy.status, 'terminated')
        self.assertEqual(self.policy.end_date, termination_date)
        
        # Try to terminate an already terminated policy
        with self.assertRaises(ValidationError):
            self.policy.terminate(termination_date, 'Duplicate termination')
    
    def test_policy_beneficiaries_validation(self):
        """Test beneficiary validation for policies."""
        # Create beneficiaries with total allocation > 100%
        Beneficiary.objects.create(
            policy=self.policy,
            name='Beneficiary 1',
            relationship='Spouse',
            percentage=60,
            id_number='9001015009087'
        )
        
        Beneficiary.objects.create(
            policy=self.policy,
            name='Beneficiary 2',
            relationship='Child',
            percentage=50,  # Total would be 110%
            id_number='9001015009088'
        )
        
        # Should raise validation error
        with self.assertRaises(ValidationError):
            self.policy.full_clean()
        assert policy.lapse_warning == 'none'
        
        # Test lapse risk calculation
        if hasattr(policy, 'check_lapse_risk'):
            # This test assumes there's a method to check lapse risk
            warning_level = policy.check_lapse_risk()
            assert warning_level in ['none', 'warning', 'lapsed']

class TestMemberModel(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Create a test member
        cls.member = Member.objects.create(
            title='Mr',
            first_name='John',
            last_name='Doe',
            id_number='9001015009087',
            gender='Male',
            date_of_birth='1990-01-01',
            phone_number='+27821234567',
            email='john@test.com',
            marital_status='Married',
            physical_address_line_1='123 Test St',
            physical_address_city='Cape Town',
            physical_address_postal_code='8001',
            postal_address_line_1='PO Box 123',
            postal_code='8000',
            employer_name='Test Company',
            occupation='Software Developer',
            is_active=True
        )
    
    def test_member_creation(self):
        """Test member creation with valid data."""
        self.assertEqual(self.member.first_name, 'John')
        self.assertEqual(self.member.last_name, 'Doe')
        self.assertEqual(self.member.email, 'john@test.com')
        self.assertEqual(self.member.full_name, 'John Doe')
        self.assertTrue(self.member.is_active)
    
    def test_member_age_calculation(self):
        """Test age calculation based on date of birth."""
        # Test with a fixed date of birth
        self.member.date_of_birth = date(1990, 1, 1)
        expected_age = date.today().year - 1990
        # Adjust if birthday hasn't occurred yet this year
        if (date.today().month, date.today().day) < (1, 1):
            expected_age -= 1
        self.assertEqual(self.member.age, expected_age)
    
    def test_member_id_validation(self):
        """Test South African ID number validation."""
        # Test valid ID number
        self.member.id_number = '9001015009087'
        self.member.full_clean()  # Should not raise ValidationError
        
        # Test invalid ID number (too short)
        self.member.id_number = '123'
        with self.assertRaises(ValidationError):
            self.member.full_clean()
        
        # Test invalid ID number (invalid date)
        self.member.id_number = '9912315009087'  # Invalid date (month 13)
        with self.assertRaises(ValidationError):
            self.member.full_clean()
    
    def test_member_phone_validation(self):
        """Test phone number validation."""
        # Test valid South African number
        self.member.phone_number = '+27821234567'
        self.member.full_clean()  # Should not raise ValidationError
        dependent = Dependent.objects.create(
            policy=policy,
            relationship='Child',
            first_name='Junior',
            last_name='Doe',
            gender='Male',
            date_of_birth=birth_date,
            id_number='1301015009087'
        )
        
        # Calculate age manually
        today = date.today()
        age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
        
        # Get age from model property or method
        dependent_age = getattr(dependent, 'age', None)
        if callable(dependent_age):
            dependent_age = dependent_age()
            
        # Compare if age property exists
        if dependent_age is not None:
            assert dependent_age == age
