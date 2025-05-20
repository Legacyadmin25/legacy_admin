# reports/views.py
print("Reports views loaded")
from django.shortcuts import render
from django.http import JsonResponse
from members.models import Policy
from schemes.models import Scheme
from django.db.models import F

def validate_policy_fields(policy):
    required_fields = [
        'membership_number',
        'plan',
        'agent',
        'main_premium',
        'main_uw_premium',
        'dependents_count',
        'beneficiaries_count'
    ]
    missing_fields = []

    # Check if any of the required fields are empty or invalid
    for field in required_fields:
        value = getattr(policy, field, None)
        if value is None or (isinstance(value, str) and not value.strip()):
            missing_fields.append(field)

    return missing_fields


def full_policy_report(request):
    # Retrieve schemes for the filter dropdown
    schemes = Scheme.objects.all()

    # Initialize filter variables with default empty or all values
    filter_scheme = request.GET.get('scheme', '')
    filter_status = request.GET.get('status', '')

    # Apply filters to the policy query
    policies = Policy.objects.all()

    if filter_scheme:
        policies = policies.filter(scheme__id=filter_scheme)  # Filter policies based on the selected scheme

    if filter_status:
        if filter_status == "active":
            policies = policies.filter(is_active=True)
        elif filter_status == "lapsed":
            policies = policies.filter(is_active=False)

    # Pass the policies, schemes, and filter parameters to the template
    return render(request, 'reports/full_policy_report.html', {
        'schemes': schemes,
        'policies': policies,
        'filter_scheme': filter_scheme,
        'filter_status': filter_status,
    })

from django.shortcuts          import render
from django.db.models          import F, ExpressionWrapper, DecimalField, Value
from django.db.models.functions import Cast
from django.utils              import timezone

from members.models import Policy
from schemes.models import Scheme

def plan_fee_report(request):
    # ── 1) Load dropdown options ────────────────────────────────────────
    schemes = Scheme.objects.all()

    # ── 2) Read incoming filters ───────────────────────────────────────
    filter_scheme = request.GET.get('scheme', '')
    filter_status = request.GET.get('status', '')
    submitted     = 'generate' in request.GET    # True only when form is submitted

    # ── 3) Build base queryset & apply scheme filter ───────────────────
    policies = Policy.objects.all()
    if filter_scheme:
        schemes  = schemes.filter(id=filter_scheme)
        policies = policies.filter(scheme__id=filter_scheme)

    # ── 4) Apply “active” / “lapsed” filter via cover_date ───────────────
    today = timezone.now().date()
    if filter_status == "active":
        policies = policies.filter(cover_date__gte=today)
    elif filter_status == "lapsed":
        policies = policies.filter(cover_date__lt=today)

    # ── 5) Only once “Generate” is clicked, annotate fees ────────────────
    policy_fees = []
    if submitted:
        qs = policies.annotate(
            # cast plan.premium (FloatField) → DecimalField
            main_premium=Cast(
                F('plan__premium'),
                output_field=DecimalField(max_digits=12, decimal_places=2)
            ),
            # cast agent fixed rand commission → DecimalField
            fixed_commission=Cast(
                F('agent__commission_rand_value'),
                output_field=DecimalField(max_digits=12, decimal_places=2)
            ),
            # percentage_commission = premium * percent / 100
            percentage_commission=ExpressionWrapper(
                Cast(F('plan__premium'),
                     output_field=DecimalField(max_digits=12, decimal_places=2))
                * Cast(F('agent__commission_percentage'),
                       output_field=DecimalField(max_digits=6, decimal_places=2))
                / Value(100),
                output_field=DecimalField(max_digits=12, decimal_places=2),
            ),
            # placeholders for the other fees
            admin_fee=Value(0, output_field=DecimalField(max_digits=12, decimal_places=2)),
            cash_payout=Value(0, output_field=DecimalField(max_digits=12, decimal_places=2)),
            loyalty_programme=Value(0, output_field=DecimalField(max_digits=12, decimal_places=2)),
        )

        # now compute total_fee
        qs = qs.annotate(
            total_fee=ExpressionWrapper(
                F('fixed_commission')
                + F('percentage_commission')
                + F('admin_fee')
                + F('cash_payout')
                + F('loyalty_programme'),
                output_field=DecimalField(max_digits=14, decimal_places=2),
            )
        ).values(
            'membership_number',
            'main_premium',
            'fixed_commission',
            'percentage_commission',
            'admin_fee',
            'cash_payout',
            'loyalty_programme',
            'total_fee',
        )

        policy_fees = list(qs)

    # ── 6) Render ────────────────────────────────────────────────────────
    return render(request, 'reports/plan_fee_report.html', {
        'schemes': schemes,
        'policy_fees': policy_fees,
        'filter_scheme': filter_scheme,
        'filter_status': filter_status,
        'submitted': submitted,
    })



def generate_report(request):
    policies = Policy.objects.all()  # Get all policies for report generation
    report_data = []

    # Validate policies and only add complete ones to the report
    for policy in policies:
        missing_fields = validate_policy_fields(policy)

        if missing_fields:
            # If any fields are missing, flag the policy
            report_data.append({
                'policy_id': policy.id,
                'missing_fields': missing_fields
            })
        else:
            # Otherwise, add complete policy data to the report
            report_data.append({
                'policy_id': policy.id,
                'plan': policy.plan.name if policy.plan else 'No Plan',
                'agent': policy.agent.name if policy.agent else 'No Agent',
                'main_premium': policy.main_premium,
                'main_uw_premium': policy.main_uw_premium,
                'dependents_count': policy.dependents.count(),
                'beneficiaries_count': policy.beneficiaries.count()
            })

    return render(request, 'members/report.html', {'report_data': report_data})
