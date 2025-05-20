from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User, Group

class RoleBasedLoginTest(TestCase):
    def setUp(self):
        self.user_admin = User.objects.create_user(username='admin', password='testpassword')
        admin_group = Group.objects.create(name="Administrator")
        self.user_admin.groups.add(admin_group)
        self.user_admin.save()

    def test_admin_redirect(self):
        self.client.login(username='admin', password='testpassword')
        response = self.client.get(reverse('accounts:login'))
        self.assertRedirects(response, reverse('accounts:admin_dashboard'))
