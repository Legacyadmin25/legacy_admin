"""
Public Enrollment Views - Self-service policy application workflow
Separate from admin/agent views with different flows and permissions
"""

import json
import logging
from datetime import timedelta, date
from decimal import Decimal, InvalidOperation
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.views.generic import FormView, TemplateView
from django.http import HttpResponseForbidden, JsonResponse, HttpResponseBadRequest
from django.contrib import messages
from django.utils import timezone
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.urls import reverse
from django.db import transaction

from members.models_public_enrollment import (
    EnrollmentLink, PublicApplication, EnrollmentOTPVerification, POPIAConsent,
    ApplicationAnswer, EnrollmentQuestionBank
)
from members.forms_public_enrollment import (
    PersonalDetailsPublicForm, AddressPublicForm, PlanSelectionPublicForm,
    PaymentDetailsPublicForm, ConditionalQuestionForm, POPIAConsentForm,
    OTPVerificationForm, OTPResendForm
)
from schemes.models import Scheme, Plan
from branches.models import Branch
from settings_app.models import Agent
from members.communications.sms_sender import send_otp_sms, send_bulk_sms

logger = logging.getLogger(__name__)


def mask_phone_number(phone_number):
    if not phone_number:
        return ''
    return f"...{str(phone_number)[-4:]}"


def extract_dob_from_id(id_number):
    if not id_number or not isinstance(id_number, str) or len(id_number) != 13 or not id_number.isdigit():
        return None
    try:
        year_prefix = '19' if int(id_number[0:2]) > 22 else '20'
        year = int(year_prefix + id_number[0:2])
        month = int(id_number[2:4])
        day = int(id_number[4:6])
        return date(year, month, day)
    except (ValueError, TypeError):
        return None


def extract_gender_from_id(id_number):
    if not id_number or not isinstance(id_number, str) or len(id_number) != 13 or not id_number.isdigit():
        return None
    try:
        gender_digits = int(id_number[6:10])
        return 'M' if gender_digits >= 5000 else 'F'
    except (ValueError, TypeError):
        return None


def invalid_enrollment_session_response():
    return HttpResponseForbidden(
        'This application session is no longer valid. Please reopen your signup link and start again.'
    )


class PublicEnrollmentStartView(View):
    """
    Entry point for public enrollment via shared link
    Validates token and shows enrollment overview
    """
    template_name = 'members/public_enrollment/start.html'
    
    def get(self, request, token):
        """Access enrollment link and validate"""
        try:
            link = EnrollmentLink.objects.get(token=token)
        except EnrollmentLink.DoesNotExist:
            return render(request, 'members/public_enrollment/link_invalid.html', {
                'error': 'Invalid or expired enrollment link'
            }, status=404)
        
        # Validate link is active
        if not link.is_valid():
            return render(request, 'members/public_enrollment/link_invalid.html', {
                'error': 'This enrollment link has expired or is inactive'
            }, status=403)
        
        # Mark as used
        link.mark_used()
        
        # Store in session for this enrollment journey
        request.session['enrollment_token'] = token
        request.session['enrollment_scheme_id'] = link.scheme.id
        request.session['enrollment_branch_id'] = link.branch.id
        request.session['enrollment_agent_id'] = link.agent.id if link.agent else None
        
        context = {
            'scheme': link.scheme,
            'branch': link.branch,
            'agent': link.agent,
            'plans': link.scheme.plans.filter(is_active=True),
        }
        
        return render(request, self.template_name, context)
    
    def post(self, request, token):
        """Handle Begin Application button"""
        try:
            link = EnrollmentLink.objects.get(token=token)
        except EnrollmentLink.DoesNotExist:
            return render(request, 'members/public_enrollment/link_invalid.html', {
                'error': 'Invalid or expired enrollment link'
            }, status=404)
        
        # Validate link is active
        if not link.is_valid():
            return render(request, 'members/public_enrollment/link_invalid.html', {
                'error': 'This enrollment link has expired or is inactive'
            }, status=403)
        
        # Store in session for this enrollment journey
        request.session['enrollment_token'] = token
        request.session['enrollment_scheme_id'] = link.scheme.id
        request.session['enrollment_branch_id'] = link.branch.id
        request.session['enrollment_agent_id'] = link.agent.id if link.agent else None
        
        # Redirect to step 1
        return redirect('public_enrollment:step1_personal')


