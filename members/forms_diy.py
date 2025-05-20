from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _
import re
from datetime import date, datetime

class DIYPersonalDetailsForm(forms.Form):
    # Title
    TITLE_CHOICES = [
        ('mr', 'Mr'),
        ('mrs', 'Mrs'),
        ('ms', 'Ms'),
        ('miss', 'Miss'),
        ('dr', 'Dr'),
        ('prof', 'Prof'),
        ('rev', 'Rev'),
        ('other', 'Other'),
    ]
    
    title = forms.ChoiceField(
        label='Title',
        choices=TITLE_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-select',
            'x-model': 'formData.title',
        })
    )
    
    # Personal Information
    first_name = forms.CharField(
        label='First Name',
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'x-model': 'formData.first_name',
            'placeholder': 'Enter your first name',
        })
    )
    
    middle_name = forms.CharField(
        label='Middle Name',
        required=False,
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'x-model': 'formData.middle_name',
            'placeholder': 'Enter your middle name (optional)',
        })
    )
    
    last_name = forms.CharField(
        label='Last Name',
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'x-model': 'formData.last_name',
            'placeholder': 'Enter your last name',
        })
    )
    
    # ID Number and Date of Birth
    id_number = forms.CharField(
        label='South African ID Number',
        max_length=13,
        min_length=13,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'x-model': 'formData.id_number',
            'placeholder': 'Enter your 13-digit ID number',
            'x-mask': '999999 9999 999',
        }),
        help_text='Please enter your 13-digit South African ID number',
    )
    
    date_of_birth = forms.DateField(
        label='Date of Birth',
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-input',
            'x-model': 'formData.date_of_birth',
            'max': timezone.now().date().strftime('%Y-%m-%d'),
        })
    )
    
    # Gender
    GENDER_CHOICES = [
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
        ('prefer_not_to_say', 'Prefer not to say'),
    ]
    
    gender = forms.ChoiceField(
        label='Gender',
        choices=GENDER_CHOICES,
        widget=forms.RadioSelect(attrs={
            'class': 'form-radio',
            'x-model': 'formData.gender',
        })
    )
    
    # Marital Status
    MARITAL_STATUS_CHOICES = [
        ('single', 'Single'),
        ('married', 'Married'),
        ('divorced', 'Divorced'),
        ('widowed', 'Widowed'),
        ('life_partner', 'Life Partner'),
        ('other', 'Other'),
    ]
    
    marital_status = forms.ChoiceField(
        label='Marital Status',
        choices=MARITAL_STATUS_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-select',
            'x-model': 'formData.marital_status',
        })
    )
    
    # Nationality
    is_south_african = forms.BooleanField(
        label='South African Citizen',
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-checkbox',
            'x-model': 'formData.is_south_african',
        })
    )
    
    passport_number = forms.CharField(
        label='Passport Number',
        required=False,
        max_length=50,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'x-model': 'formData.passport_number',
            'x-bind:disabled': 'formData.is_south_african',
            'x-bind:class': '{ "bg-gray-100": formData.is_south_african }',
            'placeholder': 'Enter passport number if not South African',
        })
    )
    
    def clean_id_number(self):
        """Validate South African ID number"""
        id_number = self.cleaned_data.get('id_number', '').replace(' ', '')
        
        # Basic validation for length and digits only
        if not re.match(r'^\d{13}$', id_number):
            raise ValidationError('ID number must be 13 digits long')
        
        # Extract date of birth from ID number
        try:
            year = int(id_number[0:2])
            month = int(id_number[2:4])
            day = int(id_number[4:6])
            
            # Determine century
            current_year = timezone.now().year % 100
            century = 2000 if (year <= current_year) else 1900
            full_year = century + year
            
            # Validate date
            date_of_birth = date(full_year, month, day)
            
            # Ensure date is not in the future
            if date_of_birth > timezone.now().date():
                raise ValidationError('Invalid date of birth in ID number')
                
        except (ValueError, TypeError):
            raise ValidationError('Invalid date of birth in ID number')
        
        return id_number
    
    def clean_date_of_birth(self):
        """Validate date of birth"""
        date_of_birth = self.cleaned_data.get('date_of_birth')
        
        # Ensure date of birth is not in the future
        if date_of_birth and date_of_birth > timezone.now().date():
            raise ValidationError('Date of birth cannot be in the future')
        
        # Ensure the person is at least 18 years old
        if date_of_birth:
            today = timezone.now().date()
            age = today.year - date_of_birth.year - ((today.month, today.day) < (date_of_birth.month, date_of_birth.day))
            
            if age < 18:
                raise ValidationError('You must be at least 18 years old to apply')
            
            if age > 100:
                raise ValidationError('Please contact our support for applicants over 100 years old')
        
        return date_of_birth
    
    def clean(self):
        cleaned_data = super().clean()
        
        # If not South African, passport number is required
        is_south_african = cleaned_data.get('is_south_african', True)
        passport_number = cleaned_data.get('passport_number')
        
        if not is_south_african and not passport_number:
            self.add_error('passport_number', 'Passport number is required for non-South African citizens')
        
        return cleaned_data


