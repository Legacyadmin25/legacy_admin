import json
import uuid
import base64
import logging
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
from .utils.ocr_processor import process_id_document

# Inline implementation of get_plan_answer to avoid import issues
logger = logging.getLogger(__name__)

def get_plan_answer(question, plan, tiers=None):
    """
    Get an answer to a question about a plan using simplified logic.
    This is an inline version to avoid import issues with null bytes.
    
    Args:
        question (str): The user's question
        plan (Plan): The plan object
        tiers (list): Optional list of tier objects
        
    Returns:
        str: The answer
    """
    try:
        # Simple rule-based approach
        question = question.lower()
        
        # Define some common questions and answers
        if any(keyword in question for keyword in ['cover', 'payout', 'benefit']):
            return f"The main cover amount for this plan is R{plan.main_cover}. This explanation is for informational purposes only and does not constitute financial advice."
        
        elif any(keyword in question for keyword in ['premium', 'cost', 'pay', 'price']):
            return f"The monthly premium for this plan is R{plan.premium}. This explanation is for informational purposes only and does not constitute financial advice."
        
        elif any(keyword in question for keyword in ['spouse', 'husband', 'wife', 'partner']):
            if plan.spouses_allowed > 0:
                spouse_tier = next((t for t in tiers if t.user_type == 'Spouse'), None) if tiers else None
                if spouse_tier:
                    return f"This plan covers {plan.spouses_allowed} spouse(s) with a cover amount of R{spouse_tier.cover}. This explanation is for informational purposes only and does not constitute financial advice."
                return f"This plan allows for {plan.spouses_allowed} spouse(s). This explanation is for informational purposes only and does not constitute financial advice."
            return "This plan does not include spouse coverage. This explanation is for informational purposes only and does not constitute financial advice."
        
        elif any(keyword in question for keyword in ['child', 'children', 'kid']):
            if plan.children_allowed > 0:
                child_tier = next((t for t in tiers if t.user_type == 'Child'), None) if tiers else None
                if child_tier:
                    return f"This plan covers up to {plan.children_allowed} children with a cover amount of R{child_tier.cover}. This explanation is for informational purposes only and does not constitute financial advice."
                return f"This plan allows for up to {plan.children_allowed} children. This explanation is for informational purposes only and does not constitute financial advice."
            return "This plan does not include children coverage. This explanation is for informational purposes only and does not constitute financial advice."
        
        # Default response for unknown questions
        return f"I don't have specific information about that in the plan details. Please contact customer support for more information about {plan.name}. This explanation is for informational purposes only and does not constitute financial advice."
    except Exception as e:
        logger.error(f"Error getting plan answer: {str(e)}")
        return "I'm sorry, I couldn't process your question. Please try again or contact customer support."

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
            # This should not happen, but just in case
            messages.error(self.request, 'There was an error with your application. Please try again.')
            return redirect('members:diy_personal_details')
        
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse('members:diy_plan_selection')


class DIYPolicySelectionView(DIYApplicationMixin, FormView):
    """
    Step 3: Policy selection form
    """
    template_name = 'members/diy/step3_policy_selection.html'
    form_class = DIYPolicyDetailsForm
    step_number = 3

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        application = self.get_application(self.request)
        kwargs['instance'] = application
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['plans'] = Plan.objects.filter(is_active=True)
        return context

    def form_valid(self, form):
        try:
            with transaction.atomic():
                application = form.save(commit=False)
                application.step = self.step_number
                application.save()
                self.request.session['diy_application_id'] = str(application.id)
        except Exception as e:
            logger.error(f"Error saving policy selection: {str(e)}")
            messages.error(self.request, 'There was an error saving your policy selection. Please try again.')
            return redirect('members:diy_policy_selection')
        
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse('members:diy_spouse_information')