class Step1PersonalDetailsView(FormView):
    """
    Step 1: Personal Details
    Collect name, ID, contact information
    """
    template_name = 'members/public_enrollment/step1_personal.html'
    form_class = PersonalDetailsPublicForm
    
    def dispatch(self, request, *args, **kwargs):
        # Verify enrollment session
        if 'enrollment_token' not in request.session:
            return invalid_enrollment_session_response()
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['step'] = 1
        context['total_steps'] = 6
        return context
    
    def form_valid(self, form):
        # Store personal details in session for now
        request_data = self.request.POST.dict()
        self.request.session['enrollment_personal'] = {
            'first_name': form.cleaned_data['first_name'],
            'last_name': form.cleaned_data['last_name'],
            'email': form.cleaned_data['email'],
            'phone_number': form.cleaned_data['phone_number'],
            'id_number': str(form.cleaned_data.get('id_number', '')),
            'passport_number': str(form.cleaned_data.get('passport_number', '')),
            'date_of_birth': str(form.cleaned_data['date_of_birth']),
            'gender': form.cleaned_data['gender'],
            'marital_status': form.cleaned_data['marital_status'],
            'is_foreign': 'is_foreign' in self.request.POST
        }
        
        return redirect('public_enrollment:step2_address')


class Step2AddressView(FormView):
    """
    Step 2: Address Details
    Collect physical address
    """
    template_name = 'members/public_enrollment/step2_address.html'
    form_class = AddressPublicForm
    
    def dispatch(self, request, *args, **kwargs):
        if 'enrollment_personal' not in request.session:
            return redirect('public_enrollment:step1_personal')
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['step'] = 2
        context['total_steps'] = 6
        context['personal_data'] = self.request.session['enrollment_personal']
        return context
    
    def form_valid(self, form):
        self.request.session['enrollment_address'] = {
            'address_line_1': form.cleaned_data['physical_address_line_1'],
            'address_line_2': form.cleaned_data['physical_address_line_2'],
            'city': form.cleaned_data['physical_address_city'],
            'postal_code': form.cleaned_data['physical_address_postal_code'],
        }
        
        return redirect('public_enrollment:step3_plan')


class Step3PlanSelectionView(FormView):
    """
    Step 3: Plan Selection
    Choose insurance plan and payment method
    """
    template_name = 'members/public_enrollment/step3_plan_selection.html'
    form_class = PlanSelectionPublicForm
    
    def dispatch(self, request, *args, **kwargs):
        if 'enrollment_address' not in request.session:
            return redirect('public_enrollment:step2_address')
        return super().dispatch(request, *args, **kwargs)
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        scheme_id = self.request.session.get('enrollment_scheme_id')
        if scheme_id:
            kwargs['scheme'] = Scheme.objects.get(id=scheme_id)
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['step'] = 3
        context['total_steps'] = 6
        
        scheme_id = self.request.session.get('enrollment_scheme_id')
        if scheme_id:
            scheme = Scheme.objects.get(id=scheme_id)
            context['scheme'] = scheme
            context['plans'] = scheme.plans.filter(is_active=True)
        
        return context
    
    def form_valid(self, form):
        self.request.session['enrollment_plan'] = {
            'plan_id': form.cleaned_data['plan'].id,
            'plan_name': form.cleaned_data['plan'].name,
            'plan_premium': str(form.cleaned_data['plan'].premium),
            'payment_method': form.cleaned_data['payment_method'],
        }
        
        # Check if payment method is debit order
        if form.cleaned_data['payment_method'] == 'DEBIT_ORDER':
            return redirect('public_enrollment:step4_payment')
        else:
            # Skip to conditional questions
            return redirect('public_enrollment:step5_questions')


