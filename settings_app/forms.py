import re
from datetime import datetime
from settings_app.utils.validation import is_strong_password
from django.core.exceptions import ValidationError

from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.contrib.auth.models import User, Group
from django.forms import inlineformset_factory

from sms_templates.models import SMSTemplate

from .models import (
    SchemeDocument,
    Agent,
    Underwriter,
    Branch,
    UserGroup,
    PlanMemberTier,
    USER_TYPE_CHOICES,
    UserProfile,
    UnderwriterDocument,
)
from schemes.models import Plan as SchemePlan
from schemes.models import Scheme as SchemeModel, Plan as SchemePlan
from members.models import Policy


# ─── Scheme Forms ───────────────────────────────────────────────────────
class SchemeForm(forms.ModelForm):
    class Meta:
        model = SchemeModel
        fields = [
    'branch', 'name', 'prefix', 'registration_no', 'fsp_number', 'email',
    'phone', 'logo', 'terms', 'debit_order_no', 'bank_name', 'branch_code',
    'account_no', 'account_type'
]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.required = False


class SchemeDocumentForm(forms.ModelForm):
    class Meta:
        model = SchemeDocument
        fields = ['name', 'file']


# ─── Agent Form ─────────────────────────────────────────────────────────
def luhn_checksum(id_number):
    def digits(n): return [int(d) for d in str(n)]
    digits_list = digits(id_number)
    odd = digits_list[-1::-2]
    even = digits_list[-2::-2]
    total = sum(odd)
    for d in even:
        total += sum(digits(d * 2))
    return total % 10 == 0

from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from settings_app.models import Agent
from schemes.models import Scheme
from settings_app.utils.validation import luhn_checksum  # adjust if it's elsewhere