class DIYSpouseInformationView(DIYApplicationMixin, FormView):
    """
    Step 4: Spouse information form
    """
    template_name = 'members/diy/step4_spouse.html'
    form_class = None  # We'll use a formset for spouse information
    step_number = 4

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        application = self.get_application(self.request)
        
        # Add spouse form to context if not already present
        if 'spouse_form' not in context:
            SpouseFormSet = self.get_spouse_formset()
            context['spouse_form'] = SpouseFormSet(
                instance=application,
                prefix='spouse'
            )
            
        return context

    def get_spouse_formset(self):
        """Return the appropriate formset for spouse information"""
        from django.forms import inlineformset_factory
        from .models_diy import DIYApplicant, Relationship
        from .forms_diy import DIYApplicantForm
        
        return inlineformset_factory(
            DIYApplication, 
            DIYApplicant,
            form=DIYApplicantForm,
            extra=1,
            max_num=1,
            can_delete=False,
            fk_name='application',
            fields=('first_name', 'last_name', 'id_number', 'date_of_birth', 'gender'),
        )

    def post(self, request, *args, **kwargs):
        application = self.get_application(request)
        SpouseFormSet = self.get_spouse_formset()
        formset = SpouseFormSet(
            request.POST,
            request.FILES,
            instance=application,
            prefix='spouse'
        )

        if formset.is_valid():
            try:
                with transaction.atomic():
                    # Delete existing spouse records
                    application.spouses.all().delete()
                    
                    # Save new spouse information
                    instances = formset.save(commit=False)
                    for instance in instances:
                        instance.relationship = Relationship.SPOUSE
                        instance.save()
                    
                    # Update application step
                    application.step = self.step_number
                    application.save()
                    
                    messages.success(request, 'Spouse information saved successfully.')
                    return redirect(self.get_success_url())
                    
            except Exception as e:
                logger.error(f"Error saving spouse information: {str(e)}")
                messages.error(request, 'There was an error saving spouse information. Please try again.')
        
        # If we get here, there was an error
        return self.render_to_response(self.get_context_data(spouse_form=formset))
    
    def get_success_url(self):
        return reverse('members:diy_dependents')


class DIYDependentsView(DIYApplicationMixin, TemplateView):
    """
    Step 5: Dependents information form
    """
    template_name = 'members/diy/step5_dependents.html'
    step_number = 5

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        application = self.get_application(self.request)
        
        # Add dependents formset to context if not already present
        if 'dependents_formset' not in context:
            DependentsFormSet = self.get_dependents_formset()
            context['dependents_formset'] = DependentsFormSet(
                instance=application,
                prefix='dependents',
                queryset=application.dependents.all()
            )
            
        return context

    def get_dependents_formset(self):
        """Return the appropriate formset for dependents"""
        from django.forms import inlineformset_factory
        from .models_diy import DIYApplicant, Relationship
        from .forms_diy import DIYApplicantForm
        
        return inlineformset_factory(
            DIYApplication, 
            DIYApplicant,
            form=DIYApplicantForm,
            extra=1,
            can_delete=True,
            fk_name='application',
            fields=('first_name', 'last_name', 'id_number', 'date_of_birth', 'gender', 'relationship'),
        )

    def post(self, request, *args, **kwargs):
        application = self.get_application(request)
        DependentsFormSet = self.get_dependents_formset()
        formset = DependentsFormSet(
            request.POST,
            request.FILES,
            instance=application,
            prefix='dependents',
            queryset=application.dependents.all()
        )

        if formset.is_valid():
            try:
                with transaction.atomic():
                    # Save dependents
                    instances = formset.save(commit=False)
                    for instance in instances:
                        if not hasattr(instance, 'relationship') or instance.relationship == '':
                            instance.relationship = Relationship.CHILD
                        instance.save()
                    
                    # Delete any marked for deletion
                    for obj in formset.deleted_objects:
                        obj.delete()
                    
                    # Update application step
                    application.step = self.step_number
                    application.save()
                    
                    messages.success(request, 'Dependents information saved successfully.')
                    return redirect(self.get_success_url())
                    
            except Exception as e:
                logger.error(f"Error saving dependents information: {str(e)}")
                messages.error(request, 'There was an error saving dependents information. Please try again.')
        
        # If we get here, there was an error
        return self.render_to_response(self.get_context_data(dependents_formset=formset))
    
    def get_success_url(self):
        return reverse('members:diy_beneficiaries')


