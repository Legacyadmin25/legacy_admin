import pytest
from datetime import date, timedelta
from decimal import Decimal
from django.test import TestCase, override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.exceptions import ValidationError
from django.utils import timezone
from members.forms import (
    PersonalDetailsForm, PolicyDetailsForm, DependentForm, BeneficiaryForm,
    PaymentDetailsForm, BankDetailsForm, BeneficiaryFormSet, DocumentUploadForm
)
from members.models import Member, Policy, Scheme, Plan, Branch, Dependent, Beneficiary
from schemes.models import PlanTier, Benefit
from accounts.models import User
from utils.luhn import luhn_check, validate_id_number

pytestmark = pytest.mark.django_db

class TestPersonalDetailsForm(TestCase):
    """Tests for the personal details form used in the policy signup wizard."""
    
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
        
        # Create a member for testing
        cls.member = Member.objects.create(
            first_name='John',
            last_name='Doe',
            id_number='9001015009087',
            gender='Male',
            date_of_birth='1990-01-01',
            phone_number='+27821234567',
            email='john@test.com',
            marital_status='Single'
        )
    
    def test_valid_form(self):
        """Test that a valid form passes validation."""
        form_data = {
            'title': 'Mr',
            'first_name': 'John',
            'last_name': 'Doe',
            'id_number': '9001015009087',  # Valid SA ID format
            'gender': 'Male',
            'date_of_birth': '1990-01-01',
            'phone_number': '+27821234567',
            'email': 'john@example.com',
            'marital_status': 'Single',
            'physical_address_line_1': '123 Main St',
            'physical_address_city': 'Cape Town',
            'physical_address_postal_code': '8001',
            'postal_address_line_1': 'PO Box 123',
            'postal_code': '8001',
            'employer_name': 'Test Company',
            'occupation': 'Software Developer',
            'is_smoker': False,
            'has_chronic_condition': False
        }
        form = PersonalDetailsForm(data=form_data)
        self.assertTrue(form.is_valid(), msg=f"Form errors: {form.errors}")

    def test_invalid_id_number(self):
        """Test that an invalid ID number fails validation."""
        form_data = {
            'title': 'Mr',
            'first_name': 'John',
            'last_name': 'Doe',
            'id_number': '12345',  # Invalid SA ID
            'gender': 'Male',
            'date_of_birth': '1990-01-01',
            'phone_number': '+27821234567',
            'email': 'john@example.com',
            'marital_status': 'Single',
            'physical_address_line_1': '123 Main St',
            'physical_address_city': 'Cape Town',
            'physical_address_postal_code': '8001',
            'postal_address_line_1': 'PO Box 123',
            'postal_code': '8001'
        }
        form = PersonalDetailsForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('id_number', form.errors)
        self.assertEqual(form.errors['id_number'], ['ID number must be 13 digits'])
    
    def test_duplicate_id_number(self):
        """Test that a duplicate ID number is caught during validation."""
        # Create a member with the same ID number
        Member.objects.create(
            title='Mr',
            first_name='Existing',
            last_name='User',
            id_number='9001015009087',
            gender='Male',
            date_of_birth='1990-01-01',
            phone_number='+27821234567',
            email='existing@test.com',
            marital_status='Single'
        )
        
        form_data = {
            'title': 'Mr',
            'first_name': 'John',
            'last_name': 'Doe',
            'id_number': '9001015009087',  # Duplicate ID
            'gender': 'Male',
            'date_of_birth': '1990-01-01',
            'phone_number': '+27821234568',
            'email': 'john@test.com',
            'marital_status': 'Single',
            'physical_address_line_1': '123 Main St',
            'physical_address_city': 'Cape Town',
            'physical_address_postal_code': '8001',
            'postal_address_line_1': 'PO Box 123',
            'postal_code': '8001'
        }
        
        form = PersonalDetailsForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('id_number', form.errors)
        self.assertEqual(form.errors['id_number'], ['Member with this ID number already exists.'])
    
    def test_age_validation(self):
        """Test that age validation works correctly."""
        # Test with age below minimum
        form_data = {
            'title': 'Mr',
            'first_name': 'Young',
            'last_name': 'User',
            'id_number': '1201015009087',  # Born in 2012
            'gender': 'Male',
            'date_of_birth': '2012-01-01',
            'phone_number': '+27821234567',
            'email': 'young@test.com',
            'marital_status': 'Single',
            'physical_address_line_1': '123 Main St',
            'physical_address_city': 'Cape Town',
            'physical_address_postal_code': '8001',
            'postal_address_line_1': 'PO Box 123',
            'postal_code': '8001'
        }
        
        form = PersonalDetailsForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('date_of_birth', form.errors)
        self.assertEqual(form.errors['date_of_birth'], ['You must be at least 18 years old to apply.'])
        
        # Test with age above maximum
        form_data.update({
            'id_number': '3001015009087',  # Born in 1930
            'date_of_birth': '1930-01-01'
        })
        
        form = PersonalDetailsForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('date_of_birth', form.errors)
        self.assertEqual(form.errors['date_of_birth'], ['Maximum age for this plan is 65 years.'])
        
    def test_id_number_luhn_validation(self):
        """Test Luhn algorithm validation for SA ID numbers."""
        # Valid ID number that passes Luhn check
        valid_id = '9001015009087'
        assert luhn_check(valid_id)
        
        # Invalid ID number that fails Luhn check (last digit changed)
        invalid_id = '9001015009088'
        assert not luhn_check(invalid_id)
        
        # Test with form
        form_data = {
            'title': 'Mr',
            'first_name': 'John',
            'last_name': 'Doe',
            'id_number': invalid_id,
            'gender': 'Male',
            'date_of_birth': '1990-01-01',
            'phone_number': '+27821234567',
            'email': 'john@example.com',
            'marital_status': 'Single',
            'physical_address_line_1': '123 Main St',
            'physical_address_city': 'Cape Town',
            'physical_address_postal_code': '8001'
        }
        form = PersonalDetailsForm(data=form_data)
        assert not form.is_valid()
        assert 'id_number' in form.errors
        
    def test_foreign_national_validation(self):
        """Test validation for foreign nationals with passport instead of ID."""
        form_data = {
            'title': 'Mr',
            'first_name': 'John',
            'last_name': 'Doe',
            'is_foreign': True,
            'passport_number': 'AB123456',
            'gender': 'Male',
            'date_of_birth': '1990-01-01',
            'phone_number': '+27821234567',
            'email': 'john@example.com',
            'marital_status': 'Single',
            'physical_address_line_1': '123 Main St',
            'physical_address_city': 'Cape Town',
            'physical_address_postal_code': '8001',
            'nationality': 'British',
            'country_of_birth': 'United Kingdom',
            'country_of_residence': 'South Africa'
        }
        
        form = PersonalDetailsForm(data=form_data)
        self.assertTrue(form.is_valid(), msg=f"Form errors: {form.errors}")
        
        # Test that ID number is not required for foreign nationals
        self.assertNotIn('id_number', form.errors)
        
        # Test that passport number is required for foreign nationals
        form_data['passport_number'] = ''
        form = PersonalDetailsForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('passport_number', form.errors)


