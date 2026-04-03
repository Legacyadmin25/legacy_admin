from django import forms
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone
from django.contrib import messages

from .views_diy_base import DIYBaseView, DIYCompletionView
from .models_incomplete import IncompleteApplication
from settings_app.models import Agent

# Form classes for each step
class PersonalDetailsForm(forms.Form):
    """Form for personal details step"""
    title = forms.ChoiceField(
        choices=[
            ('', 'Select Title'),
            ('Mr', 'Mr'),
            ('Mrs', 'Mrs'),
            ('Ms', 'Ms'),
            ('Dr', 'Dr'),
            ('Prof', 'Prof'),
        ],
        required=True,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    first_name = forms.CharField(max_length=100, required=True)
    last_name = forms.CharField(max_length=100, required=True)
    id_number = forms.CharField(max_length=13, required=False)
    passport_number = forms.CharField(max_length=20, required=False)
    date_of_birth = forms.DateField(
        required=True,
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    gender = forms.ChoiceField(
        choices=[
            ('', 'Select Gender'),
            ('Male', 'Male'),
            ('Female', 'Female'),
        ],
        required=True
    )
    is_south_african = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'x-model': 'isSouthAfrican'})
    )
    
    def clean(self):
        cleaned_data = super().clean()
        is_south_african = cleaned_data.get('is_south_african')
        id_number = cleaned_data.get('id_number')
        passport_number = cleaned_data.get('passport_number')
        
        if is_south_african and not id_number:
            self.add_error('id_number', 'ID number is required for South African citizens')
        elif not is_south_african and not passport_number:
            self.add_error('passport_number', 'Passport number is required for non-South African citizens')
        
        return cleaned_data


class ContactInfoForm(forms.Form):
    """Form for contact information step"""
    phone_number = forms.CharField(max_length=20, required=True)
    email = forms.EmailField(required=True)
    alternate_phone = forms.CharField(max_length=20, required=False)
    
    # Address fields
    address_line_1 = forms.CharField(max_length=255, required=True)
    address_line_2 = forms.CharField(max_length=255, required=False)
    city = forms.CharField(max_length=100, required=True)
    province = forms.CharField(max_length=100, required=True)
    postal_code = forms.CharField(max_length=10, required=True)


class BeneficiaryForm(forms.Form):
    """Form for beneficiary details step"""
    full_name = forms.CharField(max_length=200, required=True)
    id_number = forms.CharField(max_length=13, required=False)
    relationship = forms.ChoiceField(
        choices=[
            ('', 'Select Relationship'),
            ('spouse', 'Spouse'),
            ('child', 'Child'),
            ('parent', 'Parent'),
            ('sibling', 'Sibling'),
            ('other_relative', 'Other Relative'),
            ('friend', 'Friend'),
        ],
        required=True
    )
    percentage = forms.DecimalField(
        max_digits=5,
        decimal_places=2,
        min_value=0.01,
        max_value=100,
        required=True
    )
    phone_number = forms.CharField(max_length=20, required=False)
    email = forms.EmailField(required=False)


class PolicyDetailsForm(forms.Form):
    """Form for policy details step"""
    plan = forms.ChoiceField(
        choices=[],  # Will be populated in __init__
        required=True
    )
    cover_amount = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=True
    )
    premium_amount = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=True
    )
    has_spouse = forms.BooleanField(required=False)
    has_children = forms.BooleanField(required=False)
    children_count = forms.IntegerField(min_value=0, required=False)
    has_extended_family = forms.BooleanField(required=False)
    extended_family_count = forms.IntegerField(min_value=0, required=False)
    
    def __init__(self, *args, **kwargs):
        scheme = kwargs.pop('scheme', None)
        super().__init__(*args, **kwargs)
        
        # Populate plan choices if scheme is provided
        if scheme and hasattr(scheme, 'plans'):
            self.fields['plan'].choices = [('', 'Select Plan')] + [
                (plan.id, plan.name) for plan in scheme.plans.all()
            ]