class DIYContactInformationForm(forms.Form):
    # Email
    email = forms.EmailField(
        label='Email Address',
        widget=forms.EmailInput(attrs={
            'class': 'form-input',
            'x-model': 'formData.email',
            'placeholder': 'your.email@example.com',
        })
    )
    
    # Phone Numbers
    phone_number = forms.CharField(
        label='Mobile Number',
        max_length=20,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'x-model': 'formData.phone_number',
            'placeholder': 'e.g. 071 234 5678',
            'x-mask': '999 999 9999',
        })
    )
    
    alternate_phone = forms.CharField(
        label='Alternate Phone Number (Optional)',
        required=False,
        max_length=20,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'x-model': 'formData.alternate_phone',
            'placeholder': 'e.g. 011 234 5678',
            'x-mask': '999 999 9999',
        })
    )
    
    # Address
    address_line_1 = forms.CharField(
        label='Street Address',
        max_length=255,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'x-model': 'formData.address_line_1',
            'placeholder': 'e.g. 123 Main Road',
        })
    )
    
    address_line_2 = forms.CharField(
        label='Apartment, Suite, etc. (Optional)',
        required=False,
        max_length=255,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'x-model': 'formData.address_line_2',
            'placeholder': 'e.g. Apartment 4B',
        })
    )
    
    city = forms.CharField(
        label='City/Town',
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'x-model': 'formData.city',
            'placeholder': 'e.g. Johannesburg',
        })
    )
    
    PROVINCE_CHOICES = [
        ('', 'Select Province'),
        ('eastern_cape', 'Eastern Cape'),
        ('free_state', 'Free State'),
        ('gauteng', 'Gauteng'),
        ('kzn', 'KwaZulu-Natal'),
        ('limpopo', 'Limpopo'),
        ('mpumalanga', 'Mpumalanga'),
        ('north_west', 'North West'),
        ('northern_cape', 'Northern Cape'),
        ('western_cape', 'Western Cape'),
    ]
    
    province = forms.ChoiceField(
        label='Province',
        choices=PROVINCE_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-select',
            'x-model': 'formData.province',
        })
    )
    
    postal_code = forms.CharField(
        label='Postal Code',
        max_length=10,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'x-model': 'formData.postal_code',
            'placeholder': 'e.g. 2000',
            'x-mask': '9999',
        })
    )
    
    # Communication Preferences
    communication_preference = forms.ChoiceField(
        label='Preferred Method of Communication',
        choices=[
            ('email', 'Email'),
            ('sms', 'SMS'),
            ('whatsapp', 'WhatsApp'),
            ('call', 'Phone Call'),
        ],
        widget=forms.RadioSelect(attrs={
            'class': 'form-radio',
            'x-model': 'formData.communication_preference',
        })
    )
    
    def clean_phone_number(self):
        """Validate South African phone number"""
        phone = self.cleaned_data.get('phone_number', '').replace(' ', '')
        
        # Basic validation for South African phone numbers
        if not re.match(r'^(\+27|0)[6-8][0-9]{8}$', phone):
            raise ValidationError('Please enter a valid South African phone number')
        
        # Format as +27...
        if phone.startswith('0'):
            phone = '+27' + phone[1:]
        
        return phone
    
    def clean_alternate_phone(self):
        """Validate alternate phone number if provided"""
        phone = self.cleaned_data.get('alternate_phone', '').strip()
        
        if not phone:
            return ''
            
        phone = phone.replace(' ', '')
        
        # Basic validation for South African phone numbers
        if not re.match(r'^(\+27|0)[6-8][0-9]{8}$', phone):
            raise ValidationError('Please enter a valid South African phone number')
        
        # Format as +27...
        if phone.startswith('0'):
            phone = '+27' + phone[1:]
        
        return phone