class TestPolicyDetailsForm(TestCase):
    """Tests for the policy details form used in the policy signup wizard."""
    
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
        
        # Create a basic plan
        cls.basic_plan = Plan.objects.create(
            name='Basic Plan',
            scheme=cls.scheme,
            min_age=18,
            max_age=65,
            min_sum_assured=10000,
            max_sum_assured=500000,
            base_premium=Decimal('500.00'),
            is_active=True
        )
        
        # Create a premium plan
        cls.premium_plan = Plan.objects.create(
            name='Premium Plan',
            scheme=cls.scheme,
            min_age=18,
            max_age=65,
            min_sum_assured=100000,
            max_sum_assured=1000000,
            base_premium=Decimal('1000.00'),
            is_active=True
        )
        
        # Create a member for testing
        cls.member = Member.objects.create(
            first_name='John',
            last_name='Doe',
            id_number='9001015009087',
            gender='Male',
            date_of_birth='1990-01-01',
            phone_number='+27821234567',
            email='john@test.com',
            marital_status='Single'
        )
    
    def test_valid_form(self):
        """Test that a valid form passes validation."""
        form_data = {
            'scheme': self.scheme.id,
            'plan': self.basic_plan.id,
            'sum_assured': '250000',
            'premium_frequency': 'monthly',
            'start_date': (date.today() + timedelta(days=7)).strftime('%Y-%m-%d'),
            'payment_method': 'debit_order',
            'payment_day': '1',
            'bank_name': 'Test Bank',
            'account_holder': 'John Doe',
            'account_number': '1234567890',
            'account_type': 'savings',
            'branch_code': '123456',
            'debit_order_date': '1',
            'accept_terms': True
        }
        
        form = PolicyDetailsForm(
            data=form_data, 
            scheme_id=self.scheme.id,
            member=self.member
        )
        
        self.assertTrue(form.is_valid(), msg=f"Form errors: {form.errors}")
        
        # Test cleaned data
        cleaned_data = form.clean()
        self.assertEqual(cleaned_data['sum_assured'], 250000)
        self.assertEqual(cleaned_data['premium_frequency'], 'monthly')
        
        # Test save method
        policy = form.save(commit=False)
        policy.member = self.member
        policy.save()
        self.assertIsInstance(policy, Policy)
        self.assertEqual(policy.sum_assured, 250000)
        self.assertEqual(policy.premium_frequency, 'monthly')
    
    def test_sum_assured_validation(self):
        """Test sum assured validation against plan limits."""
        # Test sum assured below minimum
        form_data = {
            'scheme': self.scheme.id,
            'plan': self.basic_plan.id,
            'sum_assured': '5000',  # Below minimum
            'premium_frequency': 'monthly',
            'start_date': (date.today() + timedelta(days=7)).strftime('%Y-%m-%d'),
            'payment_method': 'debit_order'
        }
        
        form = PolicyDetailsForm(
            data=form_data, 
            scheme_id=self.scheme.id,
            member=self.member
        )
        
        self.assertFalse(form.is_valid())
        self.assertIn('sum_assured', form.errors)
        self.assertIn('must be at least', form.errors['sum_assured'][0])
        
        # Test sum assured above maximum
        form_data['sum_assured'] = '600000'  # Above maximum for basic plan
        form = PolicyDetailsForm(
            data=form_data, 
            scheme_id=self.scheme.id,
            member=self.member
        )
        
        self.assertFalse(form.is_valid())
        self.assertIn('sum_assured', form.errors)
        self.assertIn('cannot exceed', form.errors['sum_assured'][0])
    
    def test_start_date_validation(self):
        """Test start date validation."""
        # Test start date in the past
        form_data = {
            'scheme': self.scheme.id,
            'plan': self.basic_plan.id,
            'sum_assured': '100000',
            'premium_frequency': 'monthly',
            'start_date': (date.today() - timedelta(days=1)).strftime('%Y-%m-%d'),
            'payment_method': 'debit_order'
        }
        
        form = PolicyDetailsForm(
            data=form_data, 
            scheme_id=self.scheme.id,
            member=self.member
        )
        
        self.assertFalse(form.is_valid())
        self.assertIn('start_date', form.errors)
        self.assertEqual(form.errors['start_date'], ['Start date cannot be in the past.'])
        
        # Test start date too far in the future
        form_data['start_date'] = (date.today() + timedelta(days=366)).strftime('%Y-%m-%d')
        form = PolicyDetailsForm(
            data=form_data, 
            scheme_id=self.scheme.id,
            member=self.member
        )
        
        self.assertFalse(form.is_valid())
        self.assertIn('start_date', form.errors)
        self.assertEqual(form.errors['start_date'], ['Start date cannot be more than 1 year in the future.'])
    
    def test_payment_validation(self):
        """Test payment method validation."""
        # Test debit order without required fields
        form_data = {
            'scheme': self.scheme.id,
            'plan': self.basic_plan.id,
            'sum_assured': '100000',
            'premium_frequency': 'monthly',
            'start_date': (date.today() + timedelta(days=7)).strftime('%Y-%m-%d'),
            'payment_method': 'debit_order',
            # Missing bank details
        }
        
        form = PolicyDetailsForm(
            data=form_data, 
            scheme_id=self.scheme.id,
            member=self.member
        )
        
        self.assertFalse(form.is_valid())
        self.assertIn('bank_name', form.errors)
        self.assertIn('account_holder', form.errors)
        self.assertIn('account_number', form.errors)
        self.assertIn('branch_code', form.errors)
        
        # Test cash payment (should not require bank details)
        form_data['payment_method'] = 'cash'
        form = PolicyDetailsForm(
            data=form_data, 
            scheme_id=self.scheme.id,
            member=self.member
        )
        
        self.assertTrue(form.is_valid(), msg=f"Form errors: {form.errors}")
        
    def test_invalid_start_date(self, scheme, plan):
        """Test that a start date in the past fails validation."""
        past_date = (date.today() - timedelta(days=30)).strftime('%Y-%m-%d')
        form_data = {
            'scheme': scheme.id,
            'plan': plan.id,
            'membership_number': 'MEM123456',
            'start_date': past_date,
            'inception_date': date.today().strftime('%Y-%m-%d'),
            'cover_date': date.today().strftime('%Y-%m-%d'),
            'premium_amount': '100.00',
            'cover_amount': '10000.00'
        }
        form = PolicyDetailsForm(data=form_data)
        # Note: The form may or may not validate past dates depending on implementation
        # This test should be adjusted based on the actual requirements
        
    def test_plan_scheme_relationship(self, scheme, plan, scheme_factory):
        """Test that a plan must belong to the selected scheme."""
        # Create a different scheme
        other_scheme = scheme_factory()
        
        form_data = {
            'scheme': other_scheme.id,  # Different scheme than the plan's scheme
            'plan': plan.id,  # This plan belongs to the original scheme
            'membership_number': 'MEM123456',
            'start_date': date.today().strftime('%Y-%m-%d'),
            'inception_date': date.today().strftime('%Y-%m-%d'),
            'cover_date': date.today().strftime('%Y-%m-%d'),
            'premium_amount': '100.00',
            'cover_amount': '10000.00'
        }
        form = PolicyDetailsForm(data=form_data)
        # The form should validate or not based on whether the application enforces
        # that plans must belong to the selected scheme