class AgentForm(forms.ModelForm):
    class Meta:
        model = Agent
        fields = '__all__'
        widgets = {
            'commission_percentage': forms.TextInput(attrs={'placeholder': '%'}),
            'commission_rand_value': forms.TextInput(),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        if user and not user.is_superuser:
            if user.groups.filter(name='Branch Owner').exists():
                self.fields['scheme'].queryset = Scheme.objects.filter(branch=user.userprofile.branch)
            elif user.groups.filter(name='Scheme Admin').exists():
                self.fields['scheme'].queryset = Scheme.objects.filter(admin_user=user)

    def clean_id_number(self):
        idn = self.cleaned_data.get('id_number')
        if idn and (len(idn) != 13 or not idn.isdigit() or not luhn_checksum(idn)):
            raise ValidationError("Invalid South African ID number.")
        return idn

    def clean_contact_number(self):
        contact = self.cleaned_data.get('contact_number')
        if contact and (not contact.isdigit() or len(contact) != 10):
            raise ValidationError("Contact number must be exactly 10 digits.")
        return contact

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
            validate_email(email)
        return email


# ─── Underwriter Form ───────────────────────────────────────────────────
class UnderwriterForm(forms.ModelForm):
    class Meta:
        model = Underwriter
        fields = '__all__'
        widgets = {
            'logo': forms.ClearableFileInput(),
        }

# ─── Underwriter Document Form ───────────────────────────────────────────────────
from .models import UnderwriterDocument  # Assuming you have an UnderwriterDocument model

class UnderwriterDocumentForm(forms.ModelForm):
    class Meta:
        model = UnderwriterDocument  # Replace with your actual model
        fields = ['name', 'document']  # Replace with your actual fields


# ─── Branch Form ────────────────────────────────────────────────────────
class BranchForm(forms.ModelForm):
    schemes = forms.ModelMultipleChoiceField(
        queryset=SchemeModel.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label="Available Schemes",
        help_text="Select schemes owned by this branch"
    )

    class Meta:
        model = Branch
        fields = [
            'name', 'code', 'phone', 'cell',
            'physical_address', 'street', 'town',
            'province', 'region', 'postal_code',
            'schemes',
        ]
        labels = {
            'name': 'Branch Name',
            'code': 'Branch Code',
            'phone': 'Phone Number',
            'cell': 'Cell Number',
        }
        widgets = {
            f: forms.TextInput(attrs={'class': 'w-full px-4 py-2 border rounded'})
            for f in [
                'name', 'code', 'phone', 'cell',
                'physical_address', 'street', 'town',
                'province', 'region', 'postal_code'
            ]
        }


# ─── User Setup Form ────────────────────────────────────────────────────
from django import forms
from django.contrib.auth.models import User, Group
from django.core.exceptions import ValidationError
from settings_app.models import Branch, UserProfile
from settings_app.utils.validation import is_strong_password

class UserSetupForm(forms.ModelForm):
    first_name = forms.CharField(label="Full Name")
    last_name  = forms.CharField(label="Surname")
    username   = forms.CharField(label="Username")

    password = forms.CharField(
        widget=forms.PasswordInput(render_value=True),
        help_text="Enter a password",
        required=False,
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(render_value=True),
        label="Confirm Password",
        help_text="Re-enter the password",
        required=False,
    )

    email = forms.EmailField(label="Email", required=False)
    is_active = forms.BooleanField(label="Active", required=False, initial=True)

    # ─── profile fields ─────────────────────
    id_number        = forms.CharField(required=False, label="ID / Passport")
    cell_no          = forms.CharField(required=False, label="Cell Number")
    physical_address = forms.CharField(required=False, label="Physical Address")
    street           = forms.CharField(required=False, label="Street")
    town             = forms.CharField(required=False, label="Town")
    province         = forms.CharField(required=False, label="Province")
    code             = forms.CharField(required=False, label="Postal Code")

    branch = forms.ModelChoiceField(
        queryset=Branch.objects.all(),
        empty_label="Select Branch",
        label="Branch"
    )

    security_groups = forms.ModelMultipleChoiceField(
        queryset=Group.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="What access does the user need?"
    )

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'username', 'password', 'email', 'is_active']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Prefill profile fields on edit
        if self.instance and self.instance.pk:
            try:
                profile = self.instance.userprofile
                self.fields['branch'].initial           = profile.branch
                self.fields['id_number'].initial        = profile.id_number
                self.fields['cell_no'].initial          = profile.cell_no
                self.fields['physical_address'].initial = profile.physical_address
                self.fields['street'].initial           = profile.street
                self.fields['town'].initial             = profile.town
                self.fields['province'].initial         = profile.province
                self.fields['code'].initial             = profile.code
            except UserProfile.DoesNotExist:
                pass
            self.fields['security_groups'].initial = self.instance.groups.all()
            self.fields['is_active'].initial = self.instance.is_active

    def clean_password(self):
        password = self.cleaned_data.get('password')
        if password and not is_strong_password(password):
            raise ValidationError(
                "Password must be at least 8 characters long and include uppercase, lowercase, number, and special character."
            )
        return password

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm = cleaned_data.get("confirm_password")

        if password and confirm and password != confirm:
            self.add_error("confirm_password", "Passwords do not match.")

    def save(self, commit=True):
        user = super().save(commit=False)
        pw = self.cleaned_data.get('password')
        if pw:
            user.set_password(pw)

        user.is_active = self.cleaned_data.get('is_active', True)

        if commit:
            user.save()
            user.groups.set(self.cleaned_data['security_groups'])

            profile, _ = UserProfile.objects.get_or_create(user=user)
            profile.branch           = self.cleaned_data['branch']
            profile.id_number        = self.cleaned_data['id_number']
            profile.cell_no          = self.cleaned_data['cell_no']
            profile.physical_address = self.cleaned_data['physical_address']
            profile.street           = self.cleaned_data['street']
            profile.town             = self.cleaned_data['town']
            profile.province         = self.cleaned_data['province']
            profile.code             = self.cleaned_data['code']
            profile.save()

        return user


