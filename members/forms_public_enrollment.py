"""
Public Enrollment Forms - Separate from admin forms
Support conditional/smart questions based on answers
"""

from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from .models_public_enrollment import (
    PublicApplication, EnrollmentOTPVerification, POPIAConsent, 
    EnrollmentQuestionBank, ApplicationAnswer
)
from .models import Member
from .utils import luhn_check, validate_sa_id
from datetime import date


class EnrollmentLinkAccessForm(forms.Form):
    """
    Initial form shown when accessing public enrollment link
    Verifies the token and shows scheme/plan information
    """
    token_input = forms.CharField(
        widget=forms.HiddenInput(),
        required=False
    )


class PersonalDetailsPublicForm(forms.ModelForm):
    """
    Step 1: Personal Details for public enrollment
    Validates SA ID or accepts passport for foreigners
    """
    ID_TYPE_CHOICES = [
        ('id_number', 'South African ID Number'),
        ('passport', 'Passport'),
    ]
    
    id_type = forms.ChoiceField(
        choices=ID_TYPE_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        required=True,
        label='Identification Type'
    )
    
    class Meta:
        model = PublicApplication
        fields = [
            'title',
            'first_name',
            'last_name',
            'email',
            'phone_number',
            'id_number',
            'passport_number',
            'date_of_birth',
            'gender',
            'marital_status',
        ]
        widgets = {
            'title': forms.Select(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'First Name'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Last Name'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Email address'
            }),
            'phone_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Phone number (e.g., 0712345678)',
                'pattern': '[0-9]{10}'
            }),
            'id_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'ID number (13 digits)',
                'maxlength': '13',
                'pattern': '[0-9]{13}'
            }),
            'passport_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Passport number',
                'id': 'id_passport_number'
            }),
            'date_of_birth': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control',
                'max': date.today().isoformat()
            }),
            'gender': forms.Select(attrs={'class': 'form-control'}),
            'marital_status': forms.Select(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['title'].choices = [
            ('', '-- Select Title --'),
            ('Mr', 'Mr.'),
            ('Mrs', 'Mrs.'),
            ('Ms', 'Ms.'),
            ('Miss', 'Miss.'),
            ('Dr', 'Dr.'),
            ('Prof', 'Prof.'),
            ('Other', 'Other'),
        ]
        
        # Determine initial id_type based on instance data
        if self.instance and self.instance.passport_number and not self.instance.id_number:
            self.fields['id_type'].initial = 'passport'
        else:
            self.fields['id_type'].initial = 'id_number'
        
        self.fields['passport_number'].required = False
        self.fields['id_number'].required = False
    
    def clean(self):
        cleaned = super().clean()
        id_type = cleaned.get('id_type', 'id_number')
        id_number = cleaned.get('id_number', '').strip() if cleaned.get('id_number') else ''
        passport_number = cleaned.get('passport_number', '').strip() if cleaned.get('passport_number') else ''
        
        if id_type == 'id_number':
            # South African citizen - must have valid ID
            if not id_number:
                self.add_error('id_number', 'SA ID number is required.')
                return cleaned
            
            # Validate Luhn
            if not luhn_check(id_number):
                self.add_error('id_number', 'Invalid SA ID number (failed Luhn check).')
                return cleaned
            
            # Extract DOB and gender from ID
            valid, dob, gender = validate_sa_id(id_number)
            if not valid:
                self.add_error('id_number', 'Invalid ID number format.')
                return cleaned
            
            # Auto-fill DOB and gender
            cleaned['date_of_birth'] = dob
            cleaned['gender'] = gender
            # Clear passport when using ID
            cleaned['passport_number'] = ''
        else:  # passport
            # Foreign national - must have passport
            if not passport_number:
                self.add_error('passport_number', 'Passport number is required.')
                return cleaned
            # Clear ID when using passport
            cleaned['id_number'] = ''
        
        return cleaned


class AddressPublicForm(forms.ModelForm):
    """
    Step 2: Address Details for public enrollment
    """
    class Meta:
        model = PublicApplication
        fields = [
            'physical_address_line_1',
            'physical_address_line_2',
            'physical_address_city',
            'physical_address_postal_code',
        ]
        widgets = {
            'physical_address_line_1': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Street address'
            }),
            'physical_address_line_2': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Suburb/Complex (optional)'
            }),
            'physical_address_city': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'City/Town'
            }),
            'physical_address_postal_code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Postal code',
                'maxlength': '10'
            }),
        }


