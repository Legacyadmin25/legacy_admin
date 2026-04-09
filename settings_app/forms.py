import re
from datetime import datetime
from settings_app.utils.validation import is_strong_password
from django.core.exceptions import ObjectDoesNotExist, ValidationError

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
            'phone', 'logo', 'terms', 'debit_order_no', 'bank', 'branch_code',
            'account_no', 'account_type', 'address', 'city', 'province', 'postal_code',
            'allow_auto_policy_number', 'active'
        ]
        widgets = {
            'address': forms.TextInput(attrs={'class': 'w-full px-4 py-2 border rounded'}),
            'city': forms.TextInput(attrs={'class': 'w-full px-4 py-2 border rounded'}),
            'province': forms.Select(attrs={'class': 'w-full px-4 py-2 border rounded'}),
            'postal_code': forms.TextInput(attrs={'class': 'w-full px-4 py-2 border rounded'}),
            'allow_auto_policy_number': forms.CheckboxInput(attrs={'class': 'form-checkbox h-5 w-5 text-blue-600'}),
            'active': forms.CheckboxInput(attrs={'class': 'form-checkbox h-5 w-5 text-blue-600'}),
            'bank': forms.Select(attrs={'class': 'w-full px-4 py-2 border rounded'}),
            'branch_code': forms.TextInput(attrs={'class': 'w-full px-4 py-2 border rounded', 'readonly': True}),
            'account_no': forms.TextInput(attrs={'class': 'w-full px-4 py-2 border rounded'}),
            'account_type': forms.Select(attrs={'class': 'w-full px-4 py-2 border rounded'}),
        }
        
    def __init__(self, *args, **kwargs):
        from branches.models import Bank
        from schemes.constants import PROVINCE_CHOICES
        super().__init__(*args, **kwargs)
        
        # Set active field initial value
        if self.instance and self.instance.pk:
            self.fields['active'].initial = self.instance.active
        else:
            self.fields['active'].initial = True
        
        # Make fields not required by default, but keep required fields
        required_fields = ['branch', 'name', 'registration_no', 'fsp_number', 'email', 'phone']
        for field_name, field in self.fields.items():
            field.required = field_name in required_fields
            
        # Set up province choices
        self.fields['province'] = forms.ChoiceField(
            choices=PROVINCE_CHOICES,
            required=False,
            widget=forms.Select(attrs={'class': 'w-full px-4 py-2 border rounded'})
        )
        
        # Set up bank choices with branch code data
        self.fields['bank'].queryset = Bank.objects.all().order_by('name')
        
        # Set initial branch code if bank is selected
        if self.instance and self.instance.bank:
            self.fields['branch_code'].initial = self.instance.bank.branch_code
        
        # Update bank widget to include data-branch-code attribute
        self.fields['bank'].widget.attrs.update({
            'onchange': 'updateBranchCode(this)',
            'class': 'w-full px-4 py-2 border rounded bank-select',
        })
        
        # Add data attributes for branch codes
        self.fields['bank'].widget.choices = [
            (bank.id, bank.name, {'data-branch-code': bank.branch_code or ''}) 
            for bank in self.fields['bank'].queryset
        ]


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
            'address1': forms.TextInput(attrs={'class': 'form-control'}),
            'address2': forms.TextInput(attrs={'class': 'form-control'}),
            'address3': forms.TextInput(attrs={'class': 'form-control'}),
            'code': forms.TextInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Set required fields
        required_fields = ['full_name', 'surname', 'contact_number', 'email', 'scheme']
        for field_name in required_fields:
            if field_name in self.fields:
                self.fields[field_name].required = True
        
        # Add help text for required fields
        for field_name, field in self.fields.items():
            if field.required:
                field.help_text = f"{field.help_text or ''} Required field.".strip()
        
        # Make address fields required
        self.fields['address1'].required = True
        self.fields['address2'].required = True
        self.fields['address3'].required = True
        self.fields['code'].required = True
        
        # Make ID number and passport number optional
        self.fields['id_number'].required = False
        self.fields['passport_number'].required = False
        
        # Add help text for ID number
        self.fields['id_number'].help_text = "Optional. If provided, must be a valid South African ID number."
        
        # Set default values for address fields if they're empty
        if not self.instance.pk:
            self.fields['address1'].initial = ''
            self.fields['address2'].initial = ''
            self.fields['address3'].initial = ''
            self.fields['code'].initial = ''

        if user and not user.is_superuser:
            if user_has_role(user, 'Branch Owner', 'Scheme Manager', 'Internal Admin'):
                self.fields['scheme'].queryset = get_user_accessible_schemes(user)

    def clean_id_number(self):
        idn = self.cleaned_data.get('id_number', '').strip()
        if idn and (len(idn) != 13 or not idn.isdigit() or not luhn_checksum(idn)):
            raise ValidationError("Invalid South African ID number.")
        return idn if idn else None

    def clean_contact_number(self):
        contact = self.cleaned_data.get('contact_number', '').strip()
        if contact and (not contact.isdigit() or len(contact) != 10):
            raise ValidationError("Contact number must be exactly 10 digits.")
        return contact

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip()
        if email:
            validate_email(email)
        return email
        
    def save(self, commit=True):
        agent = super().save(commit=False)
        if commit:
            agent.save()
            self.save_m2m()
        return agent


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
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from branches.models import Branch as EnrollmentBranch
from settings_app.models import Branch as LegacyBranch, UserProfile
from settings_app.utils.validation import is_strong_password
from config.permissions import CANONICAL_ROLE_HIERARCHY, get_user_accessible_schemes, user_has_role