class DIYBeneficiaryForm(forms.Form):
    """Form for adding/editing a single beneficiary"""
    
    RELATIONSHIP_CHOICES = [
        ('spouse', 'Spouse'),
        ('child', 'Child'),
        ('parent', 'Parent'),
        ('sibling', 'Sibling'),
        ('other_relative', 'Other Relative'),
        ('friend', 'Friend'),
        ('trust', 'Trust'),
        ('estate', 'Estate'),
    ]
    
    full_name = forms.CharField(
        label='Full Name',
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'x-model': 'beneficiary.full_name',
            'placeholder': 'Enter full name',
        })
    )
    
    id_number = forms.CharField(
        label='ID Number',
        required=False,
        max_length=13,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'x-model': 'beneficiary.id_number',
            'placeholder': 'Enter 13-digit ID number',
            'x-mask': '999999 9999 999',
        })
    )
    
    relationship = forms.ChoiceField(
        label='Relationship',
        choices=RELATIONSHIP_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-select',
            'x-model': 'beneficiary.relationship',
        })
    )
    
    percentage = forms.DecimalField(
        label='Allocation %',
        min_value=0.01,
        max_value=100,
        widget=forms.NumberInput(attrs={
            'class': 'form-input',
            'x-model': 'beneficiary.percentage',
            'step': '0.01',
            'min': '0.01',
            'max': '100',
        })
    )
    
    phone_number = forms.CharField(
        label='Phone Number',
        required=False,
        max_length=20,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'x-model': 'beneficiary.phone_number',
            'placeholder': 'e.g. 071 234 5678',
            'x-mask': '999 999 9999',
        })
    )
    
    email = forms.EmailField(
        label='Email Address',
        required=False,
        widget=forms.EmailInput(attrs={
            'class': 'form-input',
            'x-model': 'beneficiary.email',
            'placeholder': 'email@example.com',
        })
    )
    
    address = forms.CharField(
        label='Address',
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-textarea',
            'x-model': 'beneficiary.address',
            'rows': 2,
            'placeholder': 'Enter full address (optional)',
        })
    )
    
    is_primary = forms.BooleanField(
        label='Primary Beneficiary',
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-checkbox',
            'x-model': 'beneficiary.is_primary',
        })
    )
    
    def clean_id_number(self):
        """Validate South African ID number if provided"""
        id_number = self.cleaned_data.get('id_number', '').replace(' ', '')
        
        if not id_number:
            return ''
            
        if not re.match(r'^\d{13}$', id_number):
            raise ValidationError('ID number must be 13 digits')
            
        return id_number
    
    def clean_phone_number(self):
        """Validate phone number if provided"""
        phone = self.cleaned_data.get('phone_number', '').replace(' ', '')
        
        if not phone:
            return ''
            
        # Basic validation for South African phone numbers
        if not re.match(r'^(\+27|0)[6-8][0-9]{8}$', phone):
            raise ValidationError('Please enter a valid South African phone number')
        
        # Format as +27...
        if phone.startswith('0'):
            phone = '+27' + phone[1:]
            
        return phone


