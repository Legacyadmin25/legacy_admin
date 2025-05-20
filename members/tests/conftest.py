import pytest
from django.contrib.auth import get_user_model
from . import factories

User = get_user_model()

@pytest.fixture
def client():
    from django.test import Client
    return Client()

@pytest.fixture
def admin_user():
    return factories.UserFactory(is_staff=True, is_superuser=True)

@pytest.fixture
def agent_user():
    return factories.UserFactory(is_staff=False, is_superuser=False)

@pytest.fixture
def scheme():
    return factories.SchemeFactory()

@pytest.fixture
def plan(scheme):
    return factories.PlanFactory(scheme=scheme)

@pytest.fixture
def member():
    return factories.MemberFactory()

@pytest.fixture
def policy(plan, member):
    return factories.PolicyFactory(plan=plan, member=member)
