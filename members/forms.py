# members/forms.py

from members.models import Policy, Member
from schemes.models import Plan, Scheme
from django.db.models import Q
from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Fieldset, Field
from .models import Member, Policy, Dependent, Beneficiary
from utils.luhn import luhn_check, validate_id_number
from datetime import date


class PersonalDetailsForm(forms.ModelForm):
    is_foreign = forms.BooleanField(required=False, label='Foreign National', 
                                    widget=forms.CheckboxInput(attrs={'class': 'form-checkbox'}))
    
    class Meta:
        model = Member
        fields = [
            'title',
            'first_name',
            'last_name',
            'id_number',
            'passport_number',
            'gender',
            'date_of_birth',
            'phone_number',
            'whatsapp_number',
            'email',
            'marital_status',
            'physical_address_line_1',
            'physical_address_line_2',
            'physical_address_city',
            'physical_address_postal_code',
            'nationality',
            'country_of_birth',
            'country_of_residence',
        ]
        widgets = {
            'date_of_birth': forms.DateInput(attrs={
                'type': 'date',
                'max': date.today().isoformat()  # Prevent future dates
            }),
            'id_number': forms.TextInput(attrs={
                'maxlength': '13',
                'pattern': '[0-9]{13}',
                'placeholder': 'Enter 13-digit SA ID number'
            }),
            'passport_number': forms.TextInput(attrs={
                'placeholder': 'Enter passport number'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Set initial value for is_foreign based on whether passport number is present
        if self.instance and self.instance.passport_number and not self.instance.id_number:
            self.fields['is_foreign'].initial = True
            
        # Make nationality required for foreigners but not for SA citizens
        self.fields['nationality'].required = False
        self.fields['country_of_birth'].required = False
        self.fields['country_of_residence'].required = False

    def clean(self):
        cleaned = super().clean()
        id_number = cleaned.get('id_number')
        passport_number = cleaned.get('passport_number')
        is_foreign = cleaned.get('is_foreign')
        nationality = cleaned.get('nationality')
        country_of_birth = cleaned.get('country_of_birth')
        country_of_residence = cleaned.get('country_of_residence')
        
        try:
            # South African citizen validation
            if not is_foreign:
                # SA citizens must provide ID number
                if not id_number:
                    self.add_error('id_number', _('ID number is required for South African citizens.'))
                    return cleaned
                
                # Validate ID number using Luhn algorithm
                from members.utils import luhn_check
                if not luhn_check(id_number):
                    self.add_error('id_number', _('Invalid South African ID number. Failed Luhn check.'))
                    return cleaned
                    
                # Extract DOB and gender from ID
                from utils.luhn import validate_id_number
                valid, dob, gender = validate_id_number(id_number)
                if not valid:
                    self.add_error('id_number', _('Invalid South African ID number.'))
                else:
                    # Auto-fill DOB and gender from ID
                    cleaned['date_of_birth'] = dob
                    cleaned['gender'] = gender
                    cleaned['nationality'] = 'South African'
                    cleaned['country_of_birth'] = 'South Africa'
                    cleaned['country_of_residence'] = 'South Africa'
            
            # Foreign national validation
            else:
                # Foreigners must provide passport number
                if not passport_number:
                    self.add_error('passport_number', _('Passport number is required for foreign nationals.'))
                
                # Foreigners must provide nationality
                if not nationality:
                    self.add_error('nationality', _('Nationality is required for foreign nationals.'))
                
                # Foreigners must provide country of birth
                if not country_of_birth:
                    self.add_error('country_of_birth', _('Country of birth is required for foreign nationals.'))
                
                # Foreigners must provide country of residence
                if not country_of_residence:
                    self.add_error('country_of_residence', _('Country of residence is required for foreign nationals.'))
        
        except Exception as e:
            # Handle any exceptions during validation
            self.add_error(None, _('Error validating ID: {}').format(str(e)))
        
        return cleaned
        
    def save(self, commit=True):
        member = super().save(commit=False)
        
        # Calculate and save age
        if member.date_of_birth:
            from members.utils import get_member_age_from_dob
            member.age = get_member_age_from_dob(member.date_of_birth)
        
        if commit:
            member.save()
        
        return member


class PolicyDetailsForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        # Extract user from kwargs before calling parent's __init__
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # Filter schemes based on user permissions
        if self.user and not self.user.is_superuser:
            branch_user = getattr(self.user, 'branchuser', None)
            if branch_user and branch_user.branch:
                self.fields['scheme'].queryset = Scheme.objects.filter(branch=branch_user.branch)
            elif hasattr(self.user, 'agent'):
                self.fields['scheme'].queryset = Scheme.objects.filter(agents=self.user.agent)

        if self.initial.get('agent'):
            self.fields['agent'].disabled = True
        if self.initial.get('scheme'):
            self.fields['scheme'].disabled = True

        # Make fields read-only
        for field in ['underwritten_by', 'premium_amount', 'cover_amount', 'uw_membership_number', 'inception_date', 'cover_date']:
            if field in self.fields:
                self.fields[field].widget.attrs['readonly'] = True
                self.fields[field].widget.attrs['class'] = 'bg-gray-100'

    class Meta:
        model = Policy
        fields = [
            'scheme', 'plan', 'membership_number', 'uw_membership_number',
            'start_date', 'inception_date', 'cover_date',
            'underwritten_by', 'premium_amount', 'cover_amount',
        ]
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'inception_date': forms.DateInput(attrs={'type': 'date'}),
            'cover_date': forms.DateInput(attrs={'type': 'date'}),
        }



class DependentForm(forms.ModelForm):
    RELATIONSHIP_CHOICES = [
        ('', 'Select...'),
        ('Spouse', 'Spouse'),
        ('Child', 'Child'),
        ('Extended Family', 'Extended Family'),
    ]
    relationship = forms.ChoiceField(choices=RELATIONSHIP_CHOICES, required=False)
    first_name = forms.CharField(required=False)
    last_name = forms.CharField(required=False)
    date_of_birth = forms.DateField(
        required=False,
        widget=forms.DateInput(
            format='%Y-%m-%d',
            attrs={
                'type': 'date',
                'class': 'form-input rounded-md shadow-sm mt-1 block w-full',
                'placeholder': 'YYYY-MM-DD'
            }
        ),
        input_formats=['%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y', '%Y/%m/%d']
    )

    class Meta:
        model = Dependent
        fields = ['relationship', 'id_number', 'first_name', 'last_name', 'gender', 'date_of_birth']
        widgets = {
            'id_number': forms.TextInput(attrs={'class': 'form-input rounded-md shadow-sm mt-1 block w-full'}),
            'first_name': forms.TextInput(attrs={'class': 'form-input rounded-md shadow-sm mt-1 block w-full'}),
            'last_name': forms.TextInput(attrs={'class': 'form-input rounded-md shadow-sm mt-1 block w-full'}),
            'gender': forms.Select(attrs={'class': 'form-select rounded-md shadow-sm mt-1 block w-full'}),
        }

    def clean(self):
        data = super().clean()
        rel = data.get('relationship')
        idn = data.get('id_number', '').strip()
        dob = data.get('date_of_birth')
        first_name = data.get('first_name', '').strip()
        last_name = data.get('last_name', '').strip()

        # If relationship is blank (Select...), skip all validation
        if not rel:
            return data
            
        # Convert string date to date object if needed
        if isinstance(dob, str):
            from django.utils.dateparse import parse_date
            try:
                dob = parse_date(dob)
                data['date_of_birth'] = dob  # Update with parsed date
            except (ValueError, TypeError):
                pass

        # Basic validation for required fields
        if not first_name:
            self.add_error('first_name', _('First name is required.'))
        if not last_name:
            self.add_error('last_name', _('Last name is required.'))

        # For Spouse, Main Member, and Beneficiary - ID is required with Luhn validation
        if rel in ['Spouse', 'Main Member', 'Beneficiary']:
            if not idn:
                self.add_error('id_number', _('ID number is required.'))
                return data  # Skip further validation if no ID provided
                
            # Validate ID number format and Luhn check
            if not idn.isdigit() or len(idn) != 13:
                self.add_error('id_number', _('ID number must be 13 digits.'))
                return data
                
            valid, id_dob, gender = validate_id_number(idn)
            if not valid:
                self.add_error('id_number', _('Invalid South African ID number.'))
                return data
                
            # Validate DOB against ID if both are provided
            if dob and id_dob and dob != id_dob:
                self.add_error('date_of_birth', _('Date of birth does not match ID number.'))
            
            # If we have a valid ID but no DOB, use the one from the ID
            if valid and id_dob and not dob:
                data['date_of_birth'] = id_dob
                
        else:
            # For children/extended family: Only require DOB, ID is optional
            if not dob:
                self.add_error('date_of_birth', _('Date of birth is required.'))
            
            # If ID is provided, it must be valid but is not required
            if idn:
                if not idn.isdigit() or len(idn) != 13:
                    self.add_error('id_number', _('ID number must be 13 digits if provided.'))
                else:
                    valid, id_dob, gender = validate_id_number(idn)
                    if not valid:
                        self.add_error('id_number', _('Invalid South African ID number.'))
                    elif dob and id_dob and dob != id_dob:
                        self.add_error('date_of_birth', _('Date of birth does not match ID number.'))

        return data


class BeneficiaryForm(forms.ModelForm):
    share = forms.IntegerField(
        min_value=1, 
        max_value=100,
        widget=forms.NumberInput(attrs={
            'class': 'form-input w-24',
            'min': '1',
            'max': '100',
            'step': '1'
        })
    )
    
    class Meta:
        model = Beneficiary
        fields = [
            'id_number', 
            'first_name', 
            'last_name', 
            'relationship_to_main_member',
            'date_of_birth',
            'gender',
            'share'
        ]
        widgets = {
            'id_number': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Enter 13-digit ID',
                'data-validate-id': 'true'
            }),
            'first_name': forms.TextInput(attrs={'class': 'form-input'}),
            'last_name': forms.TextInput(attrs={'class': 'form-input'}),
            'relationship_to_main_member': forms.TextInput(attrs={'class': 'form-input'}),
            'date_of_birth': forms.DateInput(attrs={
                'type': 'date', 
                'class': 'form-input',
                'readonly': 'readonly'
            }),
            'gender': forms.Select(attrs={
                'class': 'form-select',
                'disabled': 'disabled'
            }),
        }
        help_texts = {
            'id_number': 'Enter a valid South African ID number',
            'share': 'Percentage of benefit (1-100)'
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make date_of_birth and gender not required since they'll be auto-filled from ID
        self.fields['date_of_birth'].required = False
        self.fields['gender'].required = False
        
        # Add form-control classes to all fields
        for field_name, field in self.fields.items():
            if field_name not in ['date_of_birth', 'gender']:
                field.widget.attrs['class'] = field.widget.attrs.get('class', '') + ' form-control'

    def clean_id_number(self):
        idn = self.cleaned_data.get('id_number', '').strip()
        if not idn:
            raise ValidationError(_('ID number is required for beneficiaries.'))
            
        # Validate ID number format
        if not idn.isdigit() or len(idn) != 13:
            raise ValidationError(_('ID number must be 13 digits.'))
            
        valid, id_dob, gender = validate_id_number(idn)
        if not valid:
            raise ValidationError(_('Invalid South African ID number.'))
            
        # Store the extracted data for potential use in clean()
        self.id_dob = id_dob
        self.id_gender = gender
        
        return idn

    def clean(self):
        cleaned_data = super().clean()
        first_name = cleaned_data.get('first_name', '').strip()
        last_name = cleaned_data.get('last_name', '').strip()
        relationship = cleaned_data.get('relationship_to_main_member', '').strip()
        share = cleaned_data.get('share')
        policy = self.initial.get('policy')
        id_number = cleaned_data.get('id_number', '').strip()
        
        # If we have a valid ID, use the extracted data
        if hasattr(self, 'id_dob') and self.id_dob:
            cleaned_data['date_of_birth'] = self.id_dob
            cleaned_data['gender'] = self.id_gender
            
            # Update the form data to reflect the auto-filled values
            if 'date_of_birth' in self.data:
                self.data = self.data.copy()
                self.data['date_of_birth'] = self.id_dob.strftime('%Y-%m-%d') if self.id_dob else ''
            if 'gender' in self.data:
                self.data = self.data.copy()
                self.data['gender'] = self.id_gender
        
        # Basic validation for required fields
        if not first_name:
            self.add_error('first_name', _('First name is required.'))
        if not last_name:
            self.add_error('last_name', _('Last name is required.'))
        if not relationship:
            self.add_error('relationship_to_main_member', _('Relationship is required.'))
        if share is None:
            self.add_error('share', _('Share percentage is required.'))
        elif share <= 0 or share > 100:
            self.add_error('share', _('Share must be between 1 and 100.'))
            
        # Check total share doesn't exceed 100%
        if policy and 'share' in cleaned_data:
            existing_shares = Beneficiary.objects.filter(policy=policy)
            if self.instance and self.instance.pk:
                existing_shares = existing_shares.exclude(pk=self.instance.pk)
            total_share = sum(b.share for b in existing_shares) + int(share)
            if total_share > 100:
                self.add_error('share', _('Total beneficiary share cannot exceed 100%.'))

        return cleaned_data


from django import forms
from branches.models import Bank  # Import Bank model
from .models import Policy  # Assuming the Policy model is in the same app

class PaymentOptionsForm(forms.ModelForm):
    class Meta:
        model = Policy
        fields = [
            'payment_method', 'bank', 'branch_code',
            'account_holder_name', 'account_number',
            'debit_instruction_day', 'eft_agreed'
        ]
        widgets = {
            'branch_code': forms.TextInput(attrs={'readonly': 'readonly'}),
        }

    # Modify the 'bank' field to use ModelChoiceField for ForeignKey relationship
    bank = forms.ModelChoiceField(queryset=Bank.objects.all(), required=False)  # Use ModelChoiceField

    def clean(self):
        cleaned = super().clean()
        pm = cleaned.get('payment_method')

        if pm == 'DEBIT_ORDER':
            # These fields are all required under Debit Order
            for f in ('bank', 'account_holder_name', 'account_number', 'debit_instruction_day'):
                if not cleaned.get(f):
                    self.add_error(f, _('This field is required for debit order.'))

        elif pm == 'EFT':
            if not cleaned.get('eft_agreed'):
                self.add_error('eft_agreed', _('You must agree to pay via EFT.'))

        # Easypay no extra validation here
        return cleaned



class OTPConfirmForm(forms.Form):
    otp_code  = forms.CharField(label=_('OTP Code'), max_length=6)
    agree_tnc = forms.BooleanField(label=_('I agree to the Terms & Conditions'))


class CommunicationForm(forms.Form):
    to         = forms.CharField(label=_('To'), max_length=20)
    subject    = forms.CharField(label=_('Subject'), max_length=255)
    body       = forms.CharField(label=_('Message'), widget=forms.Textarea)
    attachment = forms.FileField(label=_('Attach File'), required=False)


class NotesForm(forms.Form):
    content = forms.CharField(label=_('New Note'), widget=forms.Textarea)


# ——— Edit forms reuse the above behavior ————————————————

class PersonalDetailsEditForm(PersonalDetailsForm):
    """Identical to PersonalDetailsForm for inline editing."""
    pass


class AddressEditForm(forms.ModelForm):
    class Meta:
        model  = Member
        fields = [
            'physical_address_line_1',
            'physical_address_line_2',
            'physical_address_city',
            'physical_address_postal_code',
        ]


class PolicyEditForm(forms.ModelForm):
    class Meta:
        model = Policy
        fields = [
            'scheme', 'plan',
            'membership_number', 'uw_membership_number',
            'start_date', 'inception_date', 'cover_date'
        ]
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
        }


