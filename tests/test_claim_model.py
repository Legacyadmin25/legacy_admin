"""
Unit tests for Claim model
"""
import pytest
from decimal import Decimal
from datetime import date
from claims.models import Claim
from members.models import Member


class TestClaimCreation:
    """Test Claim model creation"""
    
    def test_claim_can_be_created(self, db):
        """Test creating a claim with required fields"""
        member = Member.objects.create(
            first_name='John',
            last_name='Doe',
            gender='Male',
            date_of_birth=date(1990, 1, 1),
            phone_number='0712345678'
        )
        claim = Claim.objects.create(
            member=member,
            claim_type='death',
            amount=Decimal('5000.00'),
            description='Death claim'
        )
        assert claim.id is not None
        assert claim.member == member
        assert claim.amount == Decimal('5000.00')
    
    def test_claim_default_status_is_pending(self, db):
        """Test that new claim defaults to PENDING status"""
        member = Member.objects.create(
            first_name='Jane',
            last_name='Smith',
            gender='Female',
            date_of_birth=date(1985, 1, 1),
            phone_number='0787654321'
        )
        claim = Claim.objects.create(
            member=member,
            claim_type='disability',
            amount=Decimal('3000.00'),
            description='Disability claim'
        )
        assert claim.status == Claim.PENDING
    
    def test_claim_string_representation(self, db):
        """Test Claim __str__ method"""
        member = Member.objects.create(
            first_name='Bob',
            last_name='Wilson',
            gender='Male',
            date_of_birth=date(1988, 5, 15),
            phone_number='0768901234'
        )
        claim = Claim.objects.create(
            member=member,
            claim_type='death',
            amount=Decimal('10000.00'),
            description='Major claim'
        )
        str_repr = str(claim)
        assert 'Bob' in str_repr
        assert 'Wilson' in str_repr
        assert '10000' in str_repr


class TestClaimStatus:
    """Test Claim status management"""
    
    def test_claim_status_choices(self, db):
        """Test all valid claim status choices"""
        member = Member.objects.create(
            first_name='Test',
            last_name='User',
            gender='Male',
            date_of_birth=date(1990, 1, 1),
            phone_number='0711111111'
        )
        
        # Test PENDING
        pending = Claim.objects.create(
            member=member,
            claim_type='death',
            amount=Decimal('1000.00'),
            description='Test',
            status=Claim.PENDING
        )
        assert pending.status == 'pending'
        
        # Test APPROVED
        approved = Claim.objects.create(
            member=member,
            claim_type='death',
            amount=Decimal('1000.00'),
            description='Test',
            status=Claim.APPROVED
        )
        assert approved.status == 'approved'
        
        # Test REJECTED
        rejected = Claim.objects.create(
            member=member,
            claim_type='death',
            amount=Decimal('1000.00'),
            description='Test',
            status=Claim.REJECTED
        )
        assert rejected.status == 'rejected'
    
    def test_claim_status_update(self, db):
        """Test updating claim status in memory"""
        member = Member.objects.create(
            first_name='Update',
            last_name='Test',
            gender='Male',
            date_of_birth=date(1990, 1, 1),
            phone_number='0722222222'
        )
        claim = Claim.objects.create(
            member=member,
            claim_type='death',
            amount=Decimal('5000.00'),
            description='Test'
        )
        assert claim.status == Claim.PENDING
        
        # Test status change in memory without triggering audit
        claim.status = Claim.APPROVED
        assert claim.status == Claim.APPROVED


class TestClaimAmounts:
    """Test Claim amount handling"""
    
    def test_claim_various_amounts(self, db):
        """Test claims with different amounts"""
        member = Member.objects.create(
            first_name='Amount',
            last_name='Test',
            gender='Male',
            date_of_birth=date(1990, 1, 1),
            phone_number='0733333333'
        )
        
        amounts = [
            Decimal('100.00'),
            Decimal('1000.00'),
            Decimal('10000.00'),
            Decimal('99999.99')
        ]
        
        for amount in amounts:
            claim = Claim.objects.create(
                member=member,
                claim_type='death',
                amount=amount,
                description=f'Claim for {amount}'
            )
            assert claim.amount == amount
    
    def test_claim_decimal_precision(self, db):
        """Test claim amounts maintain decimal precision"""
        member = Member.objects.create(
            first_name='Decimal',
            last_name='Test',
            gender='Male',
            date_of_birth=date(1990, 1, 1),
            phone_number='0744444444'
        )
        claim = Claim.objects.create(
            member=member,
            claim_type='death',
            amount=Decimal('1234.56'),
            description='Precise amount'
        )
        refreshed = Claim.objects.get(id=claim.id)
        assert refreshed.amount == Decimal('1234.56')


