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
    SchemeProductForm,
)
from .models import BranchSchemeOnboarding, SchemeProduct


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
        context['products'] = self.object.products.select_related('wholesale_plan').all()
        context['underpriced_count'] = self.object.products.filter(retail_below_wholesale=True).count()
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


# ---------------------------------------------------------------------------
# Product Builder (token-based, accessible after onboarding is approved)
# ---------------------------------------------------------------------------

def _wholesale_plans_for_branch(branch):
    """Return all wholesale Plans that belong to the given branch."""
    from schemes.models import Plan
    return Plan.objects.filter(is_wholesale=True, scheme__branch=branch, is_active=True)


class SchemeProductBuilderView(View):
    """
    GET  /scheme-onboarding/products/<token>/
    Shows existing SchemeProducts for this onboarding + an add form.
    Only accessible once status is 'approved'.
    """
    template_name = 'schemes/onboarding/product_builder.html'

    def _get_approved_onboarding(self, token):
        onboarding = get_object_or_404(BranchSchemeOnboarding, onboarding_token=token)
        if onboarding.status != BranchSchemeOnboarding.STATUS_APPROVED:
            return None
        return onboarding

    def get(self, request, token):
        onboarding = self._get_approved_onboarding(token)
        if onboarding is None:
            return HttpResponseForbidden('Product builder is only available after your onboarding is approved.')

        wholesale_qs = _wholesale_plans_for_branch(onboarding.branch)
        form = SchemeProductForm(wholesale_qs=wholesale_qs)
        products = onboarding.products.select_related('wholesale_plan').all()
        return render(request, self.template_name, {
            'onboarding': onboarding,
            'form': form,
            'products': products,
            'wholesale_plans': wholesale_qs,
        })

    def post(self, request, token):
        onboarding = self._get_approved_onboarding(token)
        if onboarding is None:
            return HttpResponseForbidden('Product builder is only available after your onboarding is approved.')

        wholesale_qs = _wholesale_plans_for_branch(onboarding.branch)
        form = SchemeProductForm(request.POST, wholesale_qs=wholesale_qs)
        products = onboarding.products.select_related('wholesale_plan').all()

        if not form.is_valid():
            return render(request, self.template_name, {
                'onboarding': onboarding,
                'form': form,
                'products': products,
                'wholesale_plans': wholesale_qs,
            })

        product = form.save(commit=False)
        product.onboarding = onboarding
        product.save()

        if product.retail_below_wholesale:
            messages.warning(
                request,
                f'"{product.product_name}" has a retail premium (R{product.retail_premium}) '
                f'below the wholesale rate (R{product.wholesale_plan.premium}). '
                'Your branch owner will see this flag during review.'
            )
        else:
            messages.success(request, f'"{product.product_name}" added successfully.')

        return redirect(reverse('scheme_onboarding:product_builder', kwargs={'token': token}))


class SchemeProductEditView(View):
    """POST /scheme-onboarding/products/<token>/<product_pk>/edit/"""
    template_name = 'schemes/onboarding/product_edit.html'

    def _get_context(self, token, product_pk):
        onboarding = get_object_or_404(
            BranchSchemeOnboarding,
            onboarding_token=token,
            status=BranchSchemeOnboarding.STATUS_APPROVED,
        )
        product = get_object_or_404(SchemeProduct, pk=product_pk, onboarding=onboarding)
        wholesale_qs = _wholesale_plans_for_branch(onboarding.branch)
        return onboarding, product, wholesale_qs

    def get(self, request, token, product_pk):
        onboarding, product, wholesale_qs = self._get_context(token, product_pk)
        form = SchemeProductForm(instance=product, wholesale_qs=wholesale_qs)
        return render(request, self.template_name, {
            'onboarding': onboarding,
            'product': product,
            'form': form,
        })

    def post(self, request, token, product_pk):
        onboarding, product, wholesale_qs = self._get_context(token, product_pk)
        form = SchemeProductForm(request.POST, instance=product, wholesale_qs=wholesale_qs)
        if not form.is_valid():
            return render(request, self.template_name, {
                'onboarding': onboarding,
                'product': product,
                'form': form,
            })
        product = form.save()
        if product.retail_below_wholesale:
            messages.warning(
                request,
                f'"{product.product_name}" is still priced below the wholesale rate '
                f'(R{product.wholesale_plan.premium}). Branch owner will see this flag.'
            )
        else:
            messages.success(request, f'"{product.product_name}" updated.')
        return redirect(reverse('scheme_onboarding:product_builder', kwargs={'token': token}))


class SchemeProductDeleteView(View):
    """POST /scheme-onboarding/products/<token>/<product_pk>/delete/"""

    def post(self, request, token, product_pk):
        onboarding = get_object_or_404(
            BranchSchemeOnboarding,
            onboarding_token=token,
            status=BranchSchemeOnboarding.STATUS_APPROVED,
        )
        product = get_object_or_404(SchemeProduct, pk=product_pk, onboarding=onboarding)
        name = product.product_name
        product.delete()
        messages.success(request, f'"{name}" removed.')
        return redirect(reverse('scheme_onboarding:product_builder', kwargs={'token': token}))
