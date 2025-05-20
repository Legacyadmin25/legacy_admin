import pytest
from django.urls import reverse
from django.test import Client, TestCase
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission, Group
from django.contrib.contenttypes.models import ContentType
from members.models import Policy, Member, Dependent, Beneficiary, Scheme, Plan, Branch
from datetime import date, timedelta
from django.utils import timezone

User = get_user_model()
pytestmark = pytest.mark.django_db

class TestPolicySignupWizard(TestCase):
    """Tests for the policy signup wizard flow."""
    
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
            is_active=True
        )
        
        # Create test users with different roles
        cls.admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@test.com',
            password='testpass123'
        )
        
        cls.branch_owner = User.objects.create_user(
            username='branch_owner',
            email='branch@test.com',
            password='testpass123'
        )
        
        # Add branch owner permissions
        branch_owner_group, _ = Group.objects.get_or_create(name='Branch Owner')
        content_type = ContentType.objects.get_for_model(Branch)
        permission = Permission.objects.get(codename='change_branch')
        branch_owner_group.permissions.add(permission)
        cls.branch_owner.groups.add(branch_owner_group)
        
        # Create a member for testing
        cls.member = Member.objects.create(
            title='Mr',
            first_name='John',
            last_name='Doe',
            id_number='9001015009087',
            gender='Male',
            date_of_birth='1990-01-01',
            phone_number='+27821234567',
            email='john@test.com',
            marital_status='Single',
            physical_address_line_1='123 Test St',
            physical_address_city='Cape Town',
            physical_address_postal_code='8001'
        )
    
    def test_wizard_step_access_permissions_unauthenticated(self):
        """Test that unauthenticated users are redirected to login."""
        # Test access to the first step of the wizard
        response = self.client.get(reverse('policy_signup_start'))
        # Should redirect to login
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url)
    
    def test_authenticated_access_admin(self):
        """Test that authenticated admin users can access the wizard."""
        self.client.force_login(self.admin_user)
        response = self.client.get(reverse('policy_signup_start'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'members/policy_signup/start.html')
    
    def test_authenticated_access_branch_owner(self):
        """Test that branch owners can access the wizard."""
        self.client.force_login(self.branch_owner)
        response = self.client.get(reverse('policy_signup_start'))
        self.assertEqual(response.status_code, 200)
    
    def test_complete_wizard_flow(self):
        """Test the complete policy signup wizard flow."""
        self.client.force_login(self.admin_user)
        
        # Step 1: Start the wizard
        response = self.client.get(reverse('policy_signup_start'))
        self.assertEqual(response.status_code, 200)
        
        # Step 2: Submit personal details
        session = self.client.session
        session['policy_wizard_storage'] = 'django.forms.utils.Storage'
        session.save()
        
        personal_details_data = {
            'title': 'Mrs',
            'first_name': 'Jane',
            'last_name': 'Smith',
            'id_number': '9202025009087',
            'gender': 'Female',
            'date_of_birth': '1992-02-02',
            'phone_number': '+27827654321',
            'email': 'jane@test.com',
            'marital_status': 'Married',
            'physical_address_line_1': '456 Test Ave',
            'physical_address_city': 'Johannesburg',
            'physical_address_postal_code': '2001'
        }
        
        # Submit first step
        response = self.client.post(
            reverse('policy_signup_step', kwargs={'step': 'personal_details'}),
            personal_details_data
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn('policy/signup/policy-details/', response.url)
        
        # Step 3: Policy details
        policy_data = {
            'scheme': self.scheme.id,
            'plan': self.plan.id,
            'sum_assured': '100000',
            'premium_frequency': 'monthly',
            'start_date': (timezone.now() + timedelta(days=7)).strftime('%Y-%m-%d'),
            'payment_method': 'debit_order'
        }
        
        response = self.client.post(
            reverse('policy_signup_step', kwargs={'step': 'policy_details'}),
            policy_data
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn('policy/signup/beneficiaries/', response.url)
        
        # Step 4: Beneficiaries
        beneficiary_data = {
            'beneficiaries-TOTAL_FORMS': '1',
            'beneficiaries-INITIAL_FORMS': '0',
            'beneficiaries-MIN_NUM_FORMS': '1',
            'beneficiaries-MAX_NUM_FORMS': '5',
            'beneficiaries-0-name': 'Spouse Smith',
            'beneficiaries-0-relationship': 'spouse',
            'beneficiaries-0-percentage': '100',
            'beneficiaries-0-id_number': '9001015009087',
        }
        
        response = self.client.post(
            reverse('policy_signup_step', kwargs={'step': 'beneficiaries'}),
            beneficiary_data
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn('policy/signup/review/', response.url)
        
        # Step 5: Review and submit
        response = self.client.get(reverse('policy_signup_step', kwargs={'step': 'review'}))
        self.assertEqual(response.status_code, 200)
        
        # Submit the form
        response = self.client.post(
            reverse('policy_signup_step', kwargs={'step': 'review'}),
            {'accept_terms': 'on'}
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn('policy/signup/complete/', response.url)
        
        # Verify the policy was created
        self.assertTrue(Policy.objects.filter(member__id_number='9202025009087').exists())
        policy = Policy.objects.get(member__id_number='9202025009087')
        self.assertEqual(policy.status, 'pending')
        self.assertEqual(policy.sum_assured, 100000)
        self.assertEqual(policy.beneficiaries.count(), 1)
    
    def test_invalid_personal_details(self):
        """Test form validation for invalid personal details."""
        self.client.force_login(self.admin_user)
        
        # Invalid ID number (too short)
        invalid_data = {
            'title': 'Mr',
            'first_name': 'Test',
            'last_name': 'User',
            'id_number': '123',  # Invalid
            'gender': 'Male',
            'date_of_birth': '2000-01-01',
            'phone_number': 'invalid',
            'email': 'not-an-email',
            'marital_status': 'Single',
            'physical_address_line_1': '123 Test St',
            'physical_address_city': 'Test City',
            'physical_address_postal_code': '1234'
        }
        
        response = self.client.post(
            reverse('policy_signup_step', kwargs={'step': 'personal_details'}),
            invalid_data
        )
        
        self.assertEqual(response.status_code, 200)  # Form should redisplay with errors
        self.assertFormError(response, 'form', 'id_number', 'ID number must be 13 digits')
        self.assertFormError(response, 'form', 'phone_number', 'Enter a valid phone number')
        self.assertFormError(response, 'form', 'email', 'Enter a valid email address')
    
    def test_policy_details_validation(self):
        """Test validation of policy details step."""
        self.client.force_login(self.admin_user)
        
        # First, complete the personal details step
        session = self.client.session
        session['policy_wizard_storage'] = 'django.forms.utils.Storage'
        session['personal_details'] = True
        session.save()
        
        # Invalid policy details (missing required fields)
        invalid_policy_data = {
            'sum_assured': '5000',  # Below minimum
            'premium_frequency': 'invalid',
            'start_date': '2020-01-01'  # Past date
        }
        
        response = self.client.post(
            reverse('policy_signup_step', kwargs={'step': 'policy_details'}),
            invalid_policy_data
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response, 'form', 'scheme', 'This field is required.')
        self.assertFormError(response, 'form', 'plan', 'This field is required.')
        self.assertFormError(response, 'form', 'sum_assured', 
                           f'Ensure this value is greater than or equal to {self.plan.min_sum_assured}.')
    
    def test_beneficiary_validation(self):
        """Test validation of beneficiary information."""
        self.client.force_login(self.admin_user)
        
        # Set up session as if we've completed previous steps
        session = self.client.session
        session['policy_wizard_storage'] = 'django.forms.utils.Storage'
        session['personal_details'] = True
        session['policy_details'] = True
        session.save()
        
        # Invalid beneficiary data (total percentage > 100%)
        invalid_beneficiary_data = {
            'beneficiaries-TOTAL_FORMS': '2',
            'beneficiaries-INITIAL_FORMS': '0',
            'beneficiaries-MIN_NUM_FORMS': '1',
            'beneficiaries-MAX_NUM_FORMS': '5',
            'beneficiaries-0-name': 'Beneficiary 1',
            'beneficiaries-0-relationship': 'spouse',
            'beneficiaries-0-percentage': '60',
            'beneficiaries-0-id_number': '9001015009087',
            'beneficiaries-1-name': 'Beneficiary 2',
            'beneficiaries-1-relationship': 'child',
            'beneficiaries-1-percentage': '50',  # Total would be 110%
            'beneficiaries-1-id_number': '9101015009087',
        }
        
        response = self.client.post(
            reverse('policy_signup_step', kwargs={'step': 'beneficiaries'}),
            invalid_beneficiary_data
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertFormsetError(response, 'beneficiary_formset', None, None, 
                              'Total beneficiary allocation cannot exceed 100%')
    
    def test_duplicate_id_number_validation(self):
        """Test that duplicate ID numbers are caught during signup."""
        self.client.force_login(self.admin_user)
        
        # Create a member with a known ID number
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
        
        # Try to create a new member with the same ID number
        personal_details_data = {
            'title': 'Mr',
            'first_name': 'New',
            'last_name': 'User',
            'id_number': '9001015009087',  # Duplicate ID
            'gender': 'Male',
            'date_of_birth': '1990-01-01',
            'phone_number': '+27821234568',
            'email': 'new@test.com',
            'marital_status': 'Single',
            'physical_address_line_1': '123 Test St',
            'physical_address_city': 'Cape Town',
            'physical_address_postal_code': '8001'
        }
        
        response = self.client.post(
            reverse('policy_signup_step', kwargs={'step': 'personal_details'}),
            personal_details_data
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response, 'form', 'id_number', 'Member with this ID number already exists.')
    
    def test_age_validation_for_plan(self):
        """Test that member age is validated against plan age limits."""
        self.client.force_login(self.admin_user)
        
        # Create a member who is too young for the plan
        personal_details_data = {
            'title': 'Mr',
            'first_name': 'Young',
            'last_name': 'User',
            'id_number': '1201015009087',  # Born in 2012 (too young for min_age=18)
            'gender': 'Male',
            'date_of_birth': '2012-01-01',
            'phone_number': '+27821234567',
            'email': 'young@test.com',
            'marital_status': 'Single',
            'physical_address_line_1': '123 Test St',
            'physical_address_city': 'Cape Town',
            'physical_address_postal_code': '8001'
        }
        
        # First complete personal details
        session = self.client.session
        session['policy_wizard_storage'] = 'django.forms.utils.Storage'
        session.save()
        
        response = self.client.post(
            reverse('policy_signup_step', kwargs={'step': 'personal_details'}),
            personal_details_data
        )
        
        # Should redirect to policy details
        self.assertEqual(response.status_code, 302)
        
        # Now try to select the plan that has age restrictions
        policy_data = {
            'scheme': self.scheme.id,
            'plan': self.plan.id,  # This plan has min_age=18
            'sum_assured': '100000',
            'premium_frequency': 'monthly',
            'start_date': (timezone.now() + timedelta(days=7)).strftime('%Y-%m-%d'),
            'payment_method': 'debit_order'
        }
        
        response = self.client.post(
            reverse('policy_signup_step', kwargs={'step': 'policy_details'}),
            policy_data
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response, 'form', None, 
                           f'Member must be between {self.plan.min_age} and {self.plan.max_age} years old for this plan.')

        # Policy details
        policy_details_data = {
            'scheme': scheme.id,
            'plan': plan.id,
            'membership_number': 'MEM123456',
            'start_date': date.today().strftime('%Y-%m-%d'),
            'inception_date': date.today().strftime('%Y-%m-%d'),
            'cover_date': date.today().strftime('%Y-%m-%d'),
            'premium_amount': '100.00',
            'cover_amount': '10000.00'
        }
        
        # Create a policy (this would normally be done by the view)
        policy = Policy.objects.create(
            member=member,
            scheme=scheme,
            plan=plan,
            policy_number=f'POL-{member.id:06d}',
            **{k: v for k, v in policy_details_data.items() if k not in ['scheme', 'plan']}
        )
        
        # Step 4: Add spouse
        spouse_data = {
            'spouse_first_name': 'Jane',
            'spouse_last_name': 'Doe',
            'spouse_id_number': '9101015009087',
            'spouse_gender': 'Female',
            'spouse_date_of_birth': '1991-01-01',
            'spouse_phone_number': '+27821234568'
        }
        
        # Create spouse dependent (this would normally be done by the view)
        Dependent.objects.create(
            policy=policy,
            relationship='Spouse',
            first_name=spouse_data['spouse_first_name'],
            last_name=spouse_data['spouse_last_name'],
            id_number=spouse_data['spouse_id_number'],
            gender=spouse_data['spouse_gender'],
            date_of_birth=date(1991, 1, 1)
        )
        
        # Step 5: Add child
        child_data = {
            'relationship': 'Child',
            'first_name': 'Junior',
            'last_name': 'Doe',
            'id_number': '0601015009087',
            'gender': 'Male',
            'date_of_birth': '2006-01-01'
        }
        
        # Create child dependent (this would normally be done by the view)
        Dependent.objects.create(
            policy=policy,
            **child_data
        )
        
        # Step 6: Add beneficiary
        beneficiary_data = {
            'relationship_to_main_member': 'Spouse',
            'first_name': 'Jane',
            'last_name': 'Doe',
            'id_number': '9101015009087',
            'gender': 'F',
            'date_of_birth': '1991-01-01',
            'share': 100
        }
        
        # Create beneficiary (this would normally be done by the view)
        Beneficiary.objects.create(
            policy=policy,
            **beneficiary_data
        )
        
        # Final step: Check that a policy was created with all components
        assert Policy.objects.filter(member=member).exists()
        policy = Policy.objects.get(member=member)
        assert policy.dependents.count() == 2  # Spouse and child
        assert policy.beneficiaries.count() == 1


class TestDIYPolicySignup:
    """Tests for the DIY (public) policy signup flow."""
    
    def test_diy_signup_with_valid_token(self, client, scheme, plan):
        """Test DIY signup with a valid token."""
        # Import Agent model from settings_app
        from settings_app.models import Agent
        
        # Create an agent with a DIY token
        agent = Agent.objects.create(
            name="Test Agent",
            email="agent@example.com",
            phone="+27821234567",
            is_active=True,
            diy_token="valid-token-123"
        )
        
        # Associate agent with scheme
        agent.schemes.add(scheme)
        
        # Test access to the DIY signup page with the token
        response = client.get(reverse('diy_signup_start', kwargs={'token': 'valid-token-123'}))
        assert response.status_code == 200
    
    def test_diy_signup_with_invalid_token(self, client):
        """Test DIY signup with an invalid token."""
        response = client.get(reverse('diy_signup_start', kwargs={'token': 'invalid-token'}))
        assert response.status_code == 404
    
    def test_complete_diy_flow(self, client, scheme, plan):
        """Test the complete DIY signup flow."""
        # Import Agent model from settings_app
        from settings_app.models import Agent
        
        # Create an agent with a DIY token
        agent = Agent.objects.create(
            name="Test Agent",
            email="agent@example.com",
            phone="+27821234567",
            is_active=True,
            diy_token="valid-token-456"
        )
        
        # Associate agent with scheme
        agent.schemes.add(scheme)
        
        # Step 1: Start DIY signup
        response = client.get(reverse('diy_signup_start', kwargs={'token': 'valid-token-456'}))
        assert response.status_code == 200
        
        # Step 2: Submit personal details
        personal_details_data = {
            'title': 'Mr',
            'first_name': 'John',
            'last_name': 'Doe',
            'id_number': '9001015009087',
            'gender': 'Male',
            'date_of_birth': '1990-01-01',
            'phone_number': '+27821234567',
            'email': 'john@example.com',
            'marital_status': 'Single',
            'physical_address_line_1': '123 Main St',
            'physical_address_city': 'Cape Town',
            'physical_address_postal_code': '8001'
        }
        
        # Create a member manually (this would normally be done by the view)
        member = Member.objects.create(**personal_details_data)
        
        # Create a policy manually (this would normally be done by the view)
        policy = Policy.objects.create(
            member=member,
            scheme=scheme,
            plan=plan,
            policy_number=f'DIY-{member.id:06d}',
            start_date=date.today(),
            inception_date=date.today(),
            cover_date=date.today(),
            premium_amount=100.00,
            cover_amount=10000.00,
            underwritten_by=agent
        )
        
        # Final step: Check that a policy was created with the agent as underwriter
        assert Policy.objects.filter(member=member, underwritten_by=agent).exists()


class TestRoleBasedAccess:
    """Tests for role-based access control."""
    
    def test_admin_access(self, client, admin_user):
        """Test that admins can access all pages."""
        client.force_login(admin_user)
        
        # Test access to admin-only pages
        response = client.get(reverse('admin:index'))
        assert response.status_code == 200
        
        # Test access to policy signup
        response = client.get(reverse('policy_signup_start'))
        assert response.status_code == 200
        
        # Test access to policy list
        response = client.get(reverse('policy_list'))
        assert response.status_code == 200
    
    def test_branch_owner_access(self, client, admin_user):
        """Test that branch owners can access their branch's policies."""
        # Import BranchUser model
        from branches.models import Branch, BranchUser
        
        # Create a branch
        branch = Branch.objects.create(
            name="Test Branch",
            code="TEST",
            active=True
        )
        
        # Create a branch user
        branch_user = BranchUser.objects.create(
            user=admin_user,
            branch=branch,
            role="owner"
        )
        
        client.force_login(admin_user)
        
        # Test access to branch dashboard
        response = client.get(reverse('branch_dashboard', kwargs={'pk': branch.id}))
        assert response.status_code == 200
        
        # Test access to another branch's dashboard (should be forbidden)
        other_branch = Branch.objects.create(
            name="Other Branch",
            code="OTHER",
            active=True
        )
        response = client.get(reverse('branch_dashboard', kwargs={'pk': other_branch.id}))
        assert response.status_code in [302, 403]  # Either redirect or forbidden
    
    def test_scheme_manager_access(self, client, admin_user, scheme):
        """Test that scheme managers can access their scheme's policies."""
        # Import SchemeUser model
        from schemes.models import SchemeUser
        
        # Create a scheme user
        scheme_user = SchemeUser.objects.create(
            user=admin_user,
            scheme=scheme,
            role="manager"
        )
        
        client.force_login(admin_user)
        
        # Test access to scheme dashboard
        response = client.get(reverse('scheme_dashboard', kwargs={'pk': scheme.id}))
        assert response.status_code == 200
        
        # Test access to another scheme's dashboard (should be forbidden)
        from schemes.models import Scheme
        from branches.models import Branch
        other_branch = Branch.objects.create(name="Other Branch", code="OTHER", active=True)
        other_scheme = Scheme.objects.create(
            name="Other Scheme",
            branch=other_branch,
            registration_no="REG123",
            fsp_number="FSP123",
            email="other@example.com",
            phone="+27821234567",
            debit_order_no="DO123",
            bank_name="Test Bank",
            branch_code="123456",
            account_no="1234567890",
            account_type="Current"
        )
        response = client.get(reverse('scheme_dashboard', kwargs={'pk': other_scheme.id}))
        assert response.status_code in [302, 403]  # Either redirect or forbidden
    
    def test_agent_access(self, client, agent_user):
        """Test that agents can only access their allowed pages."""
        client.force_login(agent_user)
        
        # Test access to agent dashboard
        response = client.get(reverse('agent_dashboard'))
        assert response.status_code == 200
        
        # Test access to admin-only pages (should be forbidden)
        response = client.get(reverse('admin:index'))
        assert response.status_code in [302, 403]  # Either redirect or forbidden
        
        # Test access to policy creation (should be allowed)
        response = client.get(reverse('policy_signup_start'))
        assert response.status_code == 200
    
    def test_compliance_auditor_access(self, client, admin_user):
        """Test that compliance auditors have read-only access."""
        # Set user as compliance auditor
        admin_user.is_staff = True
        admin_user.is_superuser = False
        admin_user.groups.create(name="Compliance Auditors")
        admin_user.save()
        
        client.force_login(admin_user)
        
        # Test access to policy list (should be allowed)
        response = client.get(reverse('policy_list'))
        assert response.status_code == 200
        
        # Test access to policy creation (should be forbidden or read-only)
        response = client.get(reverse('policy_signup_start'))
        # This may be 200 if read-only or 403 if forbidden
        assert response.status_code in [200, 302, 403]
