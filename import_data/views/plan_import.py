# import_data/views/plan_import.py
"""
Bulk Plan Import — reads the 2-sheet XLSX format used by Net Christal and similar.

Sheet 1  "Plan Setup"    → creates/updates Plan objects
Sheet 2  "Plan Creator"  → creates/replaces PlanTier rows (Spouse, Child, Extended)
"""

from decimal import Decimal, InvalidOperation

import openpyxl
from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.decorators import method_decorator
from django.views import View

from schemes.models import Plan, PlanTier, Scheme


# ──────────────────────────────────────────────────────────────────────────────
# Form
# ──────────────────────────────────────────────────────────────────────────────

class PlanImportForm(forms.Form):
    scheme = forms.ModelChoiceField(
        queryset=Scheme.objects.filter(active=True).order_by('name'),
        label='Target Scheme',
        help_text='Plans will be imported into this scheme.',
        widget=forms.Select(attrs={'class': 'w-full border rounded px-3 py-2'}),
    )
    import_file = forms.FileField(
        label='Import file (.xlsx)',
        help_text='Upload the 2-sheet XLSX. Sheet 1 = Plan Setup, Sheet 2 = Plan Creator.',
        widget=forms.FileInput(attrs={
            'accept': '.xlsx,.xls',
            'class': 'block w-full text-sm',
        }),
    )
    is_wholesale = forms.BooleanField(
        required=False,
        initial=True,
        label='Mark plans as Wholesale',
        help_text='Tick if these are underwriter/wholesale plans available for scheme owners to base products on.',
        widget=forms.CheckboxInput(attrs={'class': 'form-checkbox h-5 w-5 text-blue-600'}),
    )
    update_existing = forms.BooleanField(
        required=False,
        initial=False,
        label='Update existing plans (match on Plan Name + Scheme)',
        widget=forms.CheckboxInput(attrs={'class': 'form-checkbox h-5 w-5 text-blue-600'}),
    )

    def clean_import_file(self):
        f = self.cleaned_data.get('import_file')
        if f:
            name = f.name.lower()
            if not (name.endswith('.xlsx') or name.endswith('.xls')):
                raise forms.ValidationError('Only Excel files (.xlsx / .xls) are supported.')
            if f.size > 10 * 1024 * 1024:
                raise forms.ValidationError('File size must not exceed 10 MB.')
        return f

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user and not user.is_superuser:
            # Scope schemes to the user's branch
            branch = getattr(user, 'branch', None)
            if branch:
                self.fields['scheme'].queryset = Scheme.objects.filter(
                    active=True, branch=branch
                ).order_by('name')


# ──────────────────────────────────────────────────────────────────────────────
# Parser
# ──────────────────────────────────────────────────────────────────────────────

# Column index maps (0-based) for "Plan Setup" sheet
_PLAN_SETUP_COLS = {
    'plan_name':        0,
    'description':      1,
    'main_premium':     2,
    'main_cover':       3,
    'main_uw_premium':  4,
    'main_uw_cover':    5,
    'main_age_from':    6,
    'main_age_to':      7,
    'waiting_period':   8,
    'lapse_period':     9,
    # col 10 = Maximum Dependents (informational, skip)
    'underwriter':      11,
    # cols 12-15 = calculated totals (skip)
    'admin_fee':        16,
    'agent_commission': 17,
    'scheme_fee':       18,
    'manager_fee':      19,
    'office_fee':       20,
    'loyalty_programme':21,
    'other_fees':       22,
    'cash_payout':      23,
    'service_fee':      24,
    'penalty_fee':      25,
}

# Column index maps (0-based) for "Plan Creator" sheet
_TIER_COLS = {
    'plan_name':    0,
    'user_type':    1,
    'age_from':     2,
    'age_to':       3,
    'cover_amount': 4,
    'premium':      5,
    'uw_cover':     6,
    'uw_premium':   7,
    'admin_fee':    8,
}