class Step4PaymentDetailsView(FormView):
    """
    Step 4: Payment Method Details (if debit order)
    Collect bank account information
    """
    template_name = 'members/public_enrollment/step4_payment_details.html'
    form_class = PaymentDetailsPublicForm
    
    def dispatch(self, request, *args, **kwargs):
        payment_method = request.session.get('enrollment_plan', {}).get('payment_method')
        if payment_method != 'DEBIT_ORDER':
            # Skip this step for non-debit-order payments
            return redirect('public_enrollment:step5_questions')
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['step'] = 4
        context['total_steps'] = 6
        return context
    
    def form_valid(self, form):
        self.request.session['enrollment_payment'] = {
            'bank_id': form.cleaned_data.get('bank').id if form.cleaned_data.get('bank') else None,
            'branch_code': form.cleaned_data.get('branch_code', ''),
            'account_holder': form.cleaned_data.get('account_holder_name', ''),
            'account_number': str(form.cleaned_data.get('account_number', '')),
            'debit_day': form.cleaned_data.get('debit_instruction_day', ''),
        }
        
        return redirect('public_enrollment:step5_questions')


class Step5ConditionalQuestionsView(View):
    """
    Step 5: Conditional Questions
    Smart form showing questions based on plan and previous answers
    """
    template_name = 'members/public_enrollment/step5_questions.html'
    
    def dispatch(self, request, *args, **kwargs):
        if 'enrollment_plan' not in request.session:
            return redirect('public_enrollment:step3_plan')
        return super().dispatch(request, *args, **kwargs)
    
    def get(self, request):
        scheme_id = request.session.get('enrollment_scheme_id')
        
        # Get applicable questions for this scheme
        all_questions = EnrollmentQuestionBank.objects.filter(
            scheme_id=scheme_id,
            is_active=True
        ).order_by('question_order')
        
        # Get previous answers from session
        previous_answers = request.session.get('enrollment_answers', {})
        
        # Determine which questions to show (conditional logic)
        questions_to_show = []
        for question in all_questions:
            if question.should_show(previous_answers):
                questions_to_show.append(question)
        
        # Get next unanswered question
        current_question = None
        for question in questions_to_show:
            if question.question_key not in previous_answers:
                current_question = question
                break
        
        if not current_question:
            # All questions answered, move to consent
            return redirect('public_enrollment:step6_consent')
        
        # Build form for current question
        form = ConditionalQuestionForm(current_question)
        
        context = {
            'step': 5,
            'total_steps': 6,
            'current_question': current_question,
            'question_number': len([q for q in questions_to_show if q.question_key in previous_answers]) + 1,
            'total_questions': len(questions_to_show),
            'form': form,
            'progress': int((len(previous_answers) / len(questions_to_show) * 100)) if questions_to_show else 0
        }
        
        return render(request, self.template_name, context)
    
    def post(self, request):
        scheme_id = request.session.get('enrollment_scheme_id')
        current_question_key = request.POST.get('question_key')
        answer_value = request.POST.get(current_question_key)
        
        if not current_question_key or not answer_value:
            messages.error(request, 'Please answer the question.')
            return redirect('public_enrollment:step5_questions')
        
        # Get question details for storage
        try:
            question = EnrollmentQuestionBank.objects.get(
                scheme_id=scheme_id,
                question_key=current_question_key
            )
        except EnrollmentQuestionBank.DoesNotExist:
            messages.error(request, 'Invalid question.')
            return redirect('public_enrollment:step5_questions')
        
        # Store answer in session
        if 'enrollment_answers' not in request.session:
            request.session['enrollment_answers'] = {}
        
        request.session['enrollment_answers'][current_question_key] = answer_value
        request.session.modified = True
        
        # Check if more questions remain
        all_questions = EnrollmentQuestionBank.objects.filter(
            scheme_id=scheme_id,
            is_active=True
        ).order_by('question_order')
        
        questions_to_show = [q for q in all_questions if q.should_show(request.session['enrollment_answers'])]
        
        unanswered = [q for q in questions_to_show if q.question_key not in request.session['enrollment_answers']]
        
        if unanswered:
            # More questions to go
            return redirect('public_enrollment:step5_questions')
        else:
            # All questions answered
            return redirect('public_enrollment:step6_consent')


