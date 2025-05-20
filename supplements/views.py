from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required

from .models import SupplementaryBenefit
from .forms import SupplementaryBenefitForm
from schemes.models import Scheme  # for the scheme list dropdown

@login_required
def supplementary_benefits_setup(request):
    schemes = Scheme.objects.all()
    benefits = SupplementaryBenefit.objects.all()

    selected_scheme = request.GET.get('scheme')
    search_query = request.GET.get('q')

    # Filter by scheme
    if selected_scheme and selected_scheme != 'all':
        benefits = benefits.filter(scheme_id=selected_scheme)

    # Filter by search
    if search_query:
        benefits = benefits.filter(
            Q(product_name__icontains=search_query) |
            Q(description__icontains=search_query)
        )

    # Paginate
    paginator = Paginator(benefits, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Form processing
    form = SupplementaryBenefitForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        benefit = form.save(commit=False)
        benefit.modified_user = request.user.email
        benefit.save()
        messages.success(request, "Supplementary Benefit saved.")
        return redirect('supplements:setup')

    return render(request, 'supplements/benefit_setup.html', {
        'form': form,
        'page_obj': page_obj,
        'schemes': schemes,
        'selected_scheme': selected_scheme or 'all',
        'search_query': search_query or ''
    })
from django.views.decorators.http import require_POST

@login_required
def edit_benefit(request, pk):
    benefit = get_object_or_404(SupplementaryBenefit, pk=pk)
    form = SupplementaryBenefitForm(request.POST or None, instance=benefit)

    if request.method == 'POST' and form.is_valid():
        benefit = form.save(commit=False)
        benefit.modified_user = request.user.email
        benefit.save()
        messages.success(request, f"{benefit.product_name} updated.")
        return redirect('supplements:setup')

    return render(request, 'supplements/benefit_form.html', {
        'form': form,
        'benefit': benefit
    })


@login_required
@require_POST
def delete_benefit(request, pk):
    benefit = get_object_or_404(SupplementaryBenefit, pk=pk)
    benefit.delete()
    messages.success(request, f"{benefit.product_name} deleted.")
    return redirect('supplements:setup')