_USER_TYPE_MAP = {
    'spouse':   'spouse',
    'child':    'child',
    'extended': 'extended',
}


class ParseError:
    def __init__(self, sheet, row, field, message):
        self.sheet = sheet
        self.row = row
        self.field = field
        self.message = message

    def __str__(self):
        return f'[{self.sheet}] Row {self.row} ({self.field}): {self.message}'


def _to_decimal(value, default=Decimal('0')):
    if value is None or value == '':
        return default
    try:
        return Decimal(str(value)).quantize(Decimal('0.0001'))
    except InvalidOperation:
        raise ValueError(f'"{value}" is not a valid number')


def _to_int(value, default=0):
    if value is None or value == '':
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        raise ValueError(f'"{value}" is not a valid integer')


def parse_plan_import_file(file_obj):
    """
    Parse the 2-sheet XLSX and return:
      {
        'plans':  [ {field: value, ...}, ... ],  ← from Plan Setup
        'tiers':  [ {plan_name, user_type, ...}, ... ],  ← from Plan Creator
        'errors': [ ParseError, ... ],
      }
    Returns immediately on fatal file-read errors.
    """
    errors = []
    plans = []
    tiers = []

    try:
        wb = openpyxl.load_workbook(file_obj, data_only=True)
    except Exception as exc:
        return {'plans': [], 'tiers': [], 'errors': [
            ParseError('file', 0, 'file', f'Cannot read Excel file: {exc}')
        ]}

    # ── Sheet 1: Plan Setup ──────────────────────────────────────────────────
    if 'Plan Setup' not in wb.sheetnames:
        errors.append(ParseError('Plan Setup', 0, 'sheet', 'Sheet "Plan Setup" not found'))
    else:
        ws = wb['Plan Setup']
        for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
            plan_name = (row[_PLAN_SETUP_COLS['plan_name']] or '').strip() if row[_PLAN_SETUP_COLS['plan_name']] else ''
            if not plan_name:
                continue  # blank row

            row_errors = []

            def _get_dec(col_key):
                try:
                    return _to_decimal(row[_PLAN_SETUP_COLS[col_key]])
                except ValueError as e:
                    row_errors.append(ParseError('Plan Setup', row_idx, col_key, str(e)))
                    return Decimal('0')

            def _get_int(col_key):
                try:
                    return _to_int(row[_PLAN_SETUP_COLS[col_key]])
                except ValueError as e:
                    row_errors.append(ParseError('Plan Setup', row_idx, col_key, str(e)))
                    return 0

            plan_data = {
                'plan_name':         plan_name,
                'description':       str(row[_PLAN_SETUP_COLS['description']] or '').strip(),
                'main_premium':      _get_dec('main_premium'),
                'main_cover':        _get_dec('main_cover'),
                'main_uw_premium':   _get_dec('main_uw_premium'),
                'main_uw_cover':     _get_dec('main_uw_cover'),
                'main_age_from':     _get_int('main_age_from'),
                'main_age_to':       _get_int('main_age_to'),
                'waiting_period':    _get_int('waiting_period'),
                'lapse_period':      _get_int('lapse_period'),
                'underwriter':       str(row[_PLAN_SETUP_COLS['underwriter']] or '').strip(),
                'admin_fee':         _get_dec('admin_fee'),
                'agent_commission':  _get_dec('agent_commission'),
                'scheme_fee':        _get_dec('scheme_fee'),
                'manager_fee':       _get_dec('manager_fee'),
                'office_fee':        _get_dec('office_fee'),
                'loyalty_programme': _get_dec('loyalty_programme'),
                'other_fees':        _get_dec('other_fees'),
                'cash_payout':       _get_dec('cash_payout'),
                'service_fee':       _get_dec('service_fee'),
                'penalty_fee':       _get_dec('penalty_fee'),
            }
            errors.extend(row_errors)
            if not row_errors:
                plans.append(plan_data)

    # ── Sheet 2: Plan Creator ────────────────────────────────────────────────
    if 'Plan Creator' not in wb.sheetnames:
        errors.append(ParseError('Plan Creator', 0, 'sheet', 'Sheet "Plan Creator" not found'))
    else:
        ws2 = wb['Plan Creator']
        for row_idx, row in enumerate(ws2.iter_rows(min_row=2, values_only=True), start=2):
            plan_name = (row[_TIER_COLS['plan_name']] or '').strip() if row[_TIER_COLS['plan_name']] else ''
            user_type_raw = str(row[_TIER_COLS['user_type']] or '').strip().lower()
            if not plan_name and not user_type_raw:
                continue  # blank row

            row_errors = []

            if not plan_name:
                errors.append(ParseError('Plan Creator', row_idx, 'plan_name', 'Plan Name is required'))
                continue

            user_type = _USER_TYPE_MAP.get(user_type_raw)
            if not user_type:
                errors.append(ParseError('Plan Creator', row_idx, 'user_type',
                                         f'Unknown user type "{user_type_raw}". Must be Spouse, Child, or Extended'))
                continue

            def _tdec(col_key):
                try:
                    return _to_decimal(row[_TIER_COLS[col_key]])
                except ValueError as e:
                    row_errors.append(ParseError('Plan Creator', row_idx, col_key, str(e)))
                    return Decimal('0')

            def _tint(col_key):
                try:
                    return _to_int(row[_TIER_COLS[col_key]])
                except ValueError as e:
                    row_errors.append(ParseError('Plan Creator', row_idx, col_key, str(e)))
                    return 0

            tier_data = {
                'plan_name':    plan_name,
                'user_type':    user_type,
                'age_from':     _tint('age_from'),
                'age_to':       _tint('age_to'),
                'cover_amount': _tdec('cover_amount'),
                'premium':      _tdec('premium'),
                'uw_cover':     _tdec('uw_cover'),
                'uw_premium':   _tdec('uw_premium'),
                'admin_fee':    _tdec('admin_fee'),
            }
            errors.extend(row_errors)
            if not row_errors:
                tiers.append(tier_data)

    return {'plans': plans, 'tiers': tiers, 'errors': errors}