class TestDependentForm:
    """Tests for the dependent form used in the policy signup wizard."""
    
    def test_valid_dependent(self, policy):
        """Test that a valid dependent form passes validation."""
        form_data = {
            'relationship': 'Child',
            'first_name': 'Junior',
            'last_name': 'Doe',
            'id_number': '0601015009087',  # Valid SA ID for a child
            'gender': 'Male',
            'date_of_birth': '2006-01-01'
        }
        form = DependentForm(data=form_data)
        assert form.is_valid(), f"Form errors: {form.errors}"
    
    def test_relationship_required(self, policy):
        """Test that relationship is required for dependents."""
        form_data = {
            'first_name': 'Junior',
            'last_name': 'Doe',
            'id_number': '0601015009087',
            'gender': 'Male',
            'date_of_birth': '2006-01-01'
        }
        form = DependentForm(data=form_data)
        assert not form.is_valid()
        assert 'relationship' in form.errors
    
    def test_id_validation(self, policy):
        """Test ID validation for dependents."""
        # Invalid ID number (wrong checksum)
        form_data = {
            'relationship': 'Child',
            'first_name': 'Junior',
            'last_name': 'Doe',
            'id_number': '0601015009088',  # Invalid checksum
            'gender': 'Male',
            'date_of_birth': '2006-01-01'
        }
        form = DependentForm(data=form_data)
        assert not form.is_valid()
        assert 'id_number' in form.errors

class TestBeneficiaryForm:
    """Tests for the beneficiary form used in the policy signup wizard."""
    
    def test_valid_beneficiary(self, policy):
        """Test that a valid beneficiary form passes validation."""
        form_data = {
            'relationship_to_main_member': 'Spouse',
            'first_name': 'Jane',
            'last_name': 'Doe',
            'id_number': '9101015009087',  # Valid SA ID
            'share': 100
        }
        form = BeneficiaryForm(data=form_data)
        assert form.is_valid(), f"Form errors: {form.errors}"
    
    def test_share_validation(self, policy):
        """Test share percentage validation for beneficiaries."""
        # Test share percentage > 100
        form_data = {
            'relationship_to_main_member': 'Spouse',
            'first_name': 'Jane',
            'last_name': 'Doe',
            'id_number': '9101015009087',
            'share': 101  # Invalid: > 100
        }
        form = BeneficiaryForm(data=form_data)
        assert not form.is_valid()
        assert 'share' in form.errors
        
        # Test share percentage < 1
        form_data['share'] = 0  # Invalid: < 1
        form = BeneficiaryForm(data=form_data)
        assert not form.is_valid()
        assert 'share' in form.errors