class DIYPolicyDetailsForm(forms.Form):
    """Form for policy details step"""
    
    POLICY_TYPES = [
        ('funeral', 'Funeral Cover'),
        ('life', 'Life Cover'),
        ('combined', 'Combined Cover'),
    ]
    
    COVER_AMOUNTS = [
        (10000, 'R10,000'),
        (20000, 'R20,000'),
        (30000, 'R30,000'),
        (50000, 'R50,000'),
        (75000, 'R75,000'),
        (100000, 'R100,000'),
        (150000, 'R150,000'),
        (200000, 'R200,000'),
        (250000, 'R250,000'),
        (300000, 'R300,000'),
        (400000, 'R400,000'),
        (500000, 'R500,000'),
        (1000000, 'R1,000,000'),
        (2000000, 'R2,000,000'),
        (3000000, 'R3,000,000'),
        (4000000, 'R4,000,000'),
        (5000000, 'R5,000,000'),
        ('other', 'Other Amount'),
    ]
    
    policy_type = forms.ChoiceField(
        label='Policy Type',
        choices=POLICY_TYPES,
        widget=forms.RadioSelect(attrs={
            'class': 'form-radio',
            'x-model': 'formData.policy_type',
        })
    )
    
    cover_amount = forms.ChoiceField(
        label='Cover Amount',
        choices=COVER_AMOUNTS,
        widget=forms.RadioSelect(attrs={
            'class': 'form-radio',
            'x-model': 'formData.cover_amount',
        })
    )
    
    custom_cover_amount = forms.DecimalField(
        label='Custom Cover Amount',
        required=False,
        min_value=1000,
        max_value=10000000,
        widget=forms.NumberInput(attrs={
            'class': 'form-input',
            'x-model': 'formData.custom_cover_amount',
            'x-show': 'formData.cover_amount === "other"',
            'min': '1000',
            'step': '1000',
        })
    )
    
    has_extended_family = forms.BooleanField(
        label='Include Extended Family Cover',
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-checkbox',
            'x-model': 'formData.has_extended_family',
        })
    )
    
    extended_family_members = forms.IntegerField(
        label='Number of Extended Family Members',
        required=False,
        min_value=1,
        max_value=20,
        initial=1,
        widget=forms.NumberInput(attrs={
            'class': 'form-input',
            'x-model': 'formData.extended_family_members',
            'x-bind:disabled': '!formData.has_extended_family',
            'min': '1',
            'max': '20',
        })
    )
    
    premium_frequency = forms.ChoiceField(
        label='Premium Frequency',
        choices=[
            ('monthly', 'Monthly'),
            ('quarterly', 'Quarterly'),
            ('annually', 'Annually'),
        ],
        widget=forms.RadioSelect(attrs={
            'class': 'form-radio',
            'x-model': 'formData.premium_frequency',
        })
    )
    
    def clean(self):
        cleaned_data = super().clean()
        
        # If 'other' cover amount is selected, ensure custom_cover_amount is provided
        if cleaned_data.get('cover_amount') == 'other' and not cleaned_data.get('custom_cover_amount'):
            self.add_error('custom_cover_amount', 'Please specify a custom cover amount')
        
        # If extended family is selected, ensure number of members is provided
        if cleaned_data.get('has_extended_family') and not cleaned_data.get('extended_family_members'):
            self.add_error('extended_family_members', 'Please specify the number of extended family members')
        
        return cleaned_data
    
    def clean_custom_cover_amount(self):
        """Validate custom cover amount"""
        cover_amount = self.cleaned_data.get('cover_amount')
        custom_amount = self.cleaned_data.get('custom_cover_amount')
        
        if cover_amount == 'other' and not custom_amount:
            raise ValidationError('Please specify a custom cover amount')
            
        if custom_amount:
            if custom_amount < 1000:
                raise ValidationError('Minimum cover amount is R1,000')
            if custom_amount > 10000000:  # R10 million
                raise ValidationError('Maximum cover amount is R10,000,000')
                
        return custom_amount


