import json
import uuid
import base64
from datetime import datetime, timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponseServerError
from django.views import View
from django.views.generic import TemplateView, FormView, RedirectView
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse, reverse_lazy
from django.db import transaction
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from .models_diy import DIYApplication, DIYApplicant, DIYBeneficiary, DIYApplicationDocument
from .forms_diy import (
    DIYPersonalDetailsForm, 
    DIYContactInformationForm, 
    DIYBeneficiaryForm, 
    DIYPolicyDetailsForm, 
    DIYPaymentOptionsForm,
    DIYApplicationConsentForm
)
from settings_app.models import Agent
from schemes.models import Plan, PlanTier
from .utils.plan_chat import get_plan_answer
from .utils.ocr_processor import process_id_document


class DIYApplicationMixin:
    """Mixin to handle common DIY application functionality"""
    
    def get_application(self, request, *args, **kwargs):
        """Get or create application from session"""
        application_id = request.session.get('diy_application_id')
        
        if application_id:
            try:
                return DIYApplication.objects.get(application_id=application_id)
            except DIYApplication.DoesNotExist:
                pass
                
        # Create a new application
        application = DIYApplication(
            status='draft',
            reference_number=None,  # Will be set on save
        )
        
        # Set agent if available
        agent_code = request.session.get('diy_agent_code')
        if agent_code:
            try:
                agent = Agent.objects.get(agent_code=agent_code, is_active=True)
                application.agent = agent
                application.agent_code = agent_code
            except Agent.DoesNotExist:
                pass
                
        application.save()
        request.session['diy_application_id'] = str(application.application_id)
        return application
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_step'] = self.step_number
        context['total_steps'] = 6
        context['progress'] = int((self.step_number / context['total_steps']) * 100)
        
        # Add application data to context
        application = self.get_application(self.request)
        context['application'] = application
        
        # Add form data from session
        form_data = self.request.session.get('diy_form_data', {})
        context['form_data'] = form_data
        
        return context


class DIYStartView(TemplateView):
    """Initial view for DIY application with agent code"""
    template_name = 'members/diy/start.html'
    
    def get(self, request, *args, **kwargs):
        # Clear any existing session data
        if 'diy_application_id' in request.session:
            del request.session['diy_application_id']
        if 'diy_form_data' in request.session:
            del request.session['diy_form_data']
            
        # Get agent code from URL or default to None
        agent_code = kwargs.get('agent_code')
        
        if agent_code:
            # Validate agent code
            try:
                agent = Agent.objects.get(agent_code=agent_code, is_active=True)
                request.session['diy_agent_code'] = agent_code
                return redirect('members:diy_personal_details')
            except Agent.DoesNotExist:
                messages.error(request, 'Invalid agent code. Please check and try again.')
        
        return super().get(request, *args, **kwargs)
    
    def post(self, request, *args, **kwargs):
        agent_code = request.POST.get('agent_code')
        if agent_code:
            try:
                agent = Agent.objects.get(agent_code=agent_code, is_active=True)
                request.session['diy_agent_code'] = agent_code
                return redirect('members:diy_personal_details')
            except Agent.DoesNotExist:
                messages.error(request, 'Invalid agent code. Please check and try again.')
        
        return self.get(request, *args, **kwargs)


class DIYPersonalDetailsView(FormView, DIYApplicationMixin):
    """Step 1: Personal details form"""
    template_name = 'members/diy/step1_personal.html'
    form_class = DIYPersonalDetailsForm
    step_number = 1
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        form_data = self.request.session.get('diy_form_data', {})
        if self.request.method == 'GET' and form_data.get('personal'):
            kwargs['data'] = form_data['personal']
        return kwargs
    
    def form_valid(self, form):
        # Save form data to session
        form_data = self.request.session.get('diy_form_data', {})
        form_data['personal'] = form.cleaned_data
        self.request.session['diy_form_data'] = form_data
        
        # Create or update application
        application = self.get_application(self.request)
        
        # Create or update applicant
        applicant, created = DIYApplicant.objects.update_or_create(
            application=application,
            defaults={
                'title': form.cleaned_data['title'],
                'first_name': form.cleaned_data['first_name'],
                'middle_name': form.cleaned_data.get('middle_name', ''),
                'last_name': form.cleaned_data['last_name'],
                'id_number': form.cleaned_data['id_number'],
                'date_of_birth': form.cleaned_data['date_of_birth'],
                'gender': form.cleaned_data['gender'],
                'marital_status': form.cleaned_data['marital_status'],
                'is_south_african': form.cleaned_data['is_south_african'],
                'passport_number': form.cleaned_data.get('passport_number'),
            }
        )
        
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse('members:diy_contact_information')


