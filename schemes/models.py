from django.db import models
from branches.models import Branch

class Scheme(models.Model):
    # — assign each Scheme to a Branch
    branch = models.ForeignKey(
        Branch,
        on_delete=models.CASCADE,
        related_name="schemes",
        help_text="Which branch this scheme belongs to"
    )

    name = models.CharField(max_length=200, unique=True)
    prefix = models.CharField(max_length=20, blank=True, null=True, help_text="Short code like CHB-001")

    registration_no = models.CharField(max_length=100)
    fsp_number = models.CharField(max_length=50)
    email = models.EmailField()
    extra_email = models.EmailField(blank=True, null=True, help_text="Additional email address")
    phone = models.CharField(max_length=20)
    logo = models.ImageField(upload_to='logos/', blank=True, null=True)
    terms = models.TextField(blank=True)
    debit_order_no = models.CharField(max_length=50)
    bank_name = models.CharField(max_length=100)
    branch_code = models.CharField(max_length=20)
    account_no = models.CharField(max_length=50)
    account_type = models.CharField(
        max_length=50,
        choices=[('Savings', 'Savings'), ('Current', 'Current')]
    )

    address = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    province = models.CharField(max_length=100, blank=True, null=True)
    village = models.CharField(max_length=100, blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)
    postal_code = models.CharField(max_length=20, blank=True, null=True)
    allow_auto_policy_number = models.BooleanField(default=False)
    active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.branch.name})"



class Plan(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    POLICY_TYPE_CHOICES = [
        ('service', 'Service Based'),
        ('cash', 'Cash Based'),
    ]
    policy_type = models.CharField(max_length=20, choices=POLICY_TYPE_CHOICES, default='service')
    premium = models.DecimalField(max_digits=10, decimal_places=2)
    underwriter = models.CharField(max_length=100, blank=True, default='')
    scheme = models.ForeignKey(Scheme, on_delete=models.CASCADE, related_name="plans")
    min_age = models.PositiveIntegerField(default=0)
    max_age = models.PositiveIntegerField(default=100)

    # Policy Details
    main_cover = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    main_premium = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    main_uw_cover = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    main_uw_premium = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    main_age_from = models.PositiveIntegerField(default=0)
    main_age_to = models.PositiveIntegerField(default=100)
    waiting_period = models.PositiveIntegerField(default=6)
    lapse_period = models.PositiveIntegerField(default=2)
    
    # Member Allowances
    spouses_allowed = models.PositiveIntegerField(default=0)
    children_allowed = models.PositiveIntegerField(default=0)
    extended_allowed = models.PositiveIntegerField(default=0)

    # Fee Distribution
    admin_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    cash_payout = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    agent_commission = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    office_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    scheme_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    manager_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    loyalty_programme = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    other_fees = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Terms & Conditions
    terms_text = models.TextField(blank=True, null=True, help_text="Terms and conditions text if no PDF is available")
    terms_pdf = models.FileField(upload_to='plan_terms/', blank=True, null=True, help_text="PDF document containing terms and conditions")

    # Other Settings
    is_active = models.BooleanField(default=True)
    is_diy_visible = models.BooleanField(default=True, help_text="Whether this plan is visible in the DIY application flow")

    modified = models.DateField(auto_now=True)

    def __str__(self):
        return self.name


class PlanTier(models.Model):
    """Tiered pricing structure for plans based on member type and age range"""
    
    USER_TYPE_CHOICES = [
        ('main', 'Main Member'),
        ('spouse', 'Spouse'),
        ('child', 'Child'),
        ('extended', 'Extended Family'),
    ]
    
    plan = models.ForeignKey(Plan, on_delete=models.CASCADE, related_name='plan_tiers')
    user_type = models.CharField(max_length=20, choices=USER_TYPE_CHOICES)
    age_from = models.PositiveIntegerField(default=0)
    age_to = models.PositiveIntegerField(default=100)
    cover_amount = models.DecimalField(max_digits=10, decimal_places=2)
    premium_amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.CharField(max_length=255, blank=True, null=True)
    
    class Meta:
        verbose_name = 'Plan Tier'
        verbose_name_plural = 'Plan Tiers'
        ordering = ['plan', 'user_type', 'age_from']
        unique_together = [('plan', 'user_type', 'age_from', 'age_to')]
    
    def __str__(self):
        return f"{self.plan.name} - {self.get_user_type_display()} ({self.age_from}-{self.age_to})"