class DIYBeneficiariesView(DIYApplicationMixin, TemplateView):
    """
    Step 6: Beneficiaries information form
    """
    template_name = 'members/diy/step6_beneficiaries.html'
    step_number = 6

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        application = self.get_application(self.request)
        
        # Add beneficiaries formset to context if not already present
        if 'beneficiaries_formset' not in context:
            BeneficiariesFormSet = self.get_beneficiaries_formset()
            context['beneficiaries_formset'] = BeneficiariesFormSet(
                instance=application,
                prefix='beneficiaries',
                queryset=application.beneficiaries.all()
            )
            
        return context

    def get_beneficiaries_formset(self):
        """Return the appropriate formset for beneficiaries"""
        from django.forms import inlineformset_factory
        from .models_diy import DIYBeneficiary
        from .forms_diy import DIYBeneficiaryForm
        
        return inlineformset_factory(
            DIYApplication, 
            DIYBeneficiary,
            form=DIYBeneficiaryForm,
            extra=1,
            can_delete=True,
            fields=('first_name', 'last_name', 'id_number', 'relationship', 'percentage'),
        )

    def post(self, request, *args, **kwargs):
        application = self.get_application(request)
        BeneficiariesFormSet = self.get_beneficiaries_formset()
        formset = BeneficiariesFormSet(
            request.POST,
            instance=application,
            prefix='beneficiaries',
            queryset=application.beneficiaries.all()
        )

        if formset.is_valid():
            try:
                with transaction.atomic():
                    # Save beneficiaries
                    instances = formset.save(commit=False)
                    for instance in instances:
                        instance.save()
                    
                    # Delete any marked for deletion
                    for obj in formset.deleted_objects:
                        obj.delete()
                    
                    # Update application step
                    application.step = self.step_number
                    application.save()
                    
                    # Validate total percentage
                    total_percentage = sum(b.percentage for b in application.beneficiaries.all())
                    if total_percentage != 100:
                        messages.warning(
                            request, 
                            f'Total beneficiary percentage is {total_percentage}%. It should be 100%. Please adjust the percentages.'
                        )
                        return self.render_to_response(self.get_context_data(beneficiaries_formset=formset))
                    
                    messages.success(request, 'Beneficiaries information saved successfully.')
                    return redirect(self.get_success_url())
                    
            except Exception as e:
                logger.error(f"Error saving beneficiaries information: {str(e)}")
                messages.error(request, 'There was an error saving beneficiaries information. Please try again.')
        
        # If we get here, there was an error
        return self.render_to_response(self.get_context_data(beneficiaries_formset=formset))
    
    def get_success_url(self):
        return reverse('members:diy_payment_options')


class DIYPaymentOptionsView(DIYApplicationMixin, FormView):
    """
    Step 7: Payment options form
    """
    template_name = 'members/diy/step7_payment_options.html'
    form_class = DIYPaymentOptionsForm
    step_number = 7

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        application = self.get_application(self.request)
        kwargs['instance'] = application
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        application = self.get_application(self.request)
        
        # Add payment options to context
        context['payment_methods'] = [
            ('bank_transfer', 'Bank Transfer'),
            ('debit_order', 'Debit Order'),
            ('credit_card', 'Credit Card'),
        ]
        
        # Add bank accounts if available
        if hasattr(settings, 'BANK_ACCOUNTS'):
            context['bank_accounts'] = settings.BANK_ACCOUNTS
            
        return context

    def form_valid(self, form):
        try:
            with transaction.atomic():
                application = form.save(commit=False)
                application.step = self.step_number
                
                # If payment method is debit order or credit card, generate a payment reference
                if application.payment_method in ['debit_order', 'credit_card']:
                    application.payment_reference = f"DIY-{application.id.hex[:8].upper()}"
                
                application.save()
                self.request.session['diy_application_id'] = str(application.id)
                
                messages.success(self.request, 'Payment information saved successfully.')
                return redirect(self.get_success_url())
                
        except Exception as e:
            logger.error(f"Error saving payment information: {str(e)}")
            messages.error(self.request, 'There was an error saving your payment information. Please try again.')
            return redirect('members:diy_payment_options')
    
    def get_success_url(self):
        return reverse('members:diy_otp_verification')


class DIYOTPVerificationView(DIYApplicationMixin, View):
    """
    Step 8: OTP Verification
    """
    template_name = 'members/diy/step8_otp_verification.html'
    step_number = 8
    
    def get(self, request, *args, **kwargs):
        application = self.get_application(request)
        
        # If OTP is already verified, redirect to next step
        if application.otp_verified:
            return redirect('members:diy_review')
            
        # Generate and send OTP if not already sent
        if not application.otp_sent_at:
            self._send_otp(application)
            
        return render(request, self.template_name, self.get_context_data())
    
    def post(self, request, *args, **kwargs):
        application = self.get_application(request)
        otp_entered = request.POST.get('otp', '').strip()
        
        # Check if OTP is valid
        if self._verify_otp(application, otp_entered):
            try:
                with transaction.atomic():
                    application.otp_verified = True
                    application.step = self.step_number
                    application.save()
                    
                    messages.success(request, 'OTP verified successfully.')
                    return redirect('members:diy_review')
                    
            except Exception as e:
                logger.error(f"Error verifying OTP: {str(e)}")
                messages.error(request, 'There was an error verifying your OTP. Please try again.')
        else:
            messages.error(request, 'Invalid OTP. Please try again.')
            
        return render(request, self.template_name, self.get_context_data())
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        application = self.get_application(self.request)
        
        # Add OTP details to context
        context['otp_sent'] = bool(application.otp_sent_at)
        context['otp_expires_in'] = self._get_otp_expiry(application)
        
        # Add resend OTP URL
        context['resend_otp_url'] = reverse('members:diy_resend_otp')
        
        return context
    
    def _send_otp(self, application):
        """Generate and send OTP to the user"""
        try:
            # Generate a 6-digit OTP
            import random
            otp = ''.join([str(random.randint(0, 9)) for _ in range(6)])
            
            # In a real application, you would send this OTP via SMS or email
            # For now, we'll just log it and store it in the database
            logger.info(f"OTP for application {application.id}: {otp}")
            
            # Store OTP details
            application.otp = otp
            application.otp_sent_at = timezone.now()
            application.otp_verified = False
            application.save()
            
            return True
            
        except Exception as e:
            logger.error(f"Error sending OTP: {str(e)}")
            return False
    
    def _verify_otp(self, application, otp_entered):
        """Verify the entered OTP"""
        try:
            # Check if OTP exists and is not expired (valid for 10 minutes)
            if not application.otp_sent_at:
                return False
                
            expiry_time = application.otp_sent_at + timedelta(minutes=10)
            if timezone.now() > expiry_time:
                return False
                
            # Check if OTP matches
            return application.otp == otp_entered
            
        except Exception as e:
            logger.error(f"Error verifying OTP: {str(e)}")
            return False
    
    def _get_otp_expiry(self, application):
        """Get remaining OTP expiry time in seconds"""
        if not application.otp_sent_at:
            return 0
            
        expiry_time = application.otp_sent_at + timedelta(minutes=10)
        remaining = (expiry_time - timezone.now()).total_seconds()
        return max(0, int(remaining))