class DIYContactInformationView(FormView, DIYApplicationMixin):
    """Step 2: Contact information form"""
    template_name = 'members/diy/step2_contact.html'
    form_class = DIYContactInformationForm
    step_number = 2
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        form_data = self.request.session.get('diy_form_data', {})
        if self.request.method == 'GET' and form_data.get('contact'):
            kwargs['data'] = form_data['contact']
        return kwargs
    
    def form_valid(self, form):
        # Save form data to session
        form_data = self.request.session.get('diy_form_data', {})
        form_data['contact'] = form.cleaned_data
        self.request.session['diy_form_data'] = form_data
        
        # Update applicant with contact information
        application = self.get_application(self.request)
        try:
            applicant = application.applicant
            applicant.email = form.cleaned_data['email']
            applicant.phone_number = form.cleaned_data['phone_number']
            applicant.alternate_phone = form.cleaned_data.get('alternate_phone')
            applicant.address_line_1 = form.cleaned_data['address_line_1']
            applicant.address_line_2 = form.cleaned_data.get('address_line_2', '')
            applicant.city = form.cleaned_data['city']
            applicant.province = form.cleaned_data['province']
            applicant.postal_code = form.cleaned_data['postal_code']
            applicant.communication_preference = form.cleaned_data['communication_preference']
            applicant.save()
        except DIYApplicant.DoesNotExist:
            # Shouldn't happen if they completed step 1 first
            messages.error(self.request, 'Please complete the personal details first.')
            return redirect('members:diy_personal_details')
        
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse('members:diy_beneficiaries')


class DIYBeneficiariesView(TemplateView, DIYApplicationMixin):
    """Step 3: Add beneficiaries"""
    template_name = 'members/diy/step3_beneficiaries.html'
    step_number = 3
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        application = self.get_application(self.request)
        context['beneficiaries'] = application.beneficiaries.all()
        return context
    
    def post(self, request, *args, **kwargs):
        action = request.POST.get('action')
        
        if action == 'add_beneficiary':
            form = DIYBeneficiaryForm(request.POST)
            if form.is_valid():
                application = self.get_application(request)
                
                # Calculate total percentage
                total_percentage = sum(
                    b.percentage for b in application.beneficiaries.all()
                )
                
                if total_percentage + form.cleaned_data['percentage'] > 100:
                    messages.error(request, 'Total percentage cannot exceed 100%')
                    return self.get(request, *args, **kwargs)
                
                # Create beneficiary
                DIYBeneficiary.objects.create(
                    application=application,
                    full_name=form.cleaned_data['full_name'],
                    id_number=form.cleaned_data.get('id_number'),
                    relationship=form.cleaned_data['relationship'],
                    percentage=form.cleaned_data['percentage'],
                    phone_number=form.cleaned_data.get('phone_number'),
                    email=form.cleaned_data.get('email'),
                    address=form.cleaned_data.get('address'),
                    is_primary=form.cleaned_data.get('is_primary', False),
                )
                
                messages.success(request, 'Beneficiary added successfully')
                return redirect('members:diy_beneficiaries')
            
            # Form is invalid, show errors
            context = self.get_context_data()
            context['beneficiary_form'] = form
            return self.render_to_response(context)
        
        elif action == 'delete_beneficiary':
            beneficiary_id = request.POST.get('beneficiary_id')
            try:
                beneficiary = DIYBeneficiary.objects.get(
                    id=beneficiary_id,
                    application__application_id=request.session.get('diy_application_id')
                )
                beneficiary.delete()
                messages.success(request, 'Beneficiary removed successfully')
            except DIYBeneficiary.DoesNotExist:
                messages.error(request, 'Beneficiary not found')
            
            return redirect('members:diy_beneficiaries')
        
        elif action == 'continue':
            # Validate at least one beneficiary
            application = self.get_application(request)
            if not application.beneficiaries.exists():
                messages.error(request, 'Please add at least one beneficiary')
                return self.get(request, *args, **kwargs)
                
            # Validate total percentage is 100%
            total_percentage = sum(
                b.percentage for b in application.beneficiaries.all()
            )
            
            if total_percentage != 100:
                messages.error(request, 'Total beneficiary allocation must be exactly 100%')
                return self.get(request, *args, **kwargs)
                
            return redirect('members:diy_policy_details')
        
        return self.get(request, *args, **kwargs)
    
    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        context['beneficiary_form'] = DIYBeneficiaryForm()
        return self.render_to_response(context)


