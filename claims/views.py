from django.shortcuts import render, redirect, get_object_or_404
from members.models import Member
from .models import Claim
from django.db.models import Q
from django.http import HttpResponse

def claims_home(request):
    print("claims_home view is being executed!")
    search_term = request.GET.get('search', '')
    claims = Claim.objects.filter(
        Q(member__first_name__icontains=search_term) |
        Q(member__last_name__icontains=search_term) |
        Q(id_number__icontains=search_term)
    )
    return render(request, "claims/claims_home.html", {'claims': claims})

def submit_claim(request):
    if request.method == 'POST':
        # grab and validate the member
        member = get_object_or_404(Member, pk=request.POST.get('member'))

        # Validate amount and description
        amount = request.POST.get('amount')
        description = request.POST.get('description')
        if not amount or not description:
            # Handle error (return message to the user)
            return render(request, "claims/submit.html", {'error': "Amount and description are required."})

        # Build and save a new Claim instance
        claim = Claim(
            member=member,
            claim_type=request.POST.get('claim_type'),
            amount=amount,
            description=description,
            document=request.FILES.get('document')
        )
        claim.save()
        return redirect('claims:status')

    # GET → show the form
    members = Member.objects.all()
    return render(request, "claims/submit.html", {'members': members})

def claim_status(request):
    search_term = request.GET.get('search', '')
    claims = Claim.objects.filter(
        Q(member__first_name__icontains=search_term) |
        Q(member__last_name__icontains=search_term) |
        Q(id_number__icontains=search_term)
    )
    return render(request, "claims/status.html", {'claims': claims})