User = get_user_model()


class SchemeBranchSelect(forms.Select):
    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex=subindex, attrs=attrs)
        if value:
            try:
                scheme = self.choices.queryset.get(pk=value)
            except Exception:
                scheme = None
            if scheme is not None:
                option['attrs']['data-branch-id'] = str(scheme.branch_id)
        return option

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
        queryset=EnrollmentBranch.objects.all().order_by('name'),
        empty_label="Select Branch",
        label="Branch"
    )

    assigned_scheme = forms.ModelChoiceField(
        queryset=SchemeModel.objects.filter(active=True).select_related('branch').order_by('name'),
        widget=SchemeBranchSelect,
        required=False,
        empty_label="Select branch first",
        label="Assigned Scheme"
    )

    generate_enrollment_link = forms.BooleanField(
        required=False,
        label="Generate client signup link after saving"
    )

    enrollment_scheme = forms.ModelChoiceField(
        queryset=SchemeModel.objects.filter(active=True).select_related('branch').order_by('name'),
        widget=SchemeBranchSelect,
        empty_label="Select branch first",
        required=False,
        label="Signup Link Scheme"
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

    @staticmethod
    def _match_enrollment_branch(legacy_branch):
        if not legacy_branch:
            return None

        if legacy_branch.code:
            matched = EnrollmentBranch.objects.filter(code=legacy_branch.code).first()
            if matched:
                return matched

        return EnrollmentBranch.objects.filter(name__iexact=legacy_branch.name).first()

    @staticmethod
    def _match_legacy_branch(enrollment_branch):
        if not enrollment_branch:
            return None

        if enrollment_branch.code:
            matched = LegacyBranch.objects.filter(code=enrollment_branch.code).first()
            if matched:
                return matched

        return LegacyBranch.objects.filter(name__iexact=enrollment_branch.name).first()

    @staticmethod
    def _sync_profile_fields(profile, values):
        profile_field_names = {field.name for field in profile._meta.fields}
        for field_name, value in values.items():
            if field_name in profile_field_names:
                setattr(profile, field_name, value)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        canonical_groups = []
        for role_name in CANONICAL_ROLE_HIERARCHY:
            group, _ = Group.objects.get_or_create(name=role_name)
            canonical_groups.append(group.pk)
        self.fields['security_groups'].queryset = Group.objects.filter(pk__in=canonical_groups).order_by('name')

        selected_branch_id = None
        if self.is_bound:
            selected_branch_id = self.data.get('branch') or None

        self.fields['enrollment_scheme'].help_text = "The generated client signup link will open this scheme's enrollment flow."
        self.fields['generate_enrollment_link'].help_text = "Use the selected branch and scheme to generate a public enrollment link for this user or agent."

        # Prefill profile fields on edit
        if self.instance and self.instance.pk:
            if getattr(self.instance, 'branch', None):
                self.fields['branch'].initial = self.instance.branch

            try:
                profile = self.instance.userprofile
                if not self.fields['branch'].initial:
                    self.fields['branch'].initial = self._match_enrollment_branch(profile.branch)
                for field_name in ('id_number', 'cell_no', 'physical_address', 'street', 'town', 'province', 'code'):
                    self.fields[field_name].initial = getattr(profile, field_name, '')
            except UserProfile.DoesNotExist:
                pass

            self.fields['assigned_scheme'].initial = self.instance.assigned_schemes.first()
            self.fields['security_groups'].initial = self.instance.groups.all()
            self.fields['is_active'].initial = self.instance.is_active

            try:
                agent = self.instance.agent
            except (AttributeError, ObjectDoesNotExist):
                agent = None
            if agent and agent.scheme:
                self.fields['enrollment_scheme'].initial = agent.scheme
            elif self.instance.assigned_schemes.count() == 1:
                self.fields['enrollment_scheme'].initial = self.instance.assigned_schemes.first()

        if not selected_branch_id and self.fields['branch'].initial:
            selected_branch_id = str(self.fields['branch'].initial.pk)

        for field_name, default_placeholder in (
            ('assigned_scheme', 'Select a scheme'),
            ('enrollment_scheme', 'Select scheme for signup link'),
        ):
            widget = self.fields[field_name].widget
            widget.attrs['data-default-placeholder'] = default_placeholder
            widget.attrs['data-branch-placeholder'] = 'Select branch first'
            if not selected_branch_id:
                widget.attrs['disabled'] = 'disabled'
            elif 'disabled' in widget.attrs:
                del widget.attrs['disabled']

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
        branch = cleaned_data.get('branch')
        assigned_scheme = cleaned_data.get('assigned_scheme')
        generate_enrollment_link = cleaned_data.get('generate_enrollment_link')
        enrollment_scheme = cleaned_data.get('enrollment_scheme')

        if password and confirm and password != confirm:
            self.add_error("confirm_password", "Passwords do not match.")

        if branch and assigned_scheme and assigned_scheme.branch_id != branch.id:
            self.add_error('assigned_scheme', 'Selected scheme does not belong to the selected branch.')

        if generate_enrollment_link and not enrollment_scheme:
            if assigned_scheme:
                enrollment_scheme = assigned_scheme
                cleaned_data['enrollment_scheme'] = enrollment_scheme
            else:
                self.add_error('enrollment_scheme', 'Select the scheme to use for the generated signup link.')

        if enrollment_scheme and branch and enrollment_scheme.branch_id != branch.id:
            self.add_error('enrollment_scheme', 'Selected signup scheme does not belong to the selected branch.')

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        pw = self.cleaned_data.get('password')
        if pw:
            user.set_password(pw)

        user.is_active = self.cleaned_data.get('is_active', True)
        user.branch = self.cleaned_data.get('branch')

        if commit:
            user.save()
            user.groups.set(self.cleaned_data['security_groups'])
            assigned_scheme = self.cleaned_data.get('assigned_scheme')
            user.assigned_schemes.set([assigned_scheme] if assigned_scheme else [])

            profile, _ = UserProfile.objects.get_or_create(user=user)
            self._sync_profile_fields(profile, {
                'branch': self._match_legacy_branch(self.cleaned_data['branch']),
                'id_number': self.cleaned_data['id_number'],
                'cell_no': self.cleaned_data['cell_no'],
                'physical_address': self.cleaned_data['physical_address'],
                'street': self.cleaned_data['street'],
                'town': self.cleaned_data['town'],
                'province': self.cleaned_data['province'],
                'code': self.cleaned_data['code'],
            })
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
    # Override the underwriter field to use a ModelChoiceField
    underwriter = forms.ModelChoiceField(
        queryset=Underwriter.objects.all().order_by('name'),
        label="Underwriter",
        empty_label="— Select Underwriter —",
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-2 border rounded focus:ring',
        })
    )
    # Set default values for waiting period and lapse period
    waiting_period = forms.IntegerField(initial=6, help_text="Months before cover starts")
    lapse_period = forms.IntegerField(initial=2, help_text="Months before lapse")
    
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
                        
                        # Check if ranges overlap (modified to allow adjacent ranges)
                        # Allow ranges that only touch at endpoints (e.g., 0-1 and 1-5)
                        if (age_from < existing_to and age_to > existing_from):
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
    extra=8,  # Fixed number of empty forms for consistent UI
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