class DIYReviewView(DIYApplicationMixin, TemplateView):
    """
    Step 9: Review application before submission
    """
    template_name = 'members/diy/step9_review.html'
    step_number = 9
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        application = self.get_application(self.request)
        
        # Add application details to context
        context['application'] = application
        context['applicant'] = application.applicants.first()  # Primary applicant
        context['spouse'] = application.spouses.first()
        context['dependents'] = application.dependents.all()
        context['beneficiaries'] = application.beneficiaries.all()
        
        # Add payment details
        context['payment_details'] = self._get_payment_details(application)
        
        # Add documents if any
        context['documents'] = application.documents.all()
        
        # Add edit URLs
        context['edit_urls'] = {
            'personal': reverse('members:diy_personal_details'),
            'policy': reverse('members:diy_policy_selection'),
            'spouse': reverse('members:diy_spouse_information'),
            'dependents': reverse('members:diy_dependents'),
            'beneficiaries': reverse('members:diy_beneficiaries'),
            'payment': reverse('members:diy_payment_options'),
        }
        
        return context
    
    def post(self, request, *args, **kwargs):
        application = self.get_application(request)
        
        try:
            with transaction.atomic():
                # Update application status to submitted
                application.status = 'submitted'
                application.submitted_at = timezone.now()
                application.step = self.step_number
                application.save()
                
                # In a real application, you would process the payment here
                # and send confirmation emails, etc.
                
                # Clear the session
                if 'diy_application_id' in request.session:
                    del request.session['diy_application_id']
                
                messages.success(request, 'Your application has been submitted successfully!')
                return redirect('members:diy_confirmation', application_id=application.id)
                
        except Exception as e:
            logger.error(f"Error submitting application: {str(e)}")
            messages.error(request, 'There was an error submitting your application. Please try again.')
            return redirect('members:diy_review')
    
    def _get_payment_details(self, application):
        """Get payment details for display in the review page"""
        details = {
            'method': dict(application.PAYMENT_METHOD_CHOICES).get(application.payment_method, 'N/A'),
            'amount': application.premium_amount,
            'frequency': application.get_payment_frequency_display(),
            'reference': application.payment_reference or 'N/A',
        }
        
        # Add bank details if payment method is bank transfer
        if application.payment_method == 'bank_transfer' and hasattr(settings, 'BANK_ACCOUNTS'):
            details['bank_accounts'] = settings.BANK_ACCOUNTS
            
        return details


class DIYConfirmationView(TemplateView):
    """
    Application submission confirmation page
    """
    template_name = 'members/diy/confirmation.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        application_id = self.kwargs.get('application_id')
        
        try:
            application = DIYApplication.objects.get(
                id=application_id,
                status='submitted'
            )
            context['application'] = application
            
            # Add any additional context needed for the confirmation page
            context['confirmation_number'] = f"CONF-{application.id.hex[:8].upper()}"
            
            # In a real application, you might want to include:
            # - Payment confirmation details
            # - Next steps
            # - Contact information for support
            
        except DIYApplication.DoesNotExist:
            raise Http404("Application not found or not submitted")
            
        return context

    def get(self, request, *args, **kwargs):
        # Clear any existing session data
        if 'diy_application_id' in request.session:
            del request.session['diy_application_id']
            
        return super().get(request, *args, **kwargs)