class PaymentOptionsEditForm(PaymentOptionsForm):
    """Identical to PaymentOptionsForm for inline editing."""
    pass

from django import forms
from localflavor.za.forms import ZAIDField
from django.forms import inlineformset_factory, formset_factory
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from dateutil.relativedelta import relativedelta

class SpouseInfoForm(forms.ModelForm):
    is_foreigner = forms.BooleanField(
        required=False,
        label='Is Foreign National',
        widget=forms.CheckboxInput(attrs={
            'class': 'form-checkbox h-5 w-5 text-blue-600',
            'onchange': 'toggleForeignerFields(this)'
        })
    )
    
    class Meta:
        model = Member
        fields = [
            'spouse_first_name', 'spouse_last_name', 'spouse_id_number',
            'spouse_date_of_birth', 'spouse_gender', 'spouse_phone_number',
            'spouse_email', 'spouse_passport_number', 'spouse_nationality',
            'spouse_country_of_birth', 'spouse_country_of_residence'
        ]
        widgets = {
            'spouse_date_of_birth': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-input rounded-md shadow-sm mt-1 block w-full'
            }),
            'spouse_gender': forms.Select(attrs={
                'class': 'form-select rounded-md shadow-sm mt-1 block w-full'
            }),
            'spouse_first_name': forms.TextInput(attrs={
                'class': 'form-input rounded-md shadow-sm mt-1 block w-full'
            }),
            'spouse_last_name': forms.TextInput(attrs={
                'class': 'form-input rounded-md shadow-sm mt-1 block w-full'
            }),
            'spouse_id_number': forms.TextInput(attrs={
                'class': 'form-input rounded-md shadow-sm mt-1 block w-full',
                'placeholder': 'Enter 13-digit ID',
                'data-validate-id': 'true'
            }),
            'spouse_phone_number': forms.TextInput(attrs={
                'class': 'form-input rounded-md shadow-sm mt-1 block w-full',
                'placeholder': 'e.g. +27 12 345 6789'
            }),
            'spouse_email': forms.EmailInput(attrs={
                'class': 'form-input rounded-md shadow-sm mt-1 block w-full',
                'placeholder': 'email@example.com'
            }),
            'spouse_passport_number': forms.TextInput(attrs={
                'class': 'form-input rounded-md shadow-sm mt-1 block w-full',
                'placeholder': 'Enter passport number'
            }),
            'spouse_nationality': forms.TextInput(attrs={
                'class': 'form-input rounded-md shadow-sm mt-1 block w-full',
                'placeholder': 'Enter nationality'
            }),
            'spouse_country_of_birth': forms.TextInput(attrs={
                'class': 'form-input rounded-md shadow-sm mt-1 block w-full',
                'placeholder': 'Enter country of birth'
            }),
            'spouse_country_of_residence': forms.TextInput(attrs={
                'class': 'form-input rounded-md shadow-sm mt-1 block w-full',
                'placeholder': 'Enter country of residence'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Set initial value for is_foreigner based on whether passport number is present
        if self.instance and self.instance.spouse_passport_number:
            self.fields['is_foreigner'].initial = True
        
        # Make fields required conditionally
        self.fields['spouse_first_name'].required = True
        self.fields['spouse_last_name'].required = True
        self.fields['spouse_phone_number'].required = True
        self.fields['spouse_email'].required = False
    
    def clean(self):
        cleaned_data = super().clean()
        is_foreigner = cleaned_data.get('is_foreigner', False)
        
        if not is_foreigner:
            # Validate South African ID number
            spouse_id = cleaned_data.get('spouse_id_number', '').strip()
            if not spouse_id:
                self.add_error('spouse_id_number', 'ID number is required for South African citizens')
            else:
                # Import the validate_id_number function from utils.luhn
                from utils.luhn import validate_id_number
                
                # Validate ID number format and extract data
                is_valid, dob_from_id, gender_from_id = validate_id_number(spouse_id)
                
                if not is_valid:
                    self.add_error('spouse_id_number', 'Invalid South African ID number')
                else:
                    # Auto-fill date of birth and gender from ID if not provided
                    if 'spouse_date_of_birth' not in self.errors and not cleaned_data.get('spouse_date_of_birth') and dob_from_id:
                        cleaned_data['spouse_date_of_birth'] = dob_from_id
                        
                    if 'spouse_gender' not in self.errors and not cleaned_data.get('spouse_gender') and gender_from_id:
                        cleaned_data['spouse_gender'] = gender_from_id.upper()
                    
                    # Clear foreigner-specific fields
                    cleaned_data['spouse_passport_number'] = ''
                    cleaned_data['spouse_nationality'] = ''
                    cleaned_data['spouse_country_of_birth'] = ''
                    cleaned_data['spouse_country_of_residence'] = ''
        else:
            # For foreigners, require passport number and nationality
            if not cleaned_data.get('spouse_passport_number'):
                self.add_error('spouse_passport_number', 'Passport number is required for foreign nationals')
            
            if not cleaned_data.get('spouse_nationality'):
                self.add_error('spouse_nationality', 'Nationality is required for foreign nationals')
            
            # Clear SA ID number and related fields
            cleaned_data['spouse_id_number'] = ''
            cleaned_data['spouse_date_of_birth'] = None
            cleaned_data['spouse_gender'] = ''
        
        # Validate date of birth if present
        spouse_dob = cleaned_data.get('spouse_date_of_birth')
        if spouse_dob and spouse_dob > timezone.now().date():
            self.add_error('spouse_date_of_birth', 'Date of birth cannot be in the future')
        
        return cleaned_data

class ChildrenInfoForm(forms.ModelForm):
    class Meta:
        model = Member
        fields = []  # We'll handle children through a formset
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.children = forms.inlineformset_factory(
            Member, 
            Dependent,
            fields=('first_name', 'last_name', 'id_number', 'date_of_birth', 'gender'),
            extra=1,
            can_delete=True,
            widgets={
                'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
            }
        )
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        if commit:
            instance.save()
        return instance

class PolicySummaryForm(forms.ModelForm):
    confirm_details = forms.BooleanField(
        required=True,
        label='I confirm that all the information provided is accurate and complete.',
        error_messages={
            'required': 'You must confirm that the information is accurate to proceed.'
        }
    )
    
    class Meta:
        model = Policy
        fields = []  # No fields to display, just confirmation
    
    def save(self, commit=True):
        policy = super().save(commit=False)
        policy.is_complete = True
        if commit:
            policy.save()
        return policy

# Form for looking up policies
class PolicyLookupForm(forms.Form):
    id_number = ZAIDField(
        label="South African ID Number",
        widget=forms.TextInput(attrs={"placeholder": "Enter your 13-digit ID"})
    )
    otp = forms.CharField(
        max_length=6,
        label="One-Time Password",
        widget=forms.TextInput(attrs={"placeholder": "Enter the OTP"}),
        required=False
    )
    
    def clean(self):
        cleaned_data = super().clean()
        id_number = cleaned_data.get('id_number')
        otp = cleaned_data.get('otp')
        
        # Basic validation for ID number
        if id_number and not luhn_check(id_number):
            raise forms.ValidationError({
                'id_number': 'Invalid South African ID number.'
            })
            
        return cleaned_data


from django import forms
from django.utils.translation import gettext_lazy as _

class OTPForm(forms.Form):
    otp_code = forms.CharField(
        label=_("One-time PIN"),
        max_length=6,
        min_length=6,
        required=True,
        widget=forms.TextInput(attrs={
            "placeholder": "Enter 6-digit PIN",
            "pattern": r"\d{6}",
            "class": "w-full px-3 py-2 border rounded",
        })
    )
    agree_tnc = forms.BooleanField(
        label=_("I agree to the Terms & Conditions"),
        required=True,
        error_messages={'required': _("You must agree to the Terms & Conditions.")},
        widget=forms.CheckboxInput(attrs={"class": "form-checkbox h-5 w-5 text-blue-600"})
    )