# ─── SMS Template Form ──────────────────────────────────────────────────
class SMSTemplateForm(forms.ModelForm):
    class Meta:
        model = SMSTemplate
        fields = ['name', 'message']
        widgets = {
            'message': forms.Textarea(attrs={
                'rows': 3,
                'class': 'w-full px-4 py-2 border rounded resize-none'
            }),
        }


# ─── Group Select Form ──────────────────────────────────────────────────
class GroupSelectForm(forms.Form):
    group = forms.ModelChoiceField(
        queryset=UserGroup.objects.all(),
        label="Select Group",
        widget=forms.Select(attrs={'class':'w-full px-4 py-2 border rounded'})
    )


# ─── Plan Form ──────────────────────────────────────────────────────────
class PlanForm(forms.ModelForm):
    class Meta:
        model = SchemePlan
        fields = [
            # Plan Information
            'name', 'description', 'policy_type', 'scheme', 'underwriter',

            # Policy Details
            'main_cover', 'main_premium', 'main_uw_cover', 'main_uw_premium',
            'main_age_from', 'main_age_to', 'waiting_period', 'lapse_period',
            'spouses_allowed', 'children_allowed', 'extended_allowed',

            # Fee Distribution
            'admin_fee', 'cash_payout', 'agent_commission', 'office_fee',
            'scheme_fee', 'manager_fee', 'loyalty_programme', 'other_fees',
            
            # Terms & Conditions
            'terms_text', 'terms_pdf',

            # Other Settings
            'is_active', 'is_diy_visible',

            # Age range (if you want min/max age outside policy details)
            'min_age', 'max_age',

            # Premium (if you want it outside policy details)
            'premium',
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class':'w-full px-4 py-2 border rounded'}),
            'description': forms.Textarea(attrs={'class':'w-full px-4 py-2 border rounded', 'rows': 2}),
            'policy_type': forms.Select(attrs={'class':'w-full border rounded'}),
            'premium': forms.NumberInput(attrs={'class':'w-full px-4 py-2 border rounded'}),
            'underwriter': forms.TextInput(attrs={'class':'w-full px-4 py-2 border rounded'}),
            'scheme': forms.Select(attrs={'class':'w-full border rounded'}),
            'min_age': forms.NumberInput(attrs={'class':'w-full px-4 py-2 border rounded'}),
            'max_age': forms.NumberInput(attrs={'class':'w-full px-4 py-2 border rounded'}),
            'terms_text': forms.Textarea(attrs={'class':'w-full px-4 py-2 border rounded', 'rows': 4}),
            'terms_pdf': forms.ClearableFileInput(attrs={'class':'w-full px-4 py-2'}),
            'is_diy_visible': forms.CheckboxInput(attrs={'class':'h-4 w-4 text-blue-600'}),
        }

    def clean(self):
        cleaned = super().clean()
        name = cleaned.get("name")
        scheme = cleaned.get("scheme")
        if name and scheme:
            qs = Plan.objects.filter(name=name, scheme=scheme)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError("A plan with this name already exists under the selected scheme.")

        return cleaned



# ─── Plan Member Tier ───────────────────────────────────────────────────
from django import forms
from django.core.exceptions import ValidationError
from settings_app.models import PlanMemberTier

USER_TYPE_CHOICES = [
    ('Main', 'Main Member'),
    ('Spouse', 'Spouse'),
    ('Child', 'Child'),
    ('Extended', 'Extended Family'),
]