class PlanSelectionPublicForm(forms.ModelForm):
    """
    Step 3: Plan Selection for public enrollment
    Shows available plans for the scheme with pricing
    """
    class Meta:
        model = PublicApplication
        fields = ['plan', 'payment_method']
        widgets = {
            'plan': forms.RadioSelect(attrs={'class': 'form-check-input'}),
            'payment_method': forms.RadioSelect(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, scheme=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        if scheme:
            # Filter plans by age (when available from previous step)
            from schemes.models import Plan
            self.fields['plan'].queryset = Plan.objects.filter(
                scheme=scheme,
                is_active=True
            ).order_by('premium')
        
        # Payment method choices
        self.fields['payment_method'].choices = [
            ('DEBIT_ORDER', 'Monthly Debit Order (Automatic)'),
            ('EASYPAY', 'EasyPay (Pay at stores)'),
            ('EFT', 'EFT Transfer (Manual)'),
        ]


class PaymentDetailsPublicForm(forms.ModelForm):
    """
    Step 4: Payment Method Details (if debit order selected)
    Conditionally shown based on payment_method choice
    """
    class Meta:
        model = PublicApplication
        fields = [
            'bank',
            'branch_code',
            'account_holder_name',
            'account_number',
            'debit_instruction_day',
        ]
        widgets = {
            'bank': forms.Select(attrs={'class': 'form-control'}),
            'branch_code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Branch code',
                'maxlength': '10',
                'readonly': True
            }),
            'account_holder_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Account holder name'
            }),
            'account_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Account number',
                'maxlength': '20'
            }),
            'debit_instruction_day': forms.Select(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Populate debit days
        self.fields['debit_instruction_day'].choices = [
            ('', '-- Select Day --'),
        ] + [(str(i), f"Day {i}") for i in range(1, 29)]
        
        # Make optional fields not required for now
        self.fields['bank'].required = False
        self.fields['branch_code'].required = False
        self.fields['account_holder_name'].required = False
        self.fields['account_number'].required = False
        self.fields['debit_instruction_day'].required = False
    
    def clean(self):
        cleaned = super().clean()
        bank = cleaned.get('bank')
        account_number = cleaned.get('account_number')
        
        if bank and not account_number:
            self.add_error('account_number', 'Account number is required')
        
        return cleaned


class ConditionalQuestionForm(forms.Form):
    """
    Dynamic form for conditional questions during enrollment
    Built from EnrollmentQuestionBank
    """
    def __init__(self, question, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        field_name = question.question_key
        
        if question.question_type == 'text':
            self.fields[field_name] = forms.CharField(
                label=question.question_text,
                help_text=question.help_text_content,
                required=question.is_required,
                widget=forms.TextInput(attrs={'class': 'form-control'})
            )
        
        elif question.question_type == 'number':
            self.fields[field_name] = forms.IntegerField(
                label=question.question_text,
                help_text=question.help_text_content,
                required=question.is_required,
                widget=forms.NumberInput(attrs={'class': 'form-control'})
            )
        
        elif question.question_type == 'email':
            self.fields[field_name] = forms.EmailField(
                label=question.question_text,
                help_text=question.help_text_content,
                required=question.is_required,
                widget=forms.EmailInput(attrs={'class': 'form-control'})
            )
        
        elif question.question_type == 'phone':
            self.fields[field_name] = forms.CharField(
                label=question.question_text,
                help_text=question.help_text_content,
                required=question.is_required,
                widget=forms.TextInput(attrs={
                    'class': 'form-control',
                    'pattern': '[0-9]{10}'
                })
            )
        
        elif question.question_type == 'date':
            self.fields[field_name] = forms.DateField(
                label=question.question_text,
                help_text=question.help_text_content,
                required=question.is_required,
                widget=forms.DateInput(attrs={
                    'type': 'date',
                    'class': 'form-control'
                })
            )
        
        elif question.question_type == 'choice':
            choices = [('', '-- Select --')] + [
                (opt, opt) for opt in question.options
            ] if question.options else []
            
            self.fields[field_name] = forms.ChoiceField(
                label=question.question_text,
                help_text=question.help_text_content,
                required=question.is_required,
                choices=choices,
                widget=forms.Select(attrs={'class': 'form-control'})
            )
        
        elif question.question_type == 'yes_no':
            self.fields[field_name] = forms.ChoiceField(
                label=question.question_text,
                help_text=question.help_text_content,
                required=question.is_required,
                choices=[('', '-- Select --'), ('Yes', 'Yes'), ('No', 'No')],
                widget=forms.RadioSelect(attrs={'class': 'form-check-input'})
            )
        
        elif question.question_type == 'checkbox':
            self.fields[field_name] = forms.BooleanField(
                label=question.question_text,
                help_text=question.help_text_content,
                required=question.is_required,
                widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
            )


class POPIAConsentForm(forms.Form):
    """
    POPIA Consent + Terms & Conditions Agreement
    Final step before OTP verification
    """
    agree_to_terms = forms.BooleanField(
        label='I have read and agree to the Terms and Conditions',
        required=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    agree_to_privacy = forms.BooleanField(
        label='I have read and agree to the Privacy Policy',
        required=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    consent_data_processing = forms.BooleanField(
        label='I consent to my personal information being processed',
        required=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    consent_marketing_sms = forms.BooleanField(
        label='I would like to receive promotional SMS messages',
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    consent_marketing_email = forms.BooleanField(
        label='I would like to receive promotional emails',
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )


class OTPVerificationForm(forms.Form):
    """
    OTP Verification Form
    User enters 6-digit code sent to their phone
    """
    otp_code = forms.CharField(
        label='Enter OTP',
        max_length=6,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg text-center',
            'placeholder': '000000',
            'pattern': '[0-9]{6}',
            'maxlength': '6',
            'inputmode': 'numeric',
            'autocomplete': 'off',
            'style': 'font-size: 24px; letter-spacing: 10px;'
        })
    )
    
    def clean_otp_code(self):
        otp = self.cleaned_data.get('otp_code')
        
        if not otp:
            raise ValidationError('OTP code is required.')
        
        if len(otp) != 6:
            raise ValidationError('OTP must be 6 digits.')
        
        if not otp.isdigit():
            raise ValidationError('OTP must contain only numbers.')
        
        return otp


class OTPResendForm(forms.Form):
    """
    Simple form for requesting OTP resend
    """
    pass


class ApplicationReviewForm(forms.ModelForm):
    """
    Admin form for reviewing and approving/rejecting applications
    """
    action = forms.ChoiceField(
        choices=[('', '-- Select Action --'), ('approve', 'Approve'), ('reject', 'Reject')],
        required=True,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    review_notes = forms.CharField(
        label='Review Notes',
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Add any notes about this application'
        })
    )
    
    class Meta:
        model = PublicApplication
        fields = ['review_notes']
