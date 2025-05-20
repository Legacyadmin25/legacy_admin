import factory
from django.contrib.auth import get_user_model
from members.models import Policy, Member
from schemes.models import Scheme, Plan
from branches.models import Branch
from datetime import date, timedelta

User = get_user_model()

class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    username = factory.Sequence(lambda n: f'user_{n}')
    email = factory.LazyAttribute(lambda u: f'{u.username}@example.com')
    password = factory.PostGenerationMethodCall('set_password', 'password')
    is_active = True
    phone = factory.Faker('phone_number')
    date_of_birth = factory.Faker('date_of_birth', minimum_age=18, maximum_age=80)

class BranchFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Branch

    name = factory.Sequence(lambda n: f'Branch {n}')
    code = factory.Sequence(lambda n: f'BRANCH_{n}')
    active = True

class SchemeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Scheme

    branch = factory.SubFactory(BranchFactory)
    name = factory.Sequence(lambda n: f'Scheme {n}')
    prefix = factory.Sequence(lambda n: f'SCH{n}')
    registration_no = factory.Sequence(lambda n: f'REG{n:05d}')
    fsp_number = factory.Sequence(lambda n: f'FSP{n:05d}')
    email = factory.Faker('email')
    phone = factory.Faker('phone_number')
    active = True

class PlanFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Plan

    name = factory.Sequence(lambda n: f'Plan {n}')
    scheme = factory.SubFactory(SchemeFactory)
    description = factory.Faker('paragraph')
    policy_type = 'cash'
    base_premium = 100.00
    spouses_allowed = 1
    children_allowed = 4
    extended_allowed = 8
    active = True

class MemberFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Member

    title = 'Mr'
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')
    id_number = factory.Sequence(lambda n: f'9001{n:06d}5009087')  # SA ID format
    gender = factory.Iterator(['Male', 'Female'])
    date_of_birth = factory.LazyFunction(lambda: date.today() - timedelta(days=365*30))
    phone_number = factory.Faker('phone_number')
    whatsapp_number = factory.Faker('phone_number')
    email = factory.Faker('email')

class PolicyFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Policy

    policy_number = factory.Sequence(lambda n: f'POL-{n:06d}')
    member = factory.SubFactory(MemberFactory)
    scheme = factory.SubFactory(SchemeFactory)
    plan = factory.SubFactory(PlanFactory)
    start_date = factory.LazyFunction(date.today)
    inception_date = factory.LazyFunction(date.today)
    cover_date = factory.LazyFunction(date.today)
    is_complete = True
    payment_method = 'DEBIT_ORDER'
    premium_amount = factory.LazyAttribute(lambda o: o.plan.base_premium)
    cover_amount = factory.LazyAttribute(lambda o: o.premium_amount * 100)
    lapse_warning = 'none'