class Step6ConsentAndTermsView(FormView):
    """
    Step 6: POPIA Consent & Terms and Conditions
    Final review before OTP verification
    """
    template_name = 'members/public_enrollment/step6_consent.html'
    form_class = POPIAConsentForm
    
    def dispatch(self, request, *args, **kwargs):
        if 'enrollment_plan' not in request.session:
            return redirect('public_enrollment:step3_plan')
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['step'] = 6
        context['total_steps'] = 6

        personal = self.request.session.get('enrollment_personal', {})
        plan_data = self.request.session.get('enrollment_plan', {})
        payment_method_key = plan_data.get('payment_method', '')

        payment_method_label = dict(PublicApplication.PAYMENT_METHOD_CHOICES).get(
            payment_method_key,
            payment_method_key,
        )

        premium_value = plan_data.get('plan_premium')
        selected_plan_obj = None
        if premium_value in (None, '') and plan_data.get('plan_id'):
            try:
                selected_plan_obj = Plan.objects.get(id=plan_data['plan_id'])
                premium_value = selected_plan_obj.premium or selected_plan_obj.main_premium
            except Plan.DoesNotExist:
                premium_value = None
        elif plan_data.get('plan_id'):
            try:
                selected_plan_obj = Plan.objects.get(id=plan_data['plan_id'])
            except Plan.DoesNotExist:
                selected_plan_obj = None

        premium_display = '-'
        if premium_value not in (None, ''):
            try:
                premium_display = f"R {Decimal(str(premium_value)):.2f}"
            except (InvalidOperation, ValueError, TypeError):
                premium_display = str(premium_value)

        beneficiary_data = self.request.session.get('enrollment_beneficiaries', {})
        family_data = self.request.session.get('enrollment_family_members', {})
        spouse_slots = 1 if selected_plan_obj and selected_plan_obj.spouses_allowed else 0
        child_slots = list(range(1, min((selected_plan_obj.children_allowed if selected_plan_obj else 0), 5) + 1))
        child_entries = [
            {
                'idx': idx,
                'first_name': family_data.get(f'child_{idx}_first_name', ''),
                'last_name': family_data.get(f'child_{idx}_last_name', ''),
                'gender': family_data.get(f'child_{idx}_gender', ''),
                'date_of_birth': family_data.get(f'child_{idx}_date_of_birth', ''),
                'id_number': family_data.get(f'child_{idx}_id_number', ''),
            }
            for idx in child_slots
        ]
        context['enrollment_data'] = {
            'personal': personal,
            'address': self.request.session.get('enrollment_address', {}),
            'plan': plan_data,
            'answers': self.request.session.get('enrollment_answers', {}),
        }
        context['applicant_name'] = f"{personal.get('first_name', '')} {personal.get('last_name', '')}".strip() or '-'
        context['applicant_email'] = personal.get('email') or '-'
        context['applicant_phone'] = personal.get('phone_number') or '-'
        context['selected_plan'] = plan_data.get('plan_name') or '-'
        context['payment_method'] = payment_method_label or '-'
        context['selected_plan_premium'] = premium_display
        context['spouse_slots'] = spouse_slots
        context['child_slots'] = child_slots
        context['child_entries'] = child_entries
        context.update(beneficiary_data)
        context.update(family_data)
        return context
    
    def form_valid(self, form):
        # Validate beneficiary capture before creating the application.
        b1_first_name = (self.request.POST.get('beneficiary_1_first_name') or '').strip()
        b1_last_name = (self.request.POST.get('beneficiary_1_last_name') or '').strip()
        b1_relationship = (self.request.POST.get('beneficiary_1_relationship') or '').strip()
        b1_share_raw = (self.request.POST.get('beneficiary_1_share') or '').strip()
        b1_phone_number = (self.request.POST.get('beneficiary_1_phone_number') or '').strip()
        b1_id_number = (self.request.POST.get('beneficiary_1_id_number') or '').strip()

        if not b1_first_name or not b1_last_name or not b1_relationship or not b1_share_raw or not b1_phone_number:
            form.add_error(None, 'Please complete all required primary beneficiary fields.')
            return self.form_invalid(form)

        try:
            b1_share = int(b1_share_raw)
        except (TypeError, ValueError):
            form.add_error(None, 'Primary beneficiary share must be a valid number.')
            return self.form_invalid(form)

        if b1_share < 1 or b1_share > 100:
            form.add_error(None, 'Primary beneficiary share must be between 1 and 100.')
            return self.form_invalid(form)

        if not b1_phone_number.isdigit() or len(b1_phone_number) < 10:
            form.add_error(None, 'Beneficiary contact number must be at least 10 digits.')
            return self.form_invalid(form)

        self.request.session['enrollment_beneficiaries'] = {
            'beneficiary_1_first_name': b1_first_name,
            'beneficiary_1_last_name': b1_last_name,
            'beneficiary_1_relationship': b1_relationship,
            'beneficiary_1_share': str(b1_share),
            'beneficiary_1_phone_number': b1_phone_number,
            'beneficiary_1_id_number': b1_id_number,
        }

        plan = Plan.objects.filter(id=self.request.session['enrollment_plan']['plan_id']).first()
        spouse_allowed = bool(plan and plan.spouses_allowed)
        children_allowed = min(plan.children_allowed, 5) if plan else 0

        family_member_answers = []
        family_member_session = {}

        if spouse_allowed:
            spouse_first_name = (self.request.POST.get('spouse_first_name') or '').strip()
            spouse_last_name = (self.request.POST.get('spouse_last_name') or '').strip()
            spouse_phone_number = (self.request.POST.get('spouse_phone_number') or '').strip()
            spouse_gender = (self.request.POST.get('spouse_gender') or '').strip()
            spouse_date_of_birth = (self.request.POST.get('spouse_date_of_birth') or '').strip()
            spouse_id_number = (self.request.POST.get('spouse_id_number') or '').strip()

            spouse_has_data = any([spouse_first_name, spouse_last_name, spouse_phone_number, spouse_gender, spouse_date_of_birth, spouse_id_number])
            if spouse_has_data:
                if not spouse_first_name or not spouse_last_name or not spouse_phone_number:
                    form.add_error(None, 'If you add a spouse, first name, last name, and contact number are required.')
                    return self.form_invalid(form)
                if not spouse_phone_number.isdigit() or len(spouse_phone_number) < 10:
                    form.add_error(None, 'Spouse contact number must be at least 10 digits.')
                    return self.form_invalid(form)
                if spouse_id_number and len(spouse_id_number) == 13 and spouse_id_number.isdigit():
                    spouse_date_of_birth = spouse_date_of_birth or str(extract_dob_from_id(spouse_id_number) or '')
                    inferred_gender = extract_gender_from_id(spouse_id_number)
                    if inferred_gender:
                        spouse_gender = spouse_gender or ('Male' if inferred_gender == 'M' else 'Female')
                if not spouse_gender or not spouse_date_of_birth:
                    form.add_error(None, 'Spouse gender and date of birth are required when spouse details are provided.')
                    return self.form_invalid(form)

                family_member_session.update({
                    'spouse_first_name': spouse_first_name,
                    'spouse_last_name': spouse_last_name,
                    'spouse_phone_number': spouse_phone_number,
                    'spouse_gender': spouse_gender,
                    'spouse_date_of_birth': spouse_date_of_birth,
                    'spouse_id_number': spouse_id_number,
                })
                family_member_answers.extend([
                    ('spouse_first_name', spouse_first_name),
                    ('spouse_last_name', spouse_last_name),
                    ('spouse_phone_number', spouse_phone_number),
                    ('spouse_gender', spouse_gender),
                    ('spouse_date_of_birth', spouse_date_of_birth),
                    ('spouse_id_number', spouse_id_number),
                ])

        for idx in range(1, children_allowed + 1):
            child_first_name = (self.request.POST.get(f'child_{idx}_first_name') or '').strip()
            child_last_name = (self.request.POST.get(f'child_{idx}_last_name') or '').strip()
            child_gender = (self.request.POST.get(f'child_{idx}_gender') or '').strip()
            child_date_of_birth = (self.request.POST.get(f'child_{idx}_date_of_birth') or '').strip()
            child_id_number = (self.request.POST.get(f'child_{idx}_id_number') or '').strip()

            child_has_data = any([child_first_name, child_last_name, child_gender, child_date_of_birth, child_id_number])
            if not child_has_data:
                continue

            if not child_first_name or not child_last_name:
                form.add_error(None, f'Child {idx} first name and last name are required when child details are provided.')
                return self.form_invalid(form)
            if child_id_number and len(child_id_number) == 13 and child_id_number.isdigit():
                child_date_of_birth = child_date_of_birth or str(extract_dob_from_id(child_id_number) or '')
                inferred_gender = extract_gender_from_id(child_id_number)
                if inferred_gender:
                    child_gender = child_gender or ('Male' if inferred_gender == 'M' else 'Female')
            if not child_gender or not child_date_of_birth:
                form.add_error(None, f'Child {idx} gender and date of birth are required when child details are provided.')
                return self.form_invalid(form)

            family_member_session.update({
                f'child_{idx}_first_name': child_first_name,
                f'child_{idx}_last_name': child_last_name,
                f'child_{idx}_gender': child_gender,
                f'child_{idx}_date_of_birth': child_date_of_birth,
                f'child_{idx}_id_number': child_id_number,
            })
            family_member_answers.extend([
                (f'child_{idx}_first_name', child_first_name),
                (f'child_{idx}_last_name', child_last_name),
                (f'child_{idx}_gender', child_gender),
                (f'child_{idx}_date_of_birth', child_date_of_birth),
                (f'child_{idx}_id_number', child_id_number),
            ])

        self.request.session['enrollment_family_members'] = family_member_session
        self.request.session.modified = True

        # Create PublicApplication from session data
        with transaction.atomic():
            try:
                personal = self.request.session['enrollment_personal']
                scheme_id = self.request.session['enrollment_scheme_id']
                plan_id = self.request.session['enrollment_plan']['plan_id']
                
                app_data = {
                    'first_name': personal['first_name'],
                    'last_name': personal['last_name'],
                    'email': personal['email'],
                    'phone_number': personal['phone_number'],
                    'id_number': personal['id_number'] or None,
                    'passport_number': personal['passport_number'] or None,
                    'date_of_birth': personal['date_of_birth'],
                    'gender': personal['gender'],
                    'marital_status': personal['marital_status'],
                    'physical_address_line_1': self.request.session['enrollment_address']['address_line_1'],
                    'physical_address_line_2': self.request.session['enrollment_address'].get('address_line_2', ''),
                    'physical_address_city': self.request.session['enrollment_address']['city'],
                    'physical_address_postal_code': self.request.session['enrollment_address'].get('postal_code', ''),
                    'scheme_id': scheme_id,
                    'plan_id': plan_id,
                    'payment_method': self.request.session['enrollment_plan']['payment_method'],
                    'enrollment_link_id': None,  # Can be linked if token was in session
                    'status': 'draft',
                }
                
                # Add payment details if debit order
                if self.request.session['enrollment_plan']['payment_method'] == 'DEBIT_ORDER':
                    payment = self.request.session.get('enrollment_payment', {})
                    app_data.update({
                        'bank_id': payment.get('bank_id'),
                        'branch_code': payment.get('branch_code', ''),
                        'account_holder_name': payment.get('account_holder', ''),
                        'account_number': payment.get('account_number', ''),
                        'debit_instruction_day': payment.get('debit_day', ''),
                    })
                
                # Create application
                application = PublicApplication.objects.create(**app_data)
                
                # Store application answers
                answers = self.request.session.get('enrollment_answers', {})
                for question_key, answer_value in answers.items():
                    try:
                        question = EnrollmentQuestionBank.objects.get(
                            scheme_id=scheme_id,
                            question_key=question_key
                        )
                        ApplicationAnswer.objects.create(
                            application=application,
                            question_key=question_key,
                            question_text=question.question_text,
                            answer=str(answer_value),
                            answer_type=question.question_type
                        )
                    except EnrollmentQuestionBank.DoesNotExist:
                        pass

                # Persist beneficiary details with the application for downstream conversion.
                beneficiary_answers = [
                    ('beneficiary_1_first_name', b1_first_name),
                    ('beneficiary_1_last_name', b1_last_name),
                    ('beneficiary_1_relationship', b1_relationship),
                    ('beneficiary_1_share', str(b1_share)),
                    ('beneficiary_1_phone_number', b1_phone_number),
                    ('beneficiary_1_id_number', b1_id_number),
                ]

                for key, value in beneficiary_answers:
                    ApplicationAnswer.objects.create(
                        application=application,
                        question_key=key,
                        question_text=key.replace('_', ' ').title(),
                        answer=value,
                        answer_type='text',
                    )

                for key, value in family_member_answers:
                    ApplicationAnswer.objects.create(
                        application=application,
                        question_key=key,
                        question_text=key.replace('_', ' ').title(),
                        answer=value,
                        answer_type='text',
                    )
                
                # Store POPIA consents
                consent_mappings = {
                    'agree_to_terms': 'data_processing',
                    'consent_marketing_sms': 'marketing_sms',
                    'consent_marketing_email': 'marketing_email',
                }
                
                for field, consent_type in consent_mappings.items():
                    if field in form.cleaned_data:
                        POPIAConsent.objects.create(
                            application=application,
                            consent_type=consent_type,
                            consented=form.cleaned_data[field],
                            ip_address=self.request.META.get('REMOTE_ADDR'),
                        )
                
                # Create and send OTP
                otp = EnrollmentOTPVerification.objects.create(
                    application=application,
                    phone_number=personal['phone_number'],
                    expires_at=timezone.now() + timedelta(minutes=15)
                )
                
                # Send OTP via SMS
                sms_sent_successfully = False
                sms_status_message = ''
                try:
                    sms_log = send_otp_sms(personal['phone_number'], otp.otp_code)
                    sms_sent_successfully = sms_log.status in {'SENT', 'TEST'}
                    sms_status_message = sms_log.detail or sms_log.status
                except Exception as e:
                    logger.error(f"Failed to send OTP SMS: {str(e)}")
                    sms_status_message = str(e)
                
                # Store application ID for next step
                self.request.session['enrollment_app_id'] = application.id
                self.request.session['otp_phone_masked'] = mask_phone_number(personal['phone_number'])
                self.request.session['otp_sms_sent_successfully'] = sms_sent_successfully
                self.request.session['otp_sms_status_message'] = sms_status_message
                self.request.session.modified = True
                
                return redirect('public_enrollment:otp_verify')
                
            except Exception as e:
                logger.error(f"Error creating application: {str(e)}")
                messages.error(self.request, 'An error occurred. Please try again.')
                return self.form_invalid(form)

    def form_invalid(self, form):
        context = self.get_context_data(form=form)
        context.update({
            'beneficiary_1_first_name': self.request.POST.get('beneficiary_1_first_name', ''),
            'beneficiary_1_last_name': self.request.POST.get('beneficiary_1_last_name', ''),
            'beneficiary_1_relationship': self.request.POST.get('beneficiary_1_relationship', ''),
            'beneficiary_1_share': self.request.POST.get('beneficiary_1_share', '100'),
            'beneficiary_1_phone_number': self.request.POST.get('beneficiary_1_phone_number', ''),
            'beneficiary_1_id_number': self.request.POST.get('beneficiary_1_id_number', ''),
            'spouse_first_name': self.request.POST.get('spouse_first_name', ''),
            'spouse_last_name': self.request.POST.get('spouse_last_name', ''),
            'spouse_phone_number': self.request.POST.get('spouse_phone_number', ''),
            'spouse_gender': self.request.POST.get('spouse_gender', ''),
            'spouse_date_of_birth': self.request.POST.get('spouse_date_of_birth', ''),
            'spouse_id_number': self.request.POST.get('spouse_id_number', ''),
        })
        plan = Plan.objects.filter(id=self.request.session.get('enrollment_plan', {}).get('plan_id')).first()
        if plan:
            context['child_entries'] = [
                {
                    'idx': idx,
                    'first_name': self.request.POST.get(f'child_{idx}_first_name', ''),
                    'last_name': self.request.POST.get(f'child_{idx}_last_name', ''),
                    'gender': self.request.POST.get(f'child_{idx}_gender', ''),
                    'date_of_birth': self.request.POST.get(f'child_{idx}_date_of_birth', ''),
                    'id_number': self.request.POST.get(f'child_{idx}_id_number', ''),
                }
                for idx in range(1, min(plan.children_allowed, 5) + 1)
            ]
        return self.render_to_response(context)