class DIYPaymentOptionsForm(forms.Form):
    """Form for payment options step"""
    
    PAYMENT_METHODS = [
        ('debit_order', 'Debit Order'),
        ('eft', 'Electronic Funds Transfer (EFT)'),
    ]
    
    BANK_CHOICES = [
        ('', 'Select Bank'),
        ('absa', 'ABSA'),
        ('fnb', 'First National Bank (FNB)'),
        ('nedbank', 'Nedbank'),
        ('standard', 'Standard Bank'),
        ('capitec', 'Capitec Bank'),
        ('investec', 'Investec'),
        ('african_bank', 'African Bank'),
        ('bidvest', 'Bidvest Bank'),
        ('other', 'Other'),
    ]
    
    ACCOUNT_TYPES = [
        ('savings', 'Savings Account'),
        ('cheque', 'Cheque Account'),
        ('transmission', 'Transmission Account'),
        ('other', 'Other'),
    ]
    
    payment_method = forms.ChoiceField(
        label='Payment Method',
        choices=PAYMENT_METHODS,
        widget=forms.RadioSelect(attrs={
            'class': 'form-radio',
            'x-model': 'formData.payment_method',
        })
    )
    
    # Bank Details (for debit order)
    bank_name = forms.ChoiceField(
        label='Bank Name',
        choices=BANK_CHOICES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select',
            'x-model': 'formData.bank_name',
            'x-bind:required': 'formData.payment_method === "debit_order"',
        })
    )
    
    account_number = forms.CharField(
        label='Account Number',
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'x-model': 'formData.account_number',
            'x-bind:required': 'formData.payment_method === "debit_order"',
            'inputmode': 'numeric',
            'pattern': r'\d*',
            'placeholder': 'e.g. 1234567890',
        })
    )
    
    account_type = forms.ChoiceField(
        label='Account Type',
        choices=ACCOUNT_TYPES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select',
            'x-model': 'formData.account_type',
            'x-bind:required': 'formData.payment_method === "debit_order"',
        })
    )
    
    branch_code = forms.CharField(
        label='Branch Code',
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'x-model': 'formData.branch_code',
            'x-bind:required': 'formData.payment_method === "debit_order"',
            'inputmode': 'numeric',
            'pattern': r'\d*',
            'placeholder': 'e.g. 123456',
        })
    )
    
    account_holder_name = forms.CharField(
        label='Account Holder Name',
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'x-model': 'formData.account_holder_name',
            'x-bind:required': 'formData.payment_method === "debit_order"',
            'x-bind:disabled': 'formData.same_as_member',
            'x-bind:class': '{ "bg-gray-100": formData.same_as_member }',
            'placeholder': 'Full name as it appears on bank account',
        })
    )
    
    same_as_member = forms.BooleanField(
        label='Account holder is the same as the policyholder',
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-checkbox',
            'x-model': 'formData.same_as_member',
        })
    )
    
    debit_day = forms.ChoiceField(
        label='Debit Day',
        choices=[(str(i), str(i)) for i in range(1, 29)],
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select',
            'x-model': 'formData.debit_day',
            'x-bind:required': 'formData.payment_method === "debit_order"',
        })
    )
    
    terms_accepted = forms.BooleanField(
        label='I accept the debit order terms and conditions',
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-checkbox',
            'x-model': 'formData.terms_accepted',
            'x-bind:required': 'formData.payment_method === "debit_order"',
        })
    )
    
    marketing_consent = forms.BooleanField(
        label='I agree to receive marketing communications',
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-checkbox',
            'x-model': 'formData.marketing_consent',
        })
    )
    
    def clean(self):
        cleaned_data = super().clean()
        payment_method = cleaned_data.get('payment_method')
        
        # If payment method is debit order, validate all debit order fields
        if payment_method == 'debit_order':
            required_fields = [
                'bank_name',
                'account_number',
                'account_type',
                'branch_code',
                'terms_accepted',
            ]
            
            for field in required_fields:
                if not cleaned_data.get(field):
                    self.add_error(field, 'This field is required for debit order payments')
            
            # If account holder is not same as member, account_holder_name is required
            if not cleaned_data.get('same_as_member') and not cleaned_data.get('account_holder_name'):
                self.add_error('account_holder_name', 'Please enter the account holder name')
        
        return cleaned_data
    
    def clean_account_number(self):
        """Validate account number"""
        account_number = self.cleaned_data.get('account_number', '')
        
        if account_number and not account_number.isdigit():
            raise ValidationError('Account number must contain only digits')
            
        return account_number
    
    def clean_branch_code(self):
        """Validate branch code"""
        branch_code = self.cleaned_data.get('branch_code', '')
        
        if branch_code and not branch_code.isdigit():
            raise ValidationError('Branch code must contain only digits')
            
        return branch_code


class DIYApplicationConsentForm(forms.Form):
    """Form for final consent and submission"""
    
    terms_accepted = forms.BooleanField(
        label='I accept the Terms and Conditions',
        required=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'focus:ring-blue-500 h-4 w-4 text-blue-600 border-gray-300 rounded',
            'x-model': 'termsAccepted',
            'required': 'required',
        })
    )
    
    popia_consent = forms.BooleanField(
        label='I consent to the processing of my personal information in accordance with POPIA',
        required=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'focus:ring-blue-500 h-4 w-4 text-blue-600 border-gray-300 rounded',
            'required': 'required',
        })
    )
    
    fsca_disclosure = forms.BooleanField(
        label='I acknowledge receipt of the FSP disclosure as required by FSCA',
        required=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'focus:ring-blue-500 h-4 w-4 text-blue-600 border-gray-300 rounded',
            'required': 'required',
        })
    )
    
    marketing_consent = forms.BooleanField(
        label='I consent to receive marketing communications',
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'focus:ring-blue-500 h-4 w-4 text-blue-600 border-gray-300 rounded',
            'x-model': 'marketingConsent',
        })
    )
    
    def clean(self):
        cleaned_data = super().clean()
        
        # All required checkboxes must be checked
        for field in ['terms_accepted', 'popia_consent', 'fsca_disclosure']:
            if not cleaned_data.get(field):
                self.add_error(field, 'This field is required')
        
        return cleaned_data
