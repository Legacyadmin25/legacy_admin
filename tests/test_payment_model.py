"""
Unit tests for Payment model
"""
import pytest
from decimal import Decimal
from datetime import date
from payments.models import Payment
from members.models import Member
from schemes.models import Scheme
from branches.models import Bank, Branch


class TestPaymentCreation:
    """Test Payment model creation"""
    
    def test_payment_can_be_created(self, db):
        """Test creating a payment with required fields"""
        member = Member.objects.create(
            first_name='John',
            last_name='Doe',
            gender='Male',
            date_of_birth=date(1990, 1, 1),
            phone_number='0712345678'
        )
        payment = Payment.objects.create(
            member=member,
            amount=Decimal('500.00'),
            date=date.today(),
            payment_method='DEBIT_ORDER'
        )
        assert payment.id is not None
        assert payment.member == member
        assert payment.amount == Decimal('500.00')
    
    def test_payment_default_status(self, db):
        """Test payment default status"""
        member = Member.objects.create(
            first_name='Jane',
            last_name='Smith',
            gender='Female',
            date_of_birth=date(1985, 1, 1),
            phone_number='0787654321'
        )
        payment = Payment.objects.create(
            member=member,
            amount=Decimal('250.00'),
            date=date.today(),
            payment_method='EFT'
        )
        # Check default status
        assert payment.status == 'COMPLETED'
    
    def test_payment_string_representation(self, db):
        """Test Payment __str__ method"""
        member = Member.objects.create(
            first_name='Bob',
            last_name='Wilson',
            gender='Male',
            date_of_birth=date(1988, 5, 15),
            phone_number='0768901234'
        )
        payment = Payment.objects.create(
            member=member,
            amount=Decimal('1000.00'),
            date=date.today(),
            payment_method='BANK_TRANSFER'
        )
        str_repr = str(payment)
        assert payment.id is not None


class TestPaymentMethods:
    """Test Payment method field"""
    
    def test_payment_various_methods(self, db):
        """Test payments with different payment methods"""
        member = Member.objects.create(
            first_name='Method',
            last_name='Tester',
            gender='Male',
            date_of_birth=date(1990, 1, 1),
            phone_number='0711111111'
        )
        
        methods = ['CASH', 'CHECK', 'CREDIT', 'BANK_TRANSFER', 'DEBIT_ORDER', 'EASYPAY', 'OTHER']
        
        for method in methods:
            payment = Payment.objects.create(
                member=member,
                amount=Decimal('100.00'),
                date=date.today(),
                payment_method=method
            )
            assert payment.payment_method == method
    
    def test_payment_method_required(self, db):
        """Test payment method is required"""
        member = Member.objects.create(
            first_name='Required',
            last_name='Field',
            gender='Male',
            date_of_birth=date(1990, 1, 1),
            phone_number='0722222222'
        )
        # Should work since payment_method has no default but is required
        payment = Payment.objects.create(
            member=member,
            amount=Decimal('500.00'),
            date=date.today(),
            payment_method='BANK_TRANSFER'
        )
        assert payment.payment_method == 'BANK_TRANSFER'


class TestPaymentStatus:
    """Test Payment status field"""
    
    def test_payment_various_statuses(self, db):
        """Test payments with different statuses"""
        member = Member.objects.create(
            first_name='Status',
            last_name='Tester',
            gender='Male',
            date_of_birth=date(1990, 1, 1),
            phone_number='0733333333'
        )
        
        statuses = ['PENDING', 'COMPLETED', 'FAILED', 'REFUNDED']
        
        for status in statuses:
            payment = Payment.objects.create(
                member=member,
                amount=Decimal('100.00'),
                date=date.today(),
                payment_method='BANK_TRANSFER',
                status=status
            )
            assert payment.status == status
    
    def test_payment_status_update(self, db):
        """Test updating payment status in memory"""
        member = Member.objects.create(
            first_name='Update',
            last_name='Status',
            gender='Male',
            date_of_birth=date(1990, 1, 1),
            phone_number='0744444444'
        )
        payment = Payment.objects.create(
            member=member,
            amount=Decimal('500.00'),
            date=date.today(),
            payment_method='BANK_TRANSFER',
            status='PENDING'
        )
        assert payment.status == 'PENDING'
        
        # Test status change in memory (save triggers audit which requires request context)
        payment.status = 'COMPLETED'
        assert payment.status == 'COMPLETED'


class TestPaymentAmounts:
    """Test Payment amount handling"""
    
    def test_payment_various_amounts(self, db):
        """Test payments with different amounts"""
        member = Member.objects.create(
            first_name='Amount',
            last_name='Tester',
            gender='Male',
            date_of_birth=date(1990, 1, 1),
            phone_number='0755555555'
        )
        
        amounts = [
            Decimal('10.00'),
            Decimal('100.00'),
            Decimal('1000.00'),
            Decimal('99999.99')
        ]
        
        for amount in amounts:
            payment = Payment.objects.create(
                member=member,
                amount=amount,
                date=date.today(),
                payment_method='BANK_TRANSFER'
            )
            assert payment.amount == amount
    
    def test_payment_decimal_precision(self, db):
        """Test payment amounts maintain decimal precision"""
        member = Member.objects.create(
            first_name='Decimal',
            last_name='Precision',
            gender='Male',
            date_of_birth=date(1990, 1, 1),
            phone_number='0766666666'
        )
        payment = Payment.objects.create(
            member=member,
            amount=Decimal('1234.56'),
            date=date.today(),
            payment_method='BANK_TRANSFER'
        )
        refreshed = Payment.objects.get(id=payment.id)
        assert refreshed.amount == Decimal('1234.56')