class OTPVerificationView(FormView):
    """
    OTP Verification - Final step before application submission
    User enters 6-digit code sent to their phone
    """
    template_name = 'members/public_enrollment/otp_verification.html'
    form_class = OTPVerificationForm
    
    def dispatch(self, request, *args, **kwargs):
        if 'enrollment_app_id' not in request.session:
            return redirect('public_enrollment:step1_personal')
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        app_id = self.request.session.get('enrollment_app_id')
        try:
            application = PublicApplication.objects.get(id=app_id)
            otp_obj = application.otp_verification
            context['phone_masked'] = self.request.session.get('otp_phone_masked') or mask_phone_number(otp_obj.phone_number)
            context['can_resend'] = otp_obj.can_resend()
            context['attempts_remaining'] = max(otp_obj.max_attempts - otp_obj.verification_attempts, 0)
            context['resend_count'] = otp_obj.resend_count
            context['expiry_timestamp'] = int(otp_obj.expires_at.timestamp())
            context['application_id'] = application.id
            context['sms_sent_successfully'] = self.request.session.get('otp_sms_sent_successfully', True)
            context['sms_status_message'] = self.request.session.get('otp_sms_status_message', '')
        except Exception:
            pass
        
        return context
    
    def form_valid(self, form):
        app_id = self.request.session.get('enrollment_app_id')
        application = PublicApplication.objects.get(id=app_id)
        otp = application.otp_verification
        
        # Verify OTP
        success, message = otp.verify_otp(form.cleaned_data['otp_code'])
        
        if success:
            # Mark application as submitted
            application.submit()
            
            # Clear session
            for key in list(self.request.session.keys()):
                if key.startswith('enrollment'):
                    del self.request.session[key]
            
            # Redirect to confirmation page
            return redirect('public_enrollment:success', app_id=application.id)
        else:
            messages.error(self.request, message)
            return self.form_invalid(form)


