from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from settings_app.models import Agent
from members.models import Member, Policy
from members.forms import (
    PersonalDetailsForm,
    PolicyDetailsForm,
    DependentForm,
    BeneficiaryForm,
    PaymentOptionsForm,
    OTPForm,
)
from .models import DiySignupLog  # If you’ve added the logging model

# ─────────────────────────────────────────────────────────────
# 0) Entry point: Welcome page (already updated)
# ─────────────────────────────────────────────────────────────

def diy_signup_start(request, token):
    # Fetch the agent with the given token and ensure it is active
    agent = get_object_or_404(Agent, diy_token=token, is_active=True)

    # Store session data for the DIY signup process
    request.session['is_diy_signup']   = True
    request.session['diy_agent_id']     = agent.id
    request.session['diy_scheme_id']    = agent.scheme.id if agent.scheme else None
    request.session['diy_token']        = token

    # Render the welcome page for DIY signup
    return render(request, 'members/diy_welcome.html', {
        'agent':  agent,
        'scheme': agent.scheme,
    })


# ─────────────────────────────────────────────────────────────
# 1) Step 1: Personal & Address Details
# ─────────────────────────────────────────────────────────────

def create_personal(request):
    # Session-lost guard
    agent_id = request.session.get('diy_agent_id')
    if not agent_id:
        return redirect('members:diy_signup_start', token=request.session.get('diy_token',''))

    agent = get_object_or_404(Agent, pk=agent_id)
    scheme = agent.scheme

    if request.method == 'POST':
        form = PersonalDetailsForm(request.POST)
        if form.is_valid():
            member = form.save(commit=False)
            member.agent = agent
            member.scheme = scheme
            member.save()
            request.session['diy_member_id'] = member.id
            return redirect('members:policy_create_step2')
    else:
        form = PersonalDetailsForm()

    return render(request, 'step1_personal_address.html', {
        'p_form': form,
        'agent': agent,
        'scheme': scheme,
        'step': 1,
        'steps': [1,2,3,4,5,6,7],
    })


# ─────────────────────────────────────────────────────────────
# 2) Step 2: Policy Details
# ─────────────────────────────────────────────────────────────

def create_policy_details(request):
    # Session-lost guard
    if not request.session.get('diy_agent_id'):
        return redirect('members:diy_signup_start', token=request.session.get('diy_token',''))

    agent = Agent.objects.get(pk=request.session['diy_agent_id'])
    scheme = agent.scheme
    member = Member.objects.get(pk=request.session['diy_member_id'])

    if request.method == 'POST':
        form = PolicyDetailsForm(request.POST)
        if form.is_valid():
            policy = form.save(commit=False)
            policy.agent = agent
            policy.scheme = scheme
            policy.member = member
            policy.save()
            request.session['diy_policy_id'] = policy.id
            return redirect('members:create_dependents', pk=policy.pk)
    else:
        form = PolicyDetailsForm(initial={'scheme': scheme})

    return render(request, 'step2_policy_details.html', {
        'form': form,
        'agent': agent,
        'scheme': scheme,
        'member': member,
        'step': 2,
        'steps': [1,2,3,4,5,6,7],
    })


# ─────────────────────────────────────────────────────────────
# 3) Step 3: Dependents & Beneficiaries
# ─────────────────────────────────────────────────────────────

def create_dependents_beneficiaries(request, pk):
    # Session-lost guard
    if not request.session.get('diy_agent_id'):
        return redirect('members:diy_signup_start', token=request.session.get('diy_token',''))

    policy = get_object_or_404(Policy, pk=pk)
    dependents   = policy.member.dependents.all()
    beneficiaries= policy.member.beneficiaries.all()

    dep_form = DependentForm(request.POST or None)
    ben_form = BeneficiaryForm(request.POST or None)

    if request.method == 'POST':
        if 'save_dependent' in request.POST and dep_form.is_valid():
            dep = dep_form.save(commit=False)
            dep.member = policy.member
            dep.save()
            return redirect('members:create_dependents', pk=pk)
        if 'save_beneficiary' in request.POST and ben_form.is_valid():
            ben = ben_form.save(commit=False)
            ben.member = policy.member
            ben.save()
            return redirect('members:create_dependents', pk=pk)
        if 'next' in request.POST:
            return redirect('members:create_payment', pk=pk)

    return render(request, 'step3_dependents_beneficiaries.html', {
        'dep_form': dep_form,
        'ben_form': ben_form,
        'dependents': dependents,
        'beneficiaries': beneficiaries,
        'policy': policy,
        'step': 3,
        'steps': [1,2,3,4,5,6,7],
    })


# ─────────────────────────────────────────────────────────────
# 4) Step 4: Payment Options
# ─────────────────────────────────────────────────────────────

def create_payment_options(request, pk):
    # Session-lost guard
    if not request.session.get('diy_agent_id'):
        return redirect('members:diy_signup_start', token=request.session.get('diy_token',''))

    policy = get_object_or_404(Policy, pk=pk)
    form = PaymentOptionsForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        form.save(policy)  # assume your form handles updating policy & member
        # send OTP logic here...
        return redirect('members:confirm_otp', pk=pk)

    return render(request, 'step4_payment_options.html', {
        'form': form,
        'policy': policy,
        'step': 4,
        'steps': [1,2,3,4,5,6,7],
    })


# ─────────────────────────────────────────────────────────────
# 5) Step 5: Confirm OTP
# ─────────────────────────────────────────────────────────────

def confirm_otp(request, pk):
    # Session-lost guard
    if not request.session.get('diy_agent_id'):
        return redirect('members:diy_signup_start', token=request.session.get('diy_token',''))

    policy = get_object_or_404(Policy, pk=pk)
    phone  = policy.member.phone_number
    form   = OTPForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        # verify OTP...
        return redirect('members:policy_certificate', pk=pk)

    return render(request, 'step5_confirm_otp.html', {
        'form': form,
        'phone': phone,
        'policy': policy,
        'step': 5,
        'steps': [1,2,3,4,5,6,7],
        'expires_at': form.expires_at,  # if your form provides it
    })


# ─────────────────────────────────────────────────────────────
# 6) Step 6: Policy Certificate (view only)
# ─────────────────────────────────────────────────────────────

def policy_certificate(request, pk):
    # Session-lost guard
    if not request.session.get('diy_agent_id'):
        return redirect('members:diy_signup_start', token=request.session.get('diy_token',''))

    policy = get_object_or_404(Policy, pk=pk)
    member = policy.member

    return render(request, 'step6_policy_completion.html', {
        'policy': policy,
        'member': member,
        'barcode_url': policy.barcode_url,
        'qr_url': policy.qr_url,
        'step': 6,
        'steps': [1,2,3,4,5,6,7],
    })


# ─────────────────────────────────────────────────────────────
# 7) Step 7: Final “Done” Screen
# ─────────────────────────────────────────────────────────────

def create_done(request, pk):
    # Session-lost guard
    if not request.session.get('diy_agent_id'):
        return redirect('members:diy_signup_start', token=request.session.get('diy_token',''))

    policy = get_object_or_404(Policy, pk=pk)
    member = policy.member

    # Log it (if you implemented DiySignupLog)
    try:
        DiySignupLog.objects.create(agent_id=request.session['diy_agent_id'],
                                    member=member)
    except:
        pass

    return render(request, 'step7_create_done.html', {
        'policy': policy,
        'member': member,
        'step': 7,
        'steps': [1,2,3,4,5,6,7],
    })