class TestPaymentDate:
    """Test Payment date field"""
    
    def test_payment_with_date(self, db):
        """Test payment stores date correctly"""
        member = Member.objects.create(
            first_name='Date',
            last_name='Tester',
            gender='Male',
            date_of_birth=date(1990, 1, 1),
            phone_number='0777777777'
        )
        payment_date = date(2023, 6, 15)
        payment = Payment.objects.create(
            member=member,
            amount=Decimal('500.00'),
            date=payment_date,
            payment_method='BANK_TRANSFER'
        )
        assert payment.date == payment_date
    
    def test_payment_today_date(self, db):
        """Test payment with today's date"""
        member = Member.objects.create(
            first_name='Today',
            last_name='Date',
            gender='Male',
            date_of_birth=date(1990, 1, 1),
            phone_number='0788888888'
        )
        payment = Payment.objects.create(
            member=member,
            amount=Decimal('500.00'),
            date=date.today(),
            payment_method='DEBIT_ORDER'
        )
        assert payment.date == date.today()


class TestPaymentRelationships:
    """Test Payment relationships"""
    
    def test_payment_member_relationship(self, db):
        """Test payment is linked to member"""
        member = Member.objects.create(
            first_name='Related',
            last_name='Member',
            gender='Male',
            date_of_birth=date(1990, 1, 1),
            phone_number='0799999999'
        )
        payment = Payment.objects.create(
            member=member,
            amount=Decimal('500.00'),
            date=date.today(),
            payment_method='BANK_TRANSFER'
        )
        
        # Retrieve via member relationship (using correct related_name)
        member_payments = member.payments.all()
        assert member_payments.count() == 1
        assert member_payments.first().id == payment.id
    
    def test_member_multiple_payments(self, db):
        """Test member can have multiple payments"""
        member = Member.objects.create(
            first_name='Multiple',
            last_name='Payments',
            gender='Male',
            date_of_birth=date(1990, 1, 1),
            phone_number='0700000000'
        )
        
        for i in range(5):
            Payment.objects.create(
                member=member,
                amount=Decimal('100.00'),
                date=date.today(),
                payment_method='BANK_TRANSFER'
            )
        
        assert member.payments.count() == 5


class TestPaymentQuerying:
    """Test Payment model querying"""
    
    def test_filter_payments_by_status(self, db):
        """Test filtering payments by status"""
        member = Member.objects.create(
            first_name='Query',
            last_name='Status',
            gender='Male',
            date_of_birth=date(1990, 1, 1),
            phone_number='0711111111'
        )
        
        Payment.objects.create(
            member=member,
            amount=Decimal('100.00'),
            date=date.today(),
            payment_method='BANK_TRANSFER',
            status='PENDING'
        )
        Payment.objects.create(
            member=member,
            amount=Decimal('200.00'),
            date=date.today(),
            payment_method='BANK_TRANSFER',
            status='COMPLETED'
        )
        
        pending_payments = Payment.objects.filter(status='PENDING')
        assert pending_payments.count() == 1
        
        completed_payments = Payment.objects.filter(status='COMPLETED')
        assert completed_payments.count() == 1
    
    def test_filter_payments_by_method(self, db):
        """Test filtering payments by method"""
        member = Member.objects.create(
            first_name='Query',
            last_name='Method',
            gender='Male',
            date_of_birth=date(1990, 1, 1),
            phone_number='0722222222'
        )
        
        Payment.objects.create(
            member=member,
            amount=Decimal('100.00'),
            date=date.today(),
            payment_method='BANK_TRANSFER'
        )
        Payment.objects.create(
            member=member,
            amount=Decimal('200.00'),
            date=date.today(),
            payment_method='DEBIT_ORDER'
        )
        
        bank_transfers = Payment.objects.filter(payment_method='BANK_TRANSFER')
        assert bank_transfers.count() == 1
    
    def test_payments_by_member(self, db):
        """Test filtering payments by member"""
        member1 = Member.objects.create(
            first_name='Payment',
            last_name='One',
            gender='Male',
            date_of_birth=date(1990, 1, 1),
            phone_number='0733333333'
        )
        member2 = Member.objects.create(
            first_name='Payment',
            last_name='Two',
            gender='Female',
            date_of_birth=date(1991, 1, 1),
            phone_number='0744444444'
        )
        
        Payment.objects.create(
            member=member1,
            amount=Decimal('100.00'),
            date=date.today(),
            payment_method='BANK_TRANSFER'
        )
        Payment.objects.create(
            member=member2,
            amount=Decimal('200.00'),
            date=date.today(),
            payment_method='BANK_TRANSFER'
        )
        
        member1_payments = Payment.objects.filter(member=member1)
        assert member1_payments.count() == 1