class TestClaimTypes:
    """Test Claim type field"""
    
    def test_claim_various_types(self, db):
        """Test claims can have different types"""
        member = Member.objects.create(
            first_name='Type',
            last_name='Test',
            gender='Male',
            date_of_birth=date(1990, 1, 1),
            phone_number='0755555555'
        )
        
        claim_types = ['death', 'disability', 'injury', 'illness']
        
        for claim_type in claim_types:
            claim = Claim.objects.create(
                member=member,
                claim_type=claim_type,
                amount=Decimal('1000.00'),
                description=f'{claim_type} claim'
            )
            assert claim.claim_type == claim_type


class TestClaimRelationships:
    """Test Claim relationships and dependencies"""
    
    def test_claim_member_relationship(self, db):
        """Test claim is properly linked to member"""
        member = Member.objects.create(
            first_name='Related',
            last_name='Member',
            gender='Male',
            date_of_birth=date(1990, 1, 1),
            phone_number='0766666666'
        )
        claim = Claim.objects.create(
            member=member,
            claim_type='death',
            amount=Decimal('5000.00'),
            description='Relationship test'
        )
        
        # Retrieve via member relationship
        member_claims = member.claim_set.all()
        assert member_claims.count() == 1
        assert member_claims.first().id == claim.id
    
    def test_member_multiple_claims(self, db):
        """Test member can have multiple claims"""
        member = Member.objects.create(
            first_name='Multiple',
            last_name='Claims',
            gender='Male',
            date_of_birth=date(1990, 1, 1),
            phone_number='0777777777'
        )
        
        for i in range(5):
            Claim.objects.create(
                member=member,
                claim_type='death',
                amount=Decimal('1000.00'),
                description=f'Claim {i}'
            )
        
        assert member.claim_set.count() == 5


class TestClaimTimestamps:
    """Test Claim timestamp fields"""
    
    def test_claim_created_at_automatic(self, db):
        """Test that created_at is automatically set"""
        member = Member.objects.create(
            first_name='Time',
            last_name='Test',
            gender='Male',
            date_of_birth=date(1990, 1, 1),
            phone_number='0788888888'
        )
        claim = Claim.objects.create(
            member=member,
            claim_type='death',
            amount=Decimal('5000.00'),
            description='Timestamp test'
        )
        assert claim.created_at is not None
    
    def test_claim_submitted_date_automatic(self, db):
        """Test that submitted_date is automatically set"""
        member = Member.objects.create(
            first_name='Submit',
            last_name='Date',
            gender='Male',
            date_of_birth=date(1990, 1, 1),
            phone_number='0799999999'
        )
        claim = Claim.objects.create(
            member=member,
            claim_type='death',
            amount=Decimal('5000.00'),
            description='Submit date test'
        )
        assert claim.submitted_date is not None


class TestClaimQuerying:
    """Test Claim model querying"""
    
    def test_filter_claims_by_status(self, db):
        """Test filtering claims by status"""
        member = Member.objects.create(
            first_name='Query',
            last_name='Test',
            gender='Male',
            date_of_birth=date(1990, 1, 1),
            phone_number='0700000000'
        )
        
        Claim.objects.create(
            member=member,
            claim_type='death',
            amount=Decimal('1000.00'),
            description='Pending',
            status=Claim.PENDING
        )
        Claim.objects.create(
            member=member,
            claim_type='death',
            amount=Decimal('2000.00'),
            description='Approved',
            status=Claim.APPROVED
        )
        
        pending_claims = Claim.objects.filter(status=Claim.PENDING)
        assert pending_claims.count() == 1
        
        approved_claims = Claim.objects.filter(status=Claim.APPROVED)
        assert approved_claims.count() == 1
    
    def test_filter_claims_by_member(self, db):
        """Test filtering claims by member"""
        member1 = Member.objects.create(
            first_name='Member',
            last_name='One',
            gender='Male',
            date_of_birth=date(1990, 1, 1),
            phone_number='0711111111'
        )
        member2 = Member.objects.create(
            first_name='Member',
            last_name='Two',
            gender='Female',
            date_of_birth=date(1991, 1, 1),
            phone_number='0722222222'
        )
        
        Claim.objects.create(
            member=member1,
            claim_type='death',
            amount=Decimal('1000.00'),
            description='Claim 1'
        )
        Claim.objects.create(
            member=member2,
            claim_type='death',
            amount=Decimal('2000.00'),
            description='Claim 2'
        )
        
        member1_claims = Claim.objects.filter(member=member1)
        assert member1_claims.count() == 1