class PaymentOptionsForm(forms.Form):
    """Form for payment options step"""
    payment_method = forms.ChoiceField(
        choices=[
            ('', 'Select Payment Method'),
            ('debit_order', 'Debit Order'),
            ('eft', 'Electronic Funds Transfer (EFT)'),
            ('easypay', 'Easypay QR Code'),
        ],
        required=True,
        widget=forms.Select(attrs={'x-model': 'paymentMethod'})
    )
    
    # Debit order fields
    bank_name = forms.CharField(max_length=100, required=False)
    account_number = forms.CharField(max_length=50, required=False)
    account_type = forms.ChoiceField(
        choices=[
            ('', 'Select Account Type'),
            ('current', 'Current Account'),
            ('savings', 'Savings Account'),
            ('transmission', 'Transmission Account'),
        ],
        required=False
    )
    branch_code = forms.CharField(max_length=20, required=False)
    account_holder_name = forms.CharField(max_length=100, required=False)
    debit_day = forms.IntegerField(min_value=1, max_value=28, required=False)
    
    # Terms and consent
    terms_accepted = forms.BooleanField(required=True)
    marketing_consent = forms.BooleanField(required=False)
    popia_consent = forms.BooleanField(required=True)
    
    def clean(self):
        cleaned_data = super().clean()
        payment_method = cleaned_data.get('payment_method')
        
        # Validate debit order fields if debit order is selected
        if payment_method == 'debit_order':
            required_fields = [
                'bank_name', 'account_number', 'account_type',
                'branch_code', 'account_holder_name', 'debit_day'
            ]
            
            for field in required_fields:
                if not cleaned_data.get(field):
                    self.add_error(field, f'This field is required for debit order payments')
        
        return cleaned_data


class ReviewForm(forms.Form):
    """Form for review step"""
    confirm_details = forms.BooleanField(
        required=True,
        label='I confirm that all the information provided is correct'
    )


# Step Views
class PersonalDetailsView(DIYBaseView):
    """View for personal details step"""
    template_name = 'members/diy/steps/01_personal_details.html'
    form_class = PersonalDetailsForm
    step_number = 1
    
    def process_form_data(self, form):
        # Save personal details to incomplete application
        if self.incomplete_application:
            # Add phone number to incomplete application for easier identification
            if 'phone_number' in form.cleaned_data:
                self.incomplete_application.phone_number = form.cleaned_data['phone_number']
                self.incomplete_application.save(update_fields=['phone_number'])


class ContactInfoView(DIYBaseView):
    """View for contact information step"""
    template_name = 'members/diy/steps/02_contact_information.html'
    form_class = ContactInfoForm
    step_number = 2
    
    def process_form_data(self, form):
        # Save contact info to incomplete application
        if self.incomplete_application:
            # Add phone number to incomplete application for easier identification
            self.incomplete_application.phone_number = form.cleaned_data['phone_number']
            self.incomplete_application.save(update_fields=['phone_number'])


class BeneficiariesView(DIYBaseView):
    """View for beneficiaries step"""
    template_name = 'members/diy/steps/03_beneficiaries.html'
    form_class = BeneficiaryForm
    step_number = 3
    
    def process_form_data(self, form):
        # Beneficiary data is saved via auto-save
        pass


class PolicyDetailsView(DIYBaseView):
    """View for policy details step"""
    template_name = 'members/diy/steps/04_policy_details.html'
    form_class = PolicyDetailsForm
    step_number = 4
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['scheme'] = self.scheme
        return kwargs
    
    def process_form_data(self, form):
        # Policy details are saved via auto-save
        pass


class PaymentOptionsView(DIYBaseView):
    """View for payment options step"""
    template_name = 'members/diy/steps/05_payment_options.html'
    form_class = PaymentOptionsForm
    step_number = 5
    
    def process_form_data(self, form):
        # Payment options are saved via auto-save
        pass


class ReviewView(DIYBaseView):
    """View for review step"""
    template_name = 'members/diy/steps/06_review_submit.html'
    form_class = ReviewForm
    step_number = 6
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add all form data from previous steps
        if self.incomplete_application:
            context['all_data'] = self.incomplete_application.form_data
        
        return context
    
    def process_form_data(self, form):
        # Review step - no specific data to save
        pass


class ConfirmationView(DIYCompletionView):
    """View for confirmation step after submission"""
    template_name = 'members/diy/steps/07_success.html'
    step_number = 7
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_step'] = self.step_number
        context['total_steps'] = 7
        context['steps'] = range(1, 8)
        
        # Add step labels
        context['step_labels'] = {
            1: 'Personal Details',
            2: 'Contact Info',
            3: 'Beneficiaries',
            4: 'Policy Details',
            5: 'Payment Options',
            6: 'Review',
            7: 'Confirmation'
        }
        
        return context