class OTPResendView(View):
    """
    Resend OTP via SMS
    Called via AJAX
    """
    def post(self, request):
        if request.headers.get('X-Requested-With') != 'XMLHttpRequest':
            return HttpResponseBadRequest()
        
        app_id = request.session.get('enrollment_app_id')
        
        try:
            application = PublicApplication.objects.get(id=app_id)
            otp = application.otp_verification
            
            if not otp.can_resend():
                return JsonResponse({
                    'success': False,
                    'message': f'Maximum resends reached. Please try again later.'
                }, status=400)
            
            # Resend OTP
            otp.resend()
            
            # Send SMS
            sms_log = send_otp_sms(otp.phone_number, otp.otp_code)
            sms_sent_successfully = sms_log.status in {'SENT', 'TEST'}
            request.session['otp_phone_masked'] = mask_phone_number(otp.phone_number)
            request.session['otp_sms_sent_successfully'] = sms_sent_successfully
            request.session['otp_sms_status_message'] = sms_log.detail or sms_log.status
            request.session.modified = True

            if not sms_sent_successfully:
                return JsonResponse({
                    'success': False,
                    'message': sms_log.detail or 'OTP SMS could not be sent.'
                }, status=500)
            
            return JsonResponse({
                'success': True,
                'message': 'OTP resent successfully'
            })
        
        except Exception as e:
            logger.error(f"Error resending OTP: {str(e)}")
            return JsonResponse({
                'success': False,
                'message': 'Error resending OTP'
            }, status=500)


class EnrollmentSuccessView(TemplateView):
    """
    Success page after OTP verification
    Shows application reference and next steps
    """
    template_name = 'members/public_enrollment/success.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        app_id = kwargs.get('app_id')
        
        try:
            application = PublicApplication.objects.get(id=app_id)
            context['application'] = application
        except PublicApplication.DoesNotExist:
            context['error'] = 'Application not found'
        
        return context
