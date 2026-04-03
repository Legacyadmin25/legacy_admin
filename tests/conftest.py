"""
Shared test fixtures for all test modules.
Provides minimal, correct test data factories using actual model fields.
"""
import pytest
from datetime import date
from decimal import Decimal
from django.contrib.auth.models import User
from django.test import Client
from django.utils import timezone

from branches.models import Bank, Branch
from schemes.models import Scheme
from members.models import Member, Policy
from claims.models import Claim
from payments.models import Payment


# ─── Helper Functions ────────────────────────────────────────────────────────

def create_bank(name='Test Bank', branch_code='000123'):
    """Factory function to create a Bank"""
    return Bank.objects.create(name=name, branch_code=branch_code)


def create_branch(bank=None, name='Test Branch', location='Test Location'):
    """Factory function to create a Branch"""
    if not bank:
        bank = create_bank()
    return Branch.objects.create(
        bank=bank,
        name=name,
        location=location
    )


def create_scheme(branch=None, name='Test Scheme'):
    """Factory function to create a Scheme"""
    if not branch:
        branch = create_branch()
    return Scheme.objects.create(
        branch=branch,
        name=name,
        registration_no='REG001',
        fsp_number='FSP123',
        email='scheme@test.com',
        phone='0710001234',
        account_no='1234567890'
    )


def create_member(first_name='John', last_name='Doe', gender='Male'):
    """Factory function to create a Member"""
    return Member.objects.create(
        first_name=first_name,
        last_name=last_name,
        gender=gender,
        date_of_birth=date(1990, 1, 1),
        phone_number='0712345678',
        email=f'{first_name}.{last_name}@test.com'
    )


def create_policy(member=None, scheme=None):
    """Factory function to create a Policy"""
    if not member:
        member = create_member()
    if not scheme:
        scheme = create_scheme()
    
    return Policy.objects.create(
        member=member,
        scheme=scheme,
        payment_method='DEBIT_ORDER',
        start_date=date.today(),
        is_complete=True
    )


def create_claim(member=None, claim_type='death', amount=Decimal('5000.00')):
    """Factory function to create a Claim"""
    if not member:
        member = create_member()
    
    return Claim.objects.create(
        member=member,
        claim_type=claim_type,
        amount=amount,
        description='Test claim description',
        status=Claim.PENDING
    )


def create_payment(member=None, amount=Decimal('500.00'), 
                   payment_method='DEBIT_ORDER', status='COMPLETED'):
    """Factory function to create a Payment"""
    if not member:
        member = create_member()
    
    return Payment.objects.create(
        member=member,
        amount=amount,
        date=date.today(),
        payment_method=payment_method,
        status=status
    )


# ─── User Fixtures ──────────────────────────────────────────────────────────

@pytest.fixture
def admin_user(db):
    """Create a superuser for admin testing"""
    return User.objects.create_superuser(
        username='admin_test',
        email='admin@test.com',
        password='adminpass123'
    )


@pytest.fixture
def regular_user(db):
    """Create a regular user without special permissions"""
    return User.objects.create_user(
        username='regular_user',
        email='user@test.com',
        password='userpass123'
    )


@pytest.fixture
def claims_officer_user(db):
    """Create a claims officer user"""
    return User.objects.create_user(
        username='claims_officer',
        email='officer@test.com',
        password='pass123'
    )


@pytest.fixture
def agent_user(db):
    """Create an agent user"""
    return User.objects.create_user(
        username='agent',
        email='agent@test.com',
        password='pass123'
    )


# ─── Client Fixtures ────────────────────────────────────────────────────────

@pytest.fixture
def admin_client(db, admin_user):
    """Create an authenticated client for admin user"""
    client = Client()
    client.force_login(admin_user)
    return client


@pytest.fixture
def user_client(db, regular_user):
    """Create an authenticated client for regular user"""
    client = Client()
    client.force_login(regular_user)
    return client


# ─── Data Fixtures ──────────────────────────────────────────────────────────

@pytest.fixture
def bank(db):
    """Create a test bank"""
    return create_bank()


@pytest.fixture
def branch(db, bank):
    """Create a test branch"""
    return create_branch(bank=bank)


@pytest.fixture
def scheme(db, branch):
    """Create a test scheme"""
    return create_scheme(branch=branch)


@pytest.fixture
def member(db):
    """Create a test member"""
    return create_member(first_name='John', last_name='Doe')


@pytest.fixture
def another_member(db):
    """Create another test member"""
    return create_member(first_name='Jane', last_name='Smith')


@pytest.fixture
def policy(db, member, scheme):
    """Create a test policy"""
    return create_policy(member=member, scheme=scheme)


@pytest.fixture
def claim_pending(db, member):
    """Create a pending claim"""
    return create_claim(member=member, claim_type='death', amount=Decimal('10000.00'))


@pytest.fixture
def claim_approved(db, member):
    """Create an approved claim"""
    claim = create_claim(member=member, claim_type='disability')
    claim.status = Claim.APPROVED
    claim.save()
    return claim


@pytest.fixture
def payment_pending(db, member):
    """Create a pending payment"""
    return create_payment(member=member, amount=Decimal('500.00'), status='PENDING')


@pytest.fixture
def payment_completed(db, member):
    """Create a completed payment"""
    return create_payment(member=member, amount=Decimal('500.00'), status='COMPLETED')


@pytest.fixture
def multiple_members(db):
    """Create multiple test members"""
    return [
        create_member(first_name=f'Member{i}', last_name=f'Test{i}')
        for i in range(3)
    ]


@pytest.fixture
def multiple_claims(db, member):
    """Create multiple test claims"""
    return [
        create_claim(member=member, amount=Decimal(f'{1000 * (i+1)}.00'))
        for i in range(3)
    ]


@pytest.fixture
def multiple_payments(db, member):
    """Create multiple test payments"""
    return [
        create_payment(member=member, amount=Decimal(f'{100 * (i+1)}.00'))
        for i in range(3)
    ]