# ──────────────────────────────────────────────────────────────────────────────
# Views
# ──────────────────────────────────────────────────────────────────────────────

@method_decorator(login_required, name='dispatch')
class PlanImportUploadView(View):
    template_name = 'import_data/plan_import.html'

    def get(self, request):
        form = PlanImportForm(user=request.user)
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = PlanImportForm(request.POST, request.FILES, user=request.user)
        if not form.is_valid():
            return render(request, self.template_name, {'form': form})

        file_obj = form.cleaned_data['import_file']
        scheme = form.cleaned_data['scheme']
        is_wholesale = form.cleaned_data['is_wholesale']
        update_existing = form.cleaned_data['update_existing']

        parsed = parse_plan_import_file(file_obj)

        if not parsed['plans'] and parsed['errors']:
            for err in parsed['errors']:
                messages.error(request, str(err))
            return render(request, self.template_name, {'form': form})

        # Store preview data in session
        request.session['plan_import_preview'] = {
            'scheme_id':       scheme.pk,
            'scheme_name':     str(scheme),
            'is_wholesale':    is_wholesale,
            'update_existing': update_existing,
            'plans': [
                {k: str(v) for k, v in p.items()} for p in parsed['plans']
            ],
            'tiers': [
                {k: str(v) for k, v in t.items()} for t in parsed['tiers']
            ],
            'errors': [str(e) for e in parsed['errors']],
        }

        return redirect('import_data:plan_import_preview')


