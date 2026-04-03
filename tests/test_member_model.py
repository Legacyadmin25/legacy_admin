"""
Unit tests for Member model
"""
import pytest
from datetime import date
from members.models import Member


class TestMemberCreation:
    """Test Member model creation and basic fields"""
    
    def test_member_can_be_created(self, db):
        """Test creating a member with required fields"""
        member = Member.objects.create(
            first_name='John',
            last_name='Doe',
            gender='Male',
            date_of_birth=date(1990, 1, 1),
            phone_number='0712345678'
        )
        assert member.id is not None
        assert member.first_name == 'John'
        assert member.last_name == 'Doe'
    
    def test_member_string_representation(self, db):
        """Test Member __str__ returns proper name"""
        member = Member.objects.create(
            first_name='Jane',
            last_name='Smith',
            gender='Female',
            date_of_birth=date(1985, 5, 15),
            phone_number='0787654321'
        )
        assert str(member) == 'Jane Smith'
    
    def test_member_email_optional(self, db):
        """Test Member can be created without email"""
        member = Member.objects.create(
            first_name='Bob',
            last_name='Johnson',
            gender='Male',
            date_of_birth=date(1988, 3, 20),
            phone_number='0768901234'
        )
        assert member.email == '' or member.email is None or member.email == ''


class TestMemberFields:
    """Test individual Member fields"""
    
    def test_member_with_title(self, db):
        """Test Member with title field"""
        member = Member.objects.create(
            title='Dr',
            first_name='John',
            last_name='Doe',
            gender='Male',
            date_of_birth=date(1985, 6, 10),
            phone_number='0712222222'
        )
        assert member.title == 'Dr'
    
    def test_member_with_gender_options(self, db):
        """Test Member gender field accepts valid options"""
        male_member = Member.objects.create(
            first_name='Male',
            last_name='Test',
            gender='Male',
            date_of_birth=date(1990, 1, 1),
            phone_number='0711111111'
        )
        female_member = Member.objects.create(
            first_name='Female',
            last_name='Test',
            gender='Female',
            date_of_birth=date(1990, 1, 1),
            phone_number='0722222222'
        )
        assert male_member.gender == 'Male'
        assert female_member.gender == 'Female'
    
    def test_member_with_marital_status(self, db):
        """Test Member marital_status field"""
        member = Member.objects.create(
            first_name='John',
            last_name='Married',
            gender='Male',
            date_of_birth=date(1985, 1, 1),
            phone_number='0733333333',
            marital_status='Married'
        )
        assert member.marital_status == 'Married'
    
    def test_member_with_nationality(self, db):
        """Test Member nationality field"""
        member = Member.objects.create(
            first_name='John',
            last_name='Doe',
            gender='Male',
            date_of_birth=date(1985, 1, 1),
            phone_number='0744444444',
            nationality='South African'
        )
        assert member.nationality == 'South African'


class TestMemberAddress:
    """Test Member address fields"""
    
    def test_member_with_address_fields(self, db):
        """Test Member with complete address information"""
        member = Member.objects.create(
            first_name='John',
            last_name='Doe',
            gender='Male',
            date_of_birth=date(1990, 1, 1),
            phone_number='0755555555',
            physical_address_line_1='123 Main Street',
            physical_address_city='Johannesburg',
            physical_address_postal_code='2000'
        )
        assert member.physical_address_line_1 == '123 Main Street'
        assert member.physical_address_city == 'Johannesburg'
    
    def test_member_address_optional(self, db):
        """Test Member address fields are optional"""
        member = Member.objects.create(
            first_name='Jane',
            last_name='Smith',
            gender='Female',
            date_of_birth=date(1985, 1, 1),
            phone_number='0766666666'
        )
        assert member.physical_address_line_1 == '' or member.physical_address_line_1 is None


class TestMemberSpouseFields:
    """Test Member spouse information fields"""
    
    def test_member_with_spouse_info(self, db):
        """Test Member with spouse information"""
        member = Member.objects.create(
            first_name='John',
            last_name='Married',
            gender='Male',
            date_of_birth=date(1985, 1, 1),
            phone_number='0777777777',
            spouse_first_name='Jane',
            spouse_last_name='Married',
            spouse_gender='Female'
        )
        assert member.spouse_first_name == 'Jane'
        assert member.spouse_last_name == 'Married'
    
    def test_member_spouse_fields_optional(self, db):
        """Test spouse fields are optional"""
        member = Member.objects.create(
            first_name='John',
            last_name='Single',
            gender='Male',
            date_of_birth=date(1990, 1, 1),
            phone_number='0788888888'
        )
        assert member.spouse_first_name == '' or member.spouse_first_name is None


class TestMemberConstraints:
    """Test Member model constraints and validation"""
    
    def test_member_multiple_with_same_name(self, db):
        """Test that multiple members can have the same name"""
        member1 = Member.objects.create(
            first_name='Common',
            last_name='Name',
            gender='Male',
            date_of_birth=date(1990, 1, 1),
            phone_number='0799999999'
        )
        member2 = Member.objects.create(
            first_name='Common',
            last_name='Name',
            gender='Female',
            date_of_birth=date(1992, 2, 2),
            phone_number='0700000000'
        )
        assert member1.id != member2.id
    
    def test_member_retrieval(self, db):
        """Test retrieving member by ID"""
        member = Member.objects.create(
            first_name='Retrieve',
            last_name='Test',
            gender='Male',
            date_of_birth=date(1990, 1, 1),
            phone_number='0711111111'
        )
        retrieved = Member.objects.get(id=member.id)
        assert retrieved.first_name == 'Retrieve'
        assert retrieved.last_name == 'Test'


class TestMemberQuerying:
    """Test Member model querying"""
    
    def test_filter_members_by_name(self, db):
        """Test filtering members by name"""
        Member.objects.create(
            first_name='John',
            last_name='Doe',
            gender='Male',
            date_of_birth=date(1990, 1, 1),
            phone_number='0711111111'
        )
        Member.objects.create(
            first_name='Jane',
            last_name='Doe',
            gender='Female',
            date_of_birth=date(1991, 1, 1),
            phone_number='0722222222'
        )
        does = Member.objects.filter(last_name='Doe')
        assert does.count() == 2
    
    def test_filter_members_by_gender(self, db):
        """Test filtering members by gender"""
        Member.objects.create(
            first_name='John',
            last_name='Male',
            gender='Male',
            date_of_birth=date(1990, 1, 1),
            phone_number='0733333333'
        )
        Member.objects.create(
            first_name='Jane',
            last_name='Female',
            gender='Female',
            date_of_birth=date(1991, 1, 1),
            phone_number='0744444444'
        )
        males = Member.objects.filter(gender='Male')
        assert males.count() == 1
        assert males.first().first_name == 'John'
    
    def test_member_count(self, db):
        """Test counting members"""
        for i in range(5):
            Member.objects.create(
                first_name=f'Member{i}',
                last_name='Test',
                gender='Male' if i % 2 == 0 else 'Female',
                date_of_birth=date(1990, 1, 1),
                phone_number=f'071{i:07d}'
            )
        assert Member.objects.count() == 5
