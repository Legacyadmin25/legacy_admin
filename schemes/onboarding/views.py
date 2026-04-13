from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View
from django.views.generic import ListView, DetailView

from .forms import (
    BranchOnboardingReviewForm,
    SchemeOnboardingStep1Form,
    SchemeOnboardingStep2Form,
)
from .models import BranchSchemeOnboarding


def _session_key(token: str) -> str:
    return f'scheme_onboarding_step_{token}'


def _get_valid_onboarding(token: str) -> BranchSchemeOnboarding:
    onboarding = get_object_or_404(BranchSchemeOnboarding, onboarding_token=token)
    if not onboarding.is_token_valid():
        return None
    return onboarding


def _can_review(user, onboarding: BranchSchemeOnboarding) -> bool:
    if not user.is_authenticated:
        return False
    if user.is_superuser or user.is_staff:
        return True
    return bool(getattr(user, 'branch_id', None) == onboarding.branch_id)


class SchemeOnboardingStartView(View):
    template_name = 'schemes/onboarding/onboarding_start.html'

    def get(self, request, token):
        onboarding = _get_valid_onboarding(token)
        if onboarding is None:
            return HttpResponseForbidden('Invalid or expired onboarding link.')

        if onboarding.status in [
            BranchSchemeOnboarding.STATUS_SUBMITTED,
            BranchSchemeOnboarding.STATUS_APPROVED,
            BranchSchemeOnboarding.STATUS_REJECTED,
        ]:
            return render(request, self.template_name, {'onboarding': onboarding, 'locked': True})

        return render(request, self.template_name, {'onboarding': onboarding, 'locked': False})

    def post(self, request, token):
        onboarding = _get_valid_onboarding(token)
        if onboarding is None:
            return HttpResponseForbidden('Invalid or expired onboarding link.')

        request.session[_session_key(token)] = 1
        onboarding.mark_used()
        return redirect('scheme_onboarding:step1', token=token)


class SchemeOnboardingStep1View(View):
    template_name = 'schemes/onboarding/onboarding_step1.html'

    def get(self, request, token):
        onboarding = _get_valid_onboarding(token)
        if onboarding is None:
            return HttpResponseForbidden('Invalid or expired onboarding link.')

        if request.session.get(_session_key(token), 0) < 1:
            return redirect('scheme_onboarding:start', token=token)

        form = SchemeOnboardingStep1Form(instance=onboarding)
        return render(request, self.template_name, {'form': form, 'onboarding': onboarding})

    def post(self, request, token):
        onboarding = _get_valid_onboarding(token)
        if onboarding is None:
            return HttpResponseForbidden('Invalid or expired onboarding link.')

        form = SchemeOnboardingStep1Form(request.POST, instance=onboarding)
        if not form.is_valid():
            return render(request, self.template_name, {'form': form, 'onboarding': onboarding})

        form.save()
        request.session[_session_key(token)] = 2
        return redirect('scheme_onboarding:step2', token=token)


class SchemeOnboardingStep2View(View):
    template_name = 'schemes/onboarding/onboarding_step2.html'

    def get(self, request, token):
        onboarding = _get_valid_onboarding(token)
        if onboarding is None:
            return HttpResponseForbidden('Invalid or expired onboarding link.')

        if request.session.get(_session_key(token), 0) < 2:
            return redirect('scheme_onboarding:step1', token=token)

        form = SchemeOnboardingStep2Form(instance=onboarding)
        return render(request, self.template_name, {'form': form, 'onboarding': onboarding})

    def post(self, request, token):
        onboarding = _get_valid_onboarding(token)
        if onboarding is None:
            return HttpResponseForbidden('Invalid or expired onboarding link.')

        form = SchemeOnboardingStep2Form(request.POST, instance=onboarding)
        if not form.is_valid():
            return render(request, self.template_name, {'form': form, 'onboarding': onboarding})

        form.save()
        request.session[_session_key(token)] = 3
        return redirect('scheme_onboarding:review', token=token)


class SchemeOnboardingReviewView(View):
    template_name = 'schemes/onboarding/onboarding_review.html'

    def get(self, request, token):
        onboarding = _get_valid_onboarding(token)
        if onboarding is None:
            return HttpResponseForbidden('Invalid or expired onboarding link.')

        if request.session.get(_session_key(token), 0) < 3:
            return redirect('scheme_onboarding:step2', token=token)

        return render(request, self.template_name, {'onboarding': onboarding})


class SchemeOnboardingSubmitView(View):
    def post(self, request, token):
        onboarding = _get_valid_onboarding(token)
        if onboarding is None:
            return HttpResponseForbidden('Invalid or expired onboarding link.')

        if request.session.get(_session_key(token), 0) < 3:
            return redirect('scheme_onboarding:step1', token=token)

        submitter = (onboarding.email or '').strip() or 'scheme-owner'
        onboarding.submit(submitted_by=submitter)
        request.session.pop(_session_key(token), None)
        messages.success(request, 'Your onboarding was submitted for branch review.')
        return redirect('scheme_onboarding:start', token=token)


class BranchOnboardingReviewListView(LoginRequiredMixin, ListView):
    model = BranchSchemeOnboarding
    template_name = 'schemes/onboarding/branch_review_list.html'
    context_object_name = 'onboardings'

    def get_queryset(self):
        queryset = BranchSchemeOnboarding.objects.filter(status=BranchSchemeOnboarding.STATUS_SUBMITTED)
        if self.request.user.is_superuser or self.request.user.is_staff:
            return queryset
        return queryset.filter(branch_id=getattr(self.request.user, 'branch_id', None))


class BranchOnboardingDetailView(LoginRequiredMixin, DetailView):
    model = BranchSchemeOnboarding
    template_name = 'schemes/onboarding/branch_review_detail.html'
    context_object_name = 'onboarding'

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        if not _can_review(request.user, self.object):
            return HttpResponseForbidden('You do not have permission to review this onboarding.')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['review_form'] = BranchOnboardingReviewForm()
        return context


class BranchOnboardingApproveView(LoginRequiredMixin, View):
    def post(self, request, pk):
        onboarding = get_object_or_404(BranchSchemeOnboarding, pk=pk)
        if not _can_review(request.user, onboarding):
            return HttpResponseForbidden('You do not have permission to approve this onboarding.')
        onboarding.approve(request.user)
        messages.success(request, 'Onboarding approved.')
        return redirect(reverse('scheme_onboarding:branch_detail', kwargs={'pk': onboarding.pk}))


class BranchOnboardingReopenView(LoginRequiredMixin, View):
    def post(self, request, pk):
        onboarding = get_object_or_404(BranchSchemeOnboarding, pk=pk)
        if not _can_review(request.user, onboarding):
            return HttpResponseForbidden('You do not have permission to reopen this onboarding.')

        form = BranchOnboardingReviewForm(request.POST)
        if not form.is_valid() or form.cleaned_data['action'] != BranchOnboardingReviewForm.ACTION_REOPEN:
            messages.error(request, 'Provide correction notes before reopening.')
            return redirect(reverse('scheme_onboarding:branch_detail', kwargs={'pk': onboarding.pk}))

        onboarding.reopen(request.user, form.cleaned_data['notes'])
        messages.success(request, 'Onboarding reopened for corrections.')
        return redirect(reverse('scheme_onboarding:branch_detail', kwargs={'pk': onboarding.pk}))