class PlanMemberTierForm(forms.ModelForm):
    class Meta:
        model = PlanMemberTier
        fields = [
            'user_type', 'age_from', 'age_to',
            'cover', 'premium', 'underwriter_cover',
            'underwriter_premium'
        ]
        widgets = {
            'user_type': forms.Select(choices=USER_TYPE_CHOICES, attrs={'class':'w-full border rounded'}),
            'age_from': forms.NumberInput(attrs={'class':'w-full border rounded', 'min': 0}),
            'age_to': forms.NumberInput(attrs={'class':'w-full border rounded', 'min': 0}),
            'cover': forms.NumberInput(attrs={'class':'w-full border rounded', 'min': 0}),
            'premium': forms.NumberInput(attrs={'class':'w-full border rounded', 'min': 0}),
            'underwriter_cover': forms.NumberInput(attrs={'class':'w-full border rounded', 'min': 0}),
            'underwriter_premium': forms.NumberInput(attrs={'class':'w-full border rounded', 'min': 0}),
            
        }

    def clean(self):
        cleaned = super().clean()
        age_from = cleaned.get('age_from')
        age_to = cleaned.get('age_to')
        if age_from is not None and age_to is not None and age_from > age_to:
            raise ValidationError("Age 'from' must be less than or equal to age 'to'.")
        return cleaned


from django import forms
from django.forms import BaseInlineFormSet, inlineformset_factory
from django.core.exceptions import ValidationError
from schemes.models import Plan
from settings_app.models import PlanMemberTier
from settings_app.forms import PlanMemberTierForm  # adjust if it's in same file

class BasePlanMemberTierFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        
        # Check if we have at least one valid form
        if not any(form.is_valid() and form.cleaned_data and not form.cleaned_data.get('DELETE', False) 
                  for form in self.forms):
            return
            
        # Track user types to ensure we don't have duplicates for the same age range
        user_type_age_ranges = {}
        
        for form in self.forms:
            if self.can_delete and self._should_delete_form(form):
                continue
                
            if form.is_valid() and form.cleaned_data:
                user_type = form.cleaned_data.get('user_type')
                age_from = form.cleaned_data.get('age_from')
                age_to = form.cleaned_data.get('age_to')
                
                if not user_type or age_from is None or age_to is None:
                    continue
                    
                # Check for overlapping age ranges for the same user type
                key = user_type
                if key in user_type_age_ranges:
                    for existing_range in user_type_age_ranges[key]:
                        existing_from, existing_to = existing_range
                        
                        # Check if ranges overlap
                        if (age_from <= existing_to and age_to >= existing_from):
                            form.add_error('age_from', 'Age ranges for the same user type cannot overlap')
                            break
                    
                    # Add this range
                    user_type_age_ranges[key].append((age_from, age_to))
                else:
                    user_type_age_ranges[key] = [(age_from, age_to)]
                    
                # Validate age range
                if age_from > age_to:
                    form.add_error('age_from', 'Age from must be less than or equal to age to')

PlanMemberTierFormSet = inlineformset_factory(
    SchemePlan,
    PlanMemberTier,
    form=PlanMemberTierForm,
    formset=BasePlanMemberTierFormSet,
    extra=5,  # Reduced from 15 to 5 for better usability
    can_delete=True  # Allow deletion of tiers
)


# ─── Plan Import Form ───────────────────────────────────────────────────
class PlanImportForm(forms.Form):
    scheme = forms.ModelChoiceField(
        queryset=SchemeModel.objects.all(),
        widget=forms.Select(attrs={'class':'w-full border rounded px-3 py-2'}),
        label="Target Scheme",
    )
    file = forms.FileField(
        widget=forms.ClearableFileInput(attrs={'class':'w-full'}),
        help_text=(
            "Upload CSV with columns: "
            "'name', 'description', 'policy_type', 'underwriter', 'main_cover', 'main_premium',"
            "main_uw_cover,main_uw_premium,main_age_from,main_age_to,"
            "admin_fee,cash_payout,agent_commission,office_fee,"
            "scheme_fee,manager_fee,loyalty_programme,other_fees,"
            "waiting_period,lapse_period,spouses_allowed,children_allowed,extended_allowed"
        ),
    )
