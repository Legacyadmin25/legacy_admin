from django.db import models
from django.conf import settings
from django.contrib.auth.models import Group
from django.contrib.auth import get_user_model
from schemes.models import Scheme

# Get the custom User model
User = get_user_model()

ROLE_SUPER_ADMIN = 'ROLE_SUPER_ADMIN'
ROLE_ADMIN = 'ROLE_ADMIN'
ROLE_BRANCH_ADMIN = 'ROLE_BRANCH_ADMIN'
ROLE_SCHEME_ADMIN = 'ROLE_SCHEME_ADMIN'
ROLE_CAPTURER = 'ROLE_CAPTURER'

ROLES = (
    (ROLE_SUPER_ADMIN, 'Super User'),
    (ROLE_ADMIN, 'Administrative User'),
    (ROLE_BRANCH_ADMIN, 'Branch User'),
    (ROLE_SCHEME_ADMIN, 'Scheme User'),
    (ROLE_CAPTURER, 'Capturer'),
)

def create_roles():
    for role_code, role_name in ROLES:
        Group.objects.get_or_create(name=role_code)


class SchemeUser(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    scheme = models.ForeignKey(Scheme, on_delete=models.CASCADE)

    def __str__(self):
        return self.user.username

class Capturer(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    scheme = models.ForeignKey(Scheme, on_delete=models.CASCADE)

    def __str__(self):
        return self.user.username
