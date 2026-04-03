"""
Unit tests for accounts app: User model, authentication, permissions.
"""
import pytest
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User, Group
from accounts.models import User as CustomUser
from django.utils import timezone


class RoleBasedLoginTest(TestCase):
    """Original role-based login test"""
    
    def setUp(self):
        self.user_admin = User.objects.create_user(username='admin', password='testpassword')
        admin_group = Group.objects.create(name="Administrator")
        self.user_admin.groups.add(admin_group)
        self.user_admin.save()

    def test_admin_redirect(self):
        self.client.login(username='admin', password='testpassword')
        response = self.client.get(reverse('accounts:login'))
        self.assertRedirects(response, reverse('accounts:admin_dashboard'))


class TestUserModel(TestCase):
    """Test custom User model and its methods"""
    
    def setUp(self):
        """Create test users"""
        self.admin = CustomUser.objects.create_superuser(
            username='admin',
            email='admin@test.com',
            password='pass'
        )
        self.regular_user = CustomUser.objects.create_user(
            username='regular',
            email='user@test.com',
            password='pass',
            phone='0712345678',
            date_of_birth='1990-01-01',
            address='123 Main St',
            city='Johannesburg'
        )
    
    def test_user_creation(self):
        """Test that user can be created with all fields"""
        self.assertEqual(self.regular_user.username, 'regular')
        self.assertEqual(self.regular_user.phone, '0712345678')
        self.assertEqual(self.regular_user.city, 'Johannesburg')
    
    def test_user_is_active_by_default(self):
        """Test that new users are active by default"""
        self.assertTrue(self.regular_user.is_active)
    
    def test_superuser_creation(self):
        """Test superuser creation"""
        self.assertTrue(self.admin.is_superuser)
        self.assertTrue(self.admin.is_staff)
    
    def test_user_full_name_property(self):
        """Test full_name property"""
        self.regular_user.first_name = 'John'
        self.regular_user.last_name = 'Doe'
        self.regular_user.save()
        
        self.assertEqual(self.regular_user.get_full_name(), 'John Doe')
    
    def test_user_profile_property_backward_compat(self):
        """Test backward compatibility: user.profile returns self (Phase 3)"""
        self.assertEqual(self.regular_user.profile, self.regular_user)
    
    def test_user_string_representation(self):
        """Test __str__ returns username"""
        self.assertEqual(str(self.regular_user), 'regular')


class TestUserGroups(TestCase):
    """Test user groups and permission assignment"""
    
    def setUp(self):
        """Set up test user and groups"""
        self.user = CustomUser.objects.create_user(
            username='testuser',
            password='pass'
        )
        self.admin_group = Group.objects.create(name='Administrator')
        self.officer_group = Group.objects.create(name='Claims Officer')
        self.agent_group = Group.objects.create(name='Agent')
    
    def test_user_can_join_group(self):
        """Test adding user to a group"""
        self.user.groups.add(self.agent_group)
        self.assertIn(self.agent_group, self.user.groups.all())
    
    def test_user_can_join_multiple_groups(self):
        """Test user can be in multiple groups"""
        self.user.groups.add(self.agent_group, self.officer_group)
        self.assertEqual(self.user.groups.count(), 2)
    
    def test_user_group_removal(self):
        """Test removing user from group"""
        self.user.groups.add(self.agent_group)
        self.user.groups.remove(self.agent_group)
        self.assertNotIn(self.agent_group, self.user.groups.all())


class TestUserPasswordManagement(TestCase):
    """Test user password handling and security"""
    
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='passtest',
            password='original_pass123'
        )
    
    def test_password_is_hashed(self):
        """Test that passwords are stored hashed, not plain"""
        self.assertNotEqual(self.user.password, 'original_pass123')
        self.assertTrue(self.user.password.startswith('pbkdf2_sha256$'))
    
    def test_password_verification(self):
        """Test that correct password verifies"""
        self.assertTrue(self.user.check_password('original_pass123'))
    
    def test_wrong_password_fails(self):
        """Test that wrong password doesn't verify"""
        self.assertFalse(self.user.check_password('wrong_password'))
    
    def test_password_change(self):
        """Test changing user password"""
        self.user.set_password('new_pass123')
        self.user.save()
        
        self.assertTrue(self.user.check_password('new_pass123'))
        self.assertFalse(self.user.check_password('original_pass123'))


class TestUserPermissions(TestCase):
    """Test user permission checking"""
    
    def setUp(self):
        self.admin = CustomUser.objects.create_superuser(
            username='admin',
            password='pass'
        )
        self.regular = CustomUser.objects.create_user(
            username='regular',
            password='pass'
        )
    
    def test_superuser_has_all_permissions(self):
        """Test that superuser has all permissions"""
        self.assertTrue(self.admin.has_perm('auth.add_user'))
        self.assertTrue(self.admin.has_perm('auth.change_user'))
        self.assertTrue(self.admin.has_perm('auth.delete_user'))
    
    def test_superuser_is_staff(self):
        """Test that superuser is marked as staff"""
        self.assertTrue(self.admin.is_staff)


class TestUserProfileFields(TestCase):
    """Test user profile-related fields (consolidated from Profile model in Phase 3)"""
    
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='profile_test',
            password='pass',
            phone='0712345678',
            date_of_birth='1990-01-01',
            address='123 Main Street',
            city='Johannesburg',
            state='Gauteng',
            postal_code='2000',
            country='South Africa',
            bio='Test bio',
            is_verified=True
        )
    
    def test_phone_field_stored(self):
        """Test that phone field is stored"""
        user = CustomUser.objects.get(username='profile_test')
        self.assertEqual(user.phone, '0712345678')
    
    def test_date_of_birth_field_stored(self):
        """Test that DOB is stored"""
        user = CustomUser.objects.get(username='profile_test')
        self.assertIsNotNone(user.date_of_birth)
    
    def test_address_fields_stored(self):
        """Test that address fields are stored"""
        user = CustomUser.objects.get(username='profile_test')
        self.assertEqual(user.address, '123 Main Street')
        self.assertEqual(user.city, 'Johannesburg')
        self.assertEqual(user.state, 'Gauteng')
        self.assertEqual(user.postal_code, '2000')
        self.assertEqual(user.country, 'South Africa')
    
    def test_bio_field_stored(self):
        """Test that bio field is stored"""
        user = CustomUser.objects.get(username='profile_test')
        self.assertEqual(user.bio, 'Test bio')
    
    def test_is_verified_field(self):
        """Test that is_verified flag works"""
        user = CustomUser.objects.get(username='profile_test')
        self.assertTrue(user.is_verified)