class DIYPolicySelectionView(TemplateView, DIYApplicationMixin):
    """Step 2: Plan selection with LegacyGuide AI assistant"""
    template_name = 'members/diy/step2_plan_selection.html'
    step_number = 2
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get all plans that are visible in DIY flow
        plans = Plan.objects.filter(is_diy_visible=True, is_active=True)
        
        # Get the application
        application = self.get_application(self.request)
        context['application'] = application
        
        # Get selected plan if any
        selected_plan_id = None
        if application.plan:
            selected_plan_id = application.plan.id
        context['selected_plan_id'] = selected_plan_id
        
        # Add plans directly to the context
        context['plans'] = plans
        
        # Format plans for Alpine.js (if needed)
        plans_data = []
        for plan in plans:
            # Get tiers for this plan
            tiers = plan.plan_tiers.all()
            
            # Format tier data
            tier_data = []
            for tier in tiers:
                tier_data.append({
                    'id': tier.id,
                    'user_type': tier.get_user_type_display(),
                    'min_age': tier.min_age,
                    'max_age': tier.max_age,
                    'cover': tier.cover_amount,
                    'premium': tier.premium_amount
                })
            
            # Get main member tier (first tier with user_type='main')
            main_tier = next((t for t in tiers if t.user_type == 'main'), None)
            spouse_tier = next((t for t in tiers if t.user_type == 'spouse'), None)
            child_tier = next((t for t in tiers if t.user_type == 'child'), None)
            extended_tier = next((t for t in tiers if t.user_type == 'extended'), None)
            
            # Get waiting period
            waiting_period = getattr(plan, 'waiting_period', 0)
            
            # Create plan data
            plan_data = {
                'id': plan.id,
                'name': plan.name,
                'description': plan.description or '',
                'premium': main_tier.premium_amount if main_tier else 0,
                'main_cover': main_tier.cover_amount if main_tier else 0,
                'main_premium': main_tier.premium_amount if main_tier else 0,
                'spouse_cover': spouse_tier.cover_amount if spouse_tier else 0,
                'spouse_premium': spouse_tier.premium_amount if spouse_tier else 0,
                'child_cover': child_tier.cover_amount if child_tier else 0,
                'child_premium': child_tier.premium_amount if child_tier else 0,
                'extended_cover': extended_tier.cover_amount if extended_tier else 0,
                'extended_premium': extended_tier.premium_amount if extended_tier else 0,
                'spouses_allowed': plan.spouses_allowed,
                'children_allowed': plan.children_allowed,
                'extended_allowed': plan.extended_allowed,
                'waiting_period': waiting_period,
                'tiers': tier_data
            }
            
            plans_data.append(plan_data)
        
        # Add plans data to context as JSON for Alpine.js
        context['plans_json'] = json.dumps(plans_data)
        
        # Add LegacyGuide configuration
        context['legacyguide_enabled'] = True
        
        return context
    
    def post(self, request, *args, **kwargs):
        # Get selected plan ID from POST data
        plan_id = request.POST.get('plan_id')
        
        if not plan_id:
            messages.error(request, 'Please select a plan to continue.')
            return self.get(request, *args, **kwargs)
        
        try:
            # Get the selected plan
            plan = Plan.objects.get(id=plan_id, is_diy_visible=True, is_active=True)
            
            # Update application with plan details
            application = self.get_application(request)
            application.plan = plan
            application.save()
            
            # Save plan data to session
            form_data = request.session.get('diy_form_data', {})
            form_data['plan'] = {
                'id': plan.id,
                'name': plan.name
            }
            request.session['diy_form_data'] = form_data
            
            # Redirect to next step
            return redirect(self.get_success_url())
            
        except Plan.DoesNotExist:
            messages.error(request, 'The selected plan is not available.')
            return self.get(request, *args, **kwargs)
    
    def get_success_url(self):
        application = self.get_application(self.request)
        
        # Check if we should skip spouse step (if spouses_allowed is 0)
        if application.plan and application.plan.spouses_allowed == 0:
            return reverse('members:diy_dependents')
            
        return reverse('members:diy_spouse_information')


class DIYPaymentOptionsView(FormView, DIYApplicationMixin):
    """Step 5: Payment options form"""
    template_name = 'members/diy/step5_payment.html'
    form_class = DIYPaymentOptionsForm
    step_number = 5
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        form_data = self.request.session.get('diy_form_data', {})
        if self.request.method == 'GET' and form_data.get('payment'):
            kwargs['data'] = form_data['payment']
        return kwargs
    
    def form_valid(self, form):
        # Save form data to session
        form_data = self.request.session.get('diy_form_data', {})
        form_data['payment'] = form.cleaned_data
        self.request.session['diy_form_data'] = form_data
        
        # Update application with payment details
        application = self.get_application(self.request)
        
        # Update payment details
        application.payment_method = form.cleaned_data['payment_method']
        
        # Only update debit order details if payment method is debit order
        if application.payment_method == 'debit_order':
            application.bank_name = form.cleaned_data['bank_name']
            application.account_number = form.cleaned_data['account_number']
            application.account_type = form.cleaned_data['account_type']
            application.branch_code = form.cleaned_data['branch_code']
            application.account_holder_name = form.cleaned_data['account_holder_name']
            application.debit_day = form.cleaned_data['debit_day']
        
        application.marketing_consent = form.cleaned_data.get('marketing_consent', False)
        application.save()
        
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse('members:diy_review')