@method_decorator(login_required, name='dispatch')
class PlanImportPreviewView(View):
    template_name = 'import_data/plan_import_preview.html'

    def get(self, request):
        data = request.session.get('plan_import_preview')
        if not data:
            messages.warning(request, 'No import data found. Please upload a file first.')
            return redirect('import_data:plan_import_upload')
        return render(request, self.template_name, {'data': data})

    def post(self, request):
        data = request.session.get('plan_import_preview')
        if not data:
            messages.warning(request, 'Session expired. Please upload again.')
            return redirect('import_data:plan_import_upload')

        scheme = get_object_or_404(Scheme, pk=data['scheme_id'])
        is_wholesale = data['is_wholesale']
        update_existing = data['update_existing']

        created_count = 0
        updated_count = 0
        tier_count = 0

        try:
            with transaction.atomic():
                # Build a name → Plan map for tiers to reference
                plan_map = {}

                for pd in data['plans']:
                    defaults = dict(
                        description=pd['description'],
                        main_premium=Decimal(pd['main_premium']),
                        main_cover=Decimal(pd['main_cover']),
                        main_uw_premium=Decimal(pd['main_uw_premium']),
                        main_uw_cover=Decimal(pd['main_uw_cover']),
                        main_age_from=int(pd['main_age_from']),
                        main_age_to=int(pd['main_age_to']),
                        waiting_period=int(pd['waiting_period']),
                        lapse_period=int(pd['lapse_period']),
                        underwriter=pd['underwriter'],
                        admin_fee=Decimal(pd['admin_fee']),
                        agent_commission=Decimal(pd['agent_commission']),
                        scheme_fee=Decimal(pd['scheme_fee']),
                        manager_fee=Decimal(pd['manager_fee']),
                        office_fee=Decimal(pd['office_fee']),
                        loyalty_programme=Decimal(pd['loyalty_programme']),
                        other_fees=Decimal(pd['other_fees']),
                        cash_payout=Decimal(pd['cash_payout']),
                        service_fee=Decimal(pd['service_fee']),
                        penalty_fee=Decimal(pd['penalty_fee']),
                        # premium = main_premium (the retail-facing total)
                        premium=Decimal(pd['main_premium']),
                        is_wholesale=is_wholesale,
                        scheme=scheme,
                    )

                    if update_existing:
                        plan_obj, created = Plan.objects.update_or_create(
                            name=pd['plan_name'], scheme=scheme, defaults=defaults
                        )
                        if created:
                            created_count += 1
                        else:
                            updated_count += 1
                    else:
                        plan_obj, created = Plan.objects.get_or_create(
                            name=pd['plan_name'], scheme=scheme, defaults=defaults
                        )
                        if created:
                            created_count += 1

                    plan_map[pd['plan_name']] = plan_obj

                # ── Create Tiers ──────────────────────────────────────────────
                for td in data['tiers']:
                    plan_obj = plan_map.get(td['plan_name'])
                    if not plan_obj:
                        # Try to find an existing plan by name in this scheme
                        try:
                            plan_obj = Plan.objects.get(name=td['plan_name'], scheme=scheme)
                        except Plan.DoesNotExist:
                            continue  # Skip tiers for plans not in this import

                    PlanTier.objects.update_or_create(
                        plan=plan_obj,
                        user_type=td['user_type'],
                        age_from=int(td['age_from']),
                        age_to=int(td['age_to']),
                        defaults=dict(
                            cover_amount=Decimal(td['cover_amount']),
                            premium_amount=Decimal(td['premium']),
                            uw_cover=Decimal(td['uw_cover']),
                            uw_premium=Decimal(td['uw_premium']),
                            tier_admin_fee=Decimal(td['admin_fee']),
                        ),
                    )
                    tier_count += 1

        except Exception as exc:
            messages.error(request, f'Import failed: {exc}')
            return redirect('import_data:plan_import_preview')

        # Clear session
        request.session.pop('plan_import_preview', None)

        messages.success(
            request,
            f'Import complete — {created_count} plan(s) created, {updated_count} updated, '
            f'{tier_count} tier row(s) saved.'
        )
        return redirect('import_data:plan_import_upload')
