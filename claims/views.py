from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from members.models import Member
from .models import Claim
from django.db.models import Q
from django.http import HttpResponse
from config.permissions import filter_by_user_scope


@login_required
def claims_home(request):
    # Check permission - only staff and claims officers
    if not (request.user.is_superuser or request.user.is_staff or 
            request.user.groups.filter(name__in=['Claims Officer', 'Administrator']).exists()):
        raise PermissionDenied("You do not have permission to view claims.")
    
    search_term = request.GET.get('search', '').strip()
    
    # Get base queryset with multi-tenancy filtering
    claims = filter_by_user_scope(Claim.objects.all(), request.user, Claim)
    
    # Only allow searching by claim ID or member name, NOT by ID number (PII)
    if search_term:
        claims = claims.filter(
            Q(member__first_name__icontains=search_term) |
            Q(member__last_name__icontains=search_term) |
            Q(id__icontains=search_term)  # Claim ID, not member ID
        )
    
    return render(request, "claims/claims_home.html", {'claims': claims, 'search_term': search_term})


@login_required
def submit_claim(request):
    # Check permission
    if not (request.user.is_superuser or request.user.is_staff or 
            request.user.groups.filter(name__in=['Claims Officer', 'Agent']).exists()):
        raise PermissionDenied("You do not have permission to submit claims.")
    
    if request.method == 'POST':
        # grab and validate the member
        member = get_object_or_404(Member, pk=request.POST.get('member'))

        # Validate amount and description
        amount = request.POST.get('amount')
        description = request.POST.get('description')
        if not amount or not description:
            # Handle error (return message to the user)
            return render(request, "claims/submit.html", {'error': "Amount and description are required."})

        # Validate file upload
        document = request.FILES.get('document')
        if document:
            # Check file size (max 20MB)
            if document.size > 20 * 1024 * 1024:
                return render(request, "claims/submit.html", {'error': "File too large. Maximum size is 20MB."})
            
            # Check file type (only PDF, DOC, DOCX allowed)
            allowed_extensions = ['pdf', 'doc', 'docx']
            file_ext = document.name.split('.')[-1].lower()
            if file_ext not in allowed_extensions:
                return render(request, "claims/submit.html", {'error': f"Invalid file type. Allowed: {', '.join(allowed_extensions)}"})

        # Build and save a new Claim instance
        claim = Claim(
            member=member,
            claim_type=request.POST.get('claim_type'),
            amount=amount,
            description=description,
            document=document
        )
        claim.save()
        return redirect('claims:status')

    # GET → show the form
    members = filter_by_user_scope(Member.objects.all(), request.user, Member)
    return render(request, "claims/submit.html", {'members': members})


@login_required
def claim_status(request):
    # Check permission
    if not (request.user.is_superuser or request.user.is_staff or 
            request.user.groups.filter(name__in=['Claims Officer', 'Agent']).exists()):
        raise PermissionDenied("You do not have permission to view claim status.")
    
    search_term = request.GET.get('search', '').strip()
    
    # Get base queryset with multi-tenancy filtering
    claims = filter_by_user_scope(Claim.objects.all(), request.user, Claim)
    
    # Only allow searching by claim ID or member name, NOT by ID number (PII)
    if search_term:
        claims = claims.filter(
            Q(member__first_name__icontains=search_term) |
            Q(member__last_name__icontains=search_term) |
            Q(id__icontains=search_term)  # Claim ID, not member ID
        )
    
    return render(request, "claims/status.html", {'claims': claims, 'search_term': search_term})