class DIYReviewView(FormView, DIYApplicationMixin):
    """Step 8: Review and submit application"""
    template_name = 'members/diy/step8_review.html'
    form_class = DIYApplicationConsentForm
    step_number = 8
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        application = self.get_application(self.request)
        
        try:
            applicant = application.applicant
            context['application'] = application
            context['applicant'] = applicant
            context['beneficiaries'] = application.beneficiaries.all()
            
            # Add plan information to context
            if application.plan:
                context['plan'] = application.plan
                
                # Check if terms and conditions are available
                context['has_terms_pdf'] = bool(application.plan.terms_pdf)
                context['has_terms_text'] = bool(application.plan.terms_text)
                
        except DIYApplicant.DoesNotExist:
            pass
            
        return context
    
    def form_valid(self, form):
        # Update application status to submitted
        application = self.get_application(self.request)
        application.status = 'submitted'
        application.submitted_at = timezone.now()
        application.marketing_consent = form.cleaned_data.get('marketing_consent', False)
        application.terms_accepted = form.cleaned_data.get('terms_accepted', False)
        application.terms_accepted_at = timezone.now() if application.terms_accepted else None
        application.save()
        
        # Send confirmation email
        self.send_confirmation_email(application)
        
        # Generate PDF certificate
        self.generate_certificate(application)
        
        return super().form_valid(form)
    
    def send_confirmation_email(self, application):
        """Send confirmation email to the applicant"""
        try:
            applicant = application.applicant
            subject = 'Your Policy Application Has Been Submitted'
            context = {
                'application': application,
                'applicant': applicant,
                'reference_number': application.reference_number
            }
            html_message = render_to_string('members/emails/application_confirmation.html', context)
            plain_message = strip_tags(html_message)
            from_email = settings.DEFAULT_FROM_EMAIL
            recipient_list = [applicant.email]
            
            send_mail(subject, plain_message, from_email, recipient_list, html_message=html_message)
            # Render email content
            text_content = render_to_string('emails/diy_application_confirmation.txt', context)
            html_content = render_to_string('emails/diy_application_confirmation.html', context)
            
            # Send email
            send_mail(
                subject=subject,
                message=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[applicant.email],
                html_message=html_content,
                fail_silently=False,
            )
            
            return True
        except Exception as e:
            # Log the error
            print(f"Error sending confirmation email: {e}")
            return False


class DIYSpouseInformationView(FormView, DIYApplicationMixin):
    """Step 3: Spouse information"""
    template_name = 'members/diy/step3_spouse.html'
    form_class = DIYBeneficiaryForm  # We'll reuse the beneficiary form for spouse
    step_number = 3
    
    def dispatch(self, request, *args, **kwargs):
        # Get the application
        application = self.get_application(request)
        
        # Check if we should skip this step (if spouses_allowed is 0)
        if application.plan and application.plan.spouses_allowed == 0:
            return redirect('members:diy_dependents')
            
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        application = self.get_application(self.request)
        
        # Add plan information to context
        if application.plan:
            context['plan'] = application.plan
            
        return context
    
    def form_valid(self, form):
        # Save spouse information
        application = self.get_application(self.request)
        
        # Update application
        application.has_spouse = True
        application.save()
        
        # Save form data to session
        form_data = self.request.session.get('diy_form_data', {})
        form_data['spouse'] = form.cleaned_data
        self.request.session['diy_form_data'] = form_data
        
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse('members:diy_dependents')


class DIYDependentsView(TemplateView, DIYApplicationMixin):
    """Step 4: Children and extended family members"""
    template_name = 'members/diy/step4_dependents.html'
    step_number = 4
    
    def dispatch(self, request, *args, **kwargs):
        # Get the application
        application = self.get_application(request)
        
        # Check if we should skip this step (if both children_allowed and extended_allowed are 0)
        if application.plan and application.plan.children_allowed == 0 and application.plan.extended_allowed == 0:
            return redirect('members:diy_beneficiaries')
            
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        application = self.get_application(self.request)
        
        # Add plan information to context
        if application.plan:
            context['plan'] = application.plan
            context['children_allowed'] = application.plan.children_allowed
            context['extended_allowed'] = application.plan.extended_allowed
            
        return context
    
    def post(self, request, *args, **kwargs):
        # Process children and extended family members
        application = self.get_application(request)
        
        # Get data from request
        data = json.loads(request.body) if request.content_type == 'application/json' else request.POST
        
        # Update application
        children_count = int(data.get('children_count', 0))
        extended_count = int(data.get('extended_count', 0))
        
        application.has_children = children_count > 0
        application.has_extended_family = extended_count > 0
        application.children_count = children_count
        application.extended_family_members = extended_count
        application.save()
        
        # Save dependents data to session
        form_data = request.session.get('diy_form_data', {})
        form_data['dependents'] = data
        request.session['diy_form_data'] = form_data
        
        return JsonResponse({'success': True, 'redirect_url': reverse('members:diy_beneficiaries')})


class DIYOTPVerificationView(TemplateView, DIYApplicationMixin):
    """Step 7: OTP verification"""
    template_name = 'members/diy/step7_otp.html'
    step_number = 7
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        application = self.get_application(self.request)
        
        # Generate OTP if not already generated
        if not application.otp_code or not application.otp_generated_at:
            application.generate_otp()
            
            # Send OTP to applicant's phone or email
            self.send_otp(application)
        
        return context
    
    def post(self, request, *args, **kwargs):
        application = self.get_application(request)
        
        # Get OTP from request
        otp_code = request.POST.get('otp_code')
        
        if not otp_code:
            messages.error(request, 'Please enter the OTP code.')
            return self.get(request, *args, **kwargs)
        
        # Verify OTP
        is_valid, message = application.verify_otp(otp_code)
        
        if not is_valid:
            messages.error(request, message)
            return self.get(request, *args, **kwargs)
        
        # OTP verified successfully
        messages.success(request, 'OTP verified successfully.')
        return redirect('members:diy_review')
    
    def send_otp(self, application):
        """Send OTP to applicant's phone or email"""
        try:
            applicant = application.applicant
            otp_code = application.otp_code
            
            # Send OTP via email
            subject = 'Your OTP Code for Policy Application'
            message = f'Your OTP code is: {otp_code}. This code will expire in 15 minutes.'
            from_email = settings.DEFAULT_FROM_EMAIL
            recipient_list = [applicant.email]
            
            send_mail(subject, message, from_email, recipient_list)
            
            # You could also implement SMS sending here if needed
            
            return True
        except Exception as e:
            # Log the error
            return False


class DIYConfirmationView(TemplateView, DIYApplicationMixin):
    """Step 9: Application confirmation"""
    template_name = 'members/diy/step9_confirmation.html'
    step_number = 9
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        application_id = self.kwargs.get('application_id')
        
        try:
            application = DIYApplication.objects.get(application_id=application_id)
            context['application'] = application
            context['applicant'] = application.applicant
            
            # Generate certificate if not already generated
            if not application.certificate_generated:
                self.generate_certificate(application)
        except DIYApplication.DoesNotExist:
            pass
            
        return context
    
    def generate_certificate(self, application):
        """Generate PDF certificate for the application"""
        try:
            # Generate certificate logic would go here
            # This would typically involve creating a PDF and storing it
            
            # For now, we'll just mark it as generated
            application.certificate_generated = True
            application.certificate_generated_at = timezone.now()
            application.save()
            
            return True
        except Exception as e:
            # Log the error
            return False


class DIYResumeApplicationView(RedirectView, DIYApplicationMixin):
    """Resume an application using a token"""
    
    def get_redirect_url(self, *args, **kwargs):
        token = kwargs.get('token')
        
        if not token:
            messages.error(self.request, 'Invalid resume token.')
            return reverse('members:diy_start')
        
        try:
            # Find application by token
            application = DIYApplication.objects.get(resume_token=token)
            
            # Check if token is expired
            if not application.can_resume():
                messages.error(self.request, 'Resume token has expired. Please start a new application.')
                return reverse('members:diy_start')
            
            # Store application ID in session
            self.request.session['diy_application_id'] = str(application.application_id)
            
            # Redirect to the appropriate step
            if application.current_step == 1:
                return reverse('members:diy_personal_details')
            elif application.current_step == 2:
                return reverse('members:diy_policy_selection')
            elif application.current_step == 3:
                return reverse('members:diy_spouse_information')
            elif application.current_step == 4:
                return reverse('members:diy_dependents')
            elif application.current_step == 5:
                return reverse('members:diy_beneficiaries')
            elif application.current_step == 6:
                return reverse('members:diy_payment_options')
            elif application.current_step == 7:
                return reverse('members:diy_otp_verification')
            elif application.current_step == 8:
                return reverse('members:diy_review')
            else:
                return reverse('members:diy_personal_details')
                
        except DIYApplication.DoesNotExist:
            messages.error(self.request, 'Application not found.')
            return reverse('members:diy_start')


class DIYSaveForLaterView(View, DIYApplicationMixin):
    """Save application for later completion"""
    
    def post(self, request, *args, **kwargs):
        application = self.get_application(request)
        
        # Update application status
        application.status = 'incomplete'
        application.last_activity_at = timezone.now()
        
        # Save current step
        current_step = request.POST.get('current_step')
        if current_step and current_step.isdigit():
            application.current_step = int(current_step)
        
        # Generate resume token
        token = application.generate_resume_token()
        
        # Get resume URL
        resume_url = request.build_absolute_uri(reverse('members:diy_resume', kwargs={'token': token}))
        
        # Save application
        application.save()
        
        # Send resume link to applicant's email
        try:
            applicant = application.applicant
            subject = 'Resume Your Policy Application'
            message = f'You can resume your application by clicking this link: {resume_url}\n\nThis link will expire in 7 days.'
            from_email = settings.DEFAULT_FROM_EMAIL
            recipient_list = [applicant.email]
            
            send_mail(subject, message, from_email, recipient_list)
        except Exception as e:
            # Log the error but continue
            pass
        
        return JsonResponse({
            'success': True,
            'message': 'Application saved successfully. A resume link has been sent to your email.',
            'resume_url': resume_url
        })


class GenerateOTPView(View, DIYApplicationMixin):
    """API endpoint to generate OTP"""
    
    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def post(self, request, *args, **kwargs):
        application = self.get_application(request)
        
        # Generate new OTP
        otp = application.generate_otp()
        
        # Send OTP to applicant's phone or email
        try:
            applicant = application.applicant
            subject = 'Your OTP Code for Policy Application'
            message = f'Your OTP code is: {otp}. This code will expire in 15 minutes.'
            from_email = settings.DEFAULT_FROM_EMAIL
            recipient_list = [applicant.email]
            
            send_mail(subject, message, from_email, recipient_list)
            
            return JsonResponse({
                'success': True,
                'message': 'OTP sent successfully.'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)


class VerifyOTPView(View, DIYApplicationMixin):
    """API endpoint to verify OTP"""
    
    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def post(self, request, *args, **kwargs):
        application = self.get_application(request)
        
        # Get OTP from request
        data = json.loads(request.body) if request.content_type == 'application/json' else request.POST
        otp_code = data.get('otp_code')
        
        if not otp_code:
            return JsonResponse({
                'success': False,
                'error': 'OTP code is required.'
            }, status=400)
        
        # Verify OTP
        is_valid, message = application.verify_otp(otp_code)
        
        return JsonResponse({
            'success': is_valid,
            'message': message
        })


class GeneratePDFView(View, DIYApplicationMixin):
    """API endpoint to generate PDF certificate"""
    
    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def post(self, request, *args, **kwargs):
        application = self.get_application(request)
        
        # Generate PDF certificate
        try:
            # PDF generation logic would go here
            # For now, we'll just mark it as generated
            
            application.certificate_generated = True
            application.certificate_generated_at = timezone.now()
            application.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Certificate generated successfully.'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)


class DIYSuccessView(TemplateView, DIYApplicationMixin):
    """Application submitted successfully (legacy view - replaced by DIYConfirmationView)"""
    template_name = 'members/diy/step7_success.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        application_id = self.kwargs.get('application_id')
        
        try:
            application = DIYApplication.objects.get(application_id=application_id)
            context['application'] = application
            context['applicant'] = application.applicant
        except DIYApplication.DoesNotExist:
            pass
            
        return context


# API Views for AJAX requests

class ProcessIDDocumentView(View):
    """API endpoint to process ID document uploads and extract information using OCR"""
    
    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def post(self, request, *args, **kwargs):
        try:
            # Get image data from request
            if 'image' not in request.FILES:
                return JsonResponse({'error': 'No image file provided'}, status=400)
            
            # Read the image file
            image_file = request.FILES['image']
            image_data = base64.b64encode(image_file.read()).decode('utf-8')
            
            # Process the ID document
            result = process_id_document(image_data)
            
            if 'error' in result and result['error']:
                return JsonResponse({'error': result['error']}, status=400)
            
            # Return the extracted information
            return JsonResponse({
                'success': True,
                'data': {
                    'id_number': result.get('id_number'),
                    'full_name': result.get('full_name'),
                    'date_of_birth': result.get('date_of_birth'),
                    'gender': result.get('gender')
                }
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


class PlanChatView(View):
    """API endpoint to get answers to questions about plans using AI"""
    
    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def post(self, request, *args, **kwargs):
        try:
            # Parse JSON data
            data = json.loads(request.body)
            plan_id = data.get('plan_id')
            question = data.get('question')
            
            # Validate input
            if not plan_id or not question:
                return JsonResponse({'error': 'Plan ID and question are required'}, status=400)
            
            # Get plan and its tiers
            try:
                plan = Plan.objects.get(id=plan_id)
                tiers = PlanTier.objects.filter(plan=plan)
            except Plan.DoesNotExist:
                return JsonResponse({'error': 'Plan not found'}, status=404)
            
            # Get answer using the plan_chat utility
            answer = get_plan_answer(question, plan, tiers)
            
            return JsonResponse({
                'success': True,
                'answer': answer
            })
            
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON data'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
class CalculatePremiumView(View):
    """API endpoint to calculate premium based on cover amount"""
    
    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
            cover_amount = float(data.get('cover_amount', 0))
            
            if cover_amount <= 0:
                return JsonResponse({'error': 'Invalid cover amount'}, status=400)
            
            # Simple premium calculation (1% of cover amount)
            premium = cover_amount * 0.01
            
            # Apply discounts for higher cover amounts
            if cover_amount > 50000:
                premium *= 0.9  # 10% discount for > R50k
            elif cover_amount > 30000:
                premium *= 0.95  # 5% discount for > R30k
            
            # Ensure minimum premium of R50
            premium = max(50, round(premium, 2))
            
            return JsonResponse({
                'success': True,
                'premium': premium,
                'formatted_premium': f'R{premium:,.2f}'
            })
            
        except (ValueError, TypeError):
            return JsonResponse({'error': 'Invalid input'}, status=400)


class ValidateIDView(View):
    """API endpoint to validate South African ID number"""
    
    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
            id_number = data.get('id_number', '').replace(' ', '')
            
            # Basic validation for length and digits only
            if not re.match(r'^\d{13}$', id_number):
                return JsonResponse({
                    'valid': False,
                    'error': 'ID number must be 13 digits long'
                })
            
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
                    return JsonResponse({
                        'valid': False,
                        'error': 'Invalid date of birth in ID number'
                    })
                
                # Calculate age
                today = timezone.now().date()
                age = today.year - date_of_birth.year - ((today.month, today.day) < (date_of_birth.month, date_of_birth.day))
                
                if age < 18:
                    return JsonResponse({
                        'valid': False,
                        'error': 'You must be at least 18 years old to apply'
                    })
                
                if age > 100:
                    return JsonResponse({
                        'valid': False,
                        'error': 'Please contact our support for applicants over 100 years old'
                    })
                
                # Get gender from ID number (7th digit, 0-4 = female, 5-9 = male)
                gender_digit = int(id_number[6])
                gender = 'female' if gender_digit < 5 else 'male'
                
                return JsonResponse({
                    'valid': True,
                    'date_of_birth': date_of_birth.isoformat(),
                    'age': age,
                    'gender': gender
                })
                
            except (ValueError, TypeError) as e:
                return JsonResponse({
                    'valid': False,
                    'error': 'Invalid date of birth in ID number'
                })
            
        except Exception as e:
            return JsonResponse({
                'valid': False,
                'error': 'An error occurred while validating the ID number'
            }, status=500)


class UploadDocumentView(View):
    """API endpoint to upload documents"""
    
    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def post(self, request, *args, **kwargs):
        try:
            application_id = request.session.get('diy_application_id')
            if not application_id:
                return JsonResponse({'error': 'Session expired'}, status=400)
            
            application = DIYApplication.objects.get(application_id=application_id)
            
            if 'document' not in request.FILES:
                return JsonResponse({'error': 'No file uploaded'}, status=400)
            
            document = request.FILES['document']
            document_type = request.POST.get('document_type', 'other')
            
            # Validate file type
            allowed_types = ['application/pdf', 'image/jpeg', 'image/png', 'image/gif']
            if document.content_type not in allowed_types:
                return JsonResponse({
                    'error': 'Invalid file type. Please upload a PDF, JPEG, or PNG file.'
                }, status=400)
            
            # Validate file size (max 5MB)
            if document.size > 5 * 1024 * 1024:  # 5MB
                return JsonResponse({
                    'error': 'File is too large. Maximum size is 5MB.'
                }, status=400)
            
            # Save document
            doc = DIYApplicationDocument(
                application=application,
                document_type=document_type,
                file=document,
                original_filename=document.name,
                file_size=document.size,
                file_type=document.content_type,
            )
            doc.save()
            
            return JsonResponse({
                'success': True,
                'document': {
                    'id': doc.id,
                    'filename': doc.original_filename,
                    'url': doc.file.url,
                    'type': doc.document_type,
                    'size': doc.file_size,
                    'uploaded_at': doc.uploaded_at.isoformat(),
                }
            })
            
        except Exception as e:
            return JsonResponse({
                'error': str(e)
            }, status=500)


class DeleteDocumentView(View):
    """API endpoint to delete a document"""
    
    def post(self, request, *args, **kwargs):
        try:
            document_id = request.POST.get('document_id')
            if not document_id:
                return JsonResponse({'error': 'Document ID is required'}, status=400)
            
            application_id = request.session.get('diy_application_id')
            if not application_id:
                return JsonResponse({'error': 'Session expired'}, status=400)
            
            # Verify document belongs to the current application
            document = DIYApplicationDocument.objects.get(
                id=document_id,
                application__application_id=application_id
            )
            
            # Delete the file and record
            document.file.delete()
            document.delete()
            
            return JsonResponse({'success': True})
            
        except DIYApplicationDocument.DoesNotExist:
            return JsonResponse({'error': 'Document not found'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


class CheckApplicationStatusView(View):
    """API endpoint to check application status"""
    
    def get(self, request, *args, **kwargs):
        reference_number = request.GET.get('reference_number')
        id_number = request.GET.get('id_number')
        
        if not reference_number or not id_number:
            return JsonResponse({
                'error': 'Reference number and ID number are required'
            }, status=400)
        
        try:
            application = DIYApplication.objects.get(
                reference_number=reference_number,
                applicant__id_number=id_number
            )
            
            return JsonResponse({
                'status': application.get_status_display(),
                'submitted_at': application.submitted_at.isoformat() if application.submitted_at else None,
                'policy_type': application.get_policy_type_display(),
                'cover_amount': application.cover_amount,
                'monthly_premium': application.monthly_premium,
            })
            
        except DIYApplication.DoesNotExist:
            return JsonResponse({
                'error': 'No application found with the provided details'
            }, status=404)
        except Exception as e:
            return JsonResponse({
                'error': 'An error occurred while checking the application status'
            }, status=500)


class DownloadCertificateView(View, DIYApplicationMixin):
    """View to download the policy certificate PDF"""
    
    def get(self, request, application_id, *args, **kwargs):
        try:
            # Get the application
            application = get_object_or_404(DIYApplication, application_id=application_id)
            
            # Check if certificate exists
            if not application.certificate_generated or not application.certificate_file:
                # Generate certificate if it doesn't exist
                self.generate_certificate(application)
                
                if not application.certificate_file:
                    messages.error(request, "Certificate could not be generated. Please try again later.")
                    return redirect('members:diy_confirmation', application_id=application_id)
            
            # Increment download count
            application.certificate_download_count += 1
            application.save(update_fields=['certificate_download_count'])
            
            # Serve the file
            response = redirect(application.certificate_file.url)
            return response
            
        except DIYApplication.DoesNotExist:
            messages.error(request, "Application not found.")
            return redirect('members:diy_start')
        except Exception as e:
            messages.error(request, f"An error occurred: {str(e)}")
            return redirect('members:diy_confirmation', application_id=application_id)
    
    def generate_certificate(self, application):
        """Generate PDF certificate for the application"""
        try:
            # This would typically involve creating a PDF using a library like ReportLab or WeasyPrint
            # For now, we'll just mark it as generated with a placeholder
            
            from django.core.files.base import ContentFile
            import io
            from reportlab.pdfgen import canvas
            from reportlab.lib.pagesizes import letter
            
            # Create a PDF in memory
            buffer = io.BytesIO()
            p = canvas.Canvas(buffer, pagesize=letter)
            
            # Add content to the PDF
            p.setFont("Helvetica-Bold", 16)
            p.drawCentredString(300, 750, "Policy Certificate")
            
            p.setFont("Helvetica", 12)
            p.drawString(100, 700, f"Reference Number: {application.reference_number}")
            
            # Add applicant details if available
            try:
                applicant = application.applicant
                p.drawString(100, 680, f"Policy Holder: {applicant.first_name} {applicant.last_name}")
                p.drawString(100, 660, f"ID Number: {applicant.id_number}")
            except DIYApplicant.DoesNotExist:
                p.drawString(100, 680, "Policy Holder: Information not available")
            
            if application.plan:
                p.drawString(100, 640, f"Plan: {application.plan.name}")
                p.drawString(100, 620, f"Cover Amount: R{application.plan.main_cover}")
                p.drawString(100, 600, f"Monthly Premium: R{application.monthly_premium}")
            
            p.drawString(100, 580, f"Commencement Date: {application.submitted_at.strftime('%d %B %Y') if application.submitted_at else 'Pending'}")
            
            p.setFont("Helvetica-Bold", 14)
            p.drawString(100, 520, "Covered Members:")
            
            y_position = 500
            p.setFont("Helvetica", 12)
            
            # Add main member
            try:
                p.drawString(120, y_position, f"Main Member: {application.applicant.first_name} {application.applicant.last_name}")
                y_position -= 20
            except DIYApplicant.DoesNotExist:
                pass
            
            # Add spouse if applicable
            if application.has_spouse:
                try:
                    spouse = application.dependents.filter(relationship='spouse').first()
                    if spouse:
                        p.drawString(120, y_position, f"Spouse: {spouse.first_name} {spouse.last_name}")
                        y_position -= 20
                except Exception:
                    pass
            
            # Add dependents if applicable
            children = application.dependents.filter(relationship='child')
            if children.exists():
                for child in children:
                    p.drawString(120, y_position, f"Child: {child.first_name} {child.last_name}")
                    y_position -= 20
            
            extended = application.dependents.filter(relationship='extended')
            if extended.exists():
                for member in extended:
                    p.drawString(120, y_position, f"Extended Member: {member.first_name} {member.last_name}")
                    y_position -= 20
            
            # Add footer
            p.setFont("Helvetica-Italic", 10)
            p.drawString(100, 100, "This certificate is valid only if premiums are paid up to date.")
            p.drawString(100, 80, f"Generated on {timezone.now().strftime('%d %B %Y at %H:%M')}")
            
            # Save the PDF
            p.showPage()
            p.save()
            
            # Get the PDF content
            buffer.seek(0)
            pdf_content = buffer.getvalue()
            
            # Save to the application
            file_name = f"certificate_{application.reference_number}.pdf"
            application.certificate_file.save(file_name, ContentFile(pdf_content), save=False)
            application.certificate_generated = True
            application.certificate_generated_at = timezone.now()
            application.save(update_fields=['certificate_file', 'certificate_generated', 'certificate_generated_at'])
            
            return True
        except Exception as e:
            print(f"Error generating certificate: {str(e)}")
            return False


class VerifyCertificateView(TemplateView):
    """View to verify a policy certificate"""
    template_name = 'members/diy/verify_certificate.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        application_id = self.kwargs.get('application_id')
        
        try:
            application = get_object_or_404(DIYApplication, application_id=application_id)
            
            # Check if application is valid
            is_valid = application.status in ['submitted', 'approved', 'active']
            
            context.update({
                'application': application,
                'is_valid': is_valid,
                'verification_date': timezone.now(),
                'plan': application.plan,
            })
            
            # Add applicant details if available
            try:
                context['applicant'] = application.applicant
            except DIYApplicant.DoesNotExist:
                context['applicant'] = None
            
        except DIYApplication.DoesNotExist:
            context['is_valid'] = False
            context['error'] = "Certificate not found"
        
        return context


class DIYChatView(TemplateView, DIYApplicationMixin):
    """View for AI-powered chat about the policy"""
    template_name = 'members/diy/plan_chat.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        application_id = self.kwargs.get('application_id')
        
        try:
            # Get the application
            application = get_object_or_404(DIYApplication, application_id=application_id)
            context['application'] = application
            
            # Get the plan
            if application.plan:
                context['plan'] = application.plan
            else:
                messages.error(self.request, "No plan selected for this application.")
                return context
            
            # Get applicant details
            try:
                context['applicant'] = application.applicant
            except DIYApplicant.DoesNotExist:
                context['applicant'] = None
            
            # Get plan tiers for reference
            context['plan_tiers'] = application.plan.plan_tiers.all()
            
        except DIYApplication.DoesNotExist:
            messages.error(self.request, "Application not found.")
            
        return context
