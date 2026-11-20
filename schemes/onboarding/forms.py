from decimal import Decimal

from django import forms

from .models import BranchSchemeOnboarding, SchemeProduct


class SchemeOnboardingStep1Form(forms.ModelForm):
    class Meta:
        model = BranchSchemeOnboarding
        fields = ['company_name', 'registration_no', 'fsp_number', 'email', 'phone']


class SchemeOnboardingStep2Form(forms.ModelForm):
    class Meta:
        model = BranchSchemeOnboarding
        fields = ['bank_account_no', 'debit_order_no', 'account_type']


class BranchOnboardingReviewForm(forms.Form):
    ACTION_APPROVE = 'approve'
    ACTION_REOPEN = 'reopen'

    action = forms.ChoiceField(
        choices=[(ACTION_APPROVE, 'Approve'), (ACTION_REOPEN, 'Reopen for corrections')]
    )
    notes = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows': 3}))

    def clean(self):
        cleaned = super().clean()
        action = cleaned.get('action')
        notes = (cleaned.get('notes') or '').strip()
        if action == self.ACTION_REOPEN and not notes:
            self.add_error('notes', 'Notes are required when reopening for corrections.')
        return cleaned


class SchemeProductForm(forms.ModelForm):
    """
    Used by the scheme owner in the product builder.
    wholesale_plan choices are injected at instantiation time (branch-scoped).
    """

    class Meta:
        model = SchemeProduct
        fields = ['wholesale_plan', 'product_name', 'product_description',
                  'retail_premium', 'client_cover_amount', 'policy_type']
        widgets = {
            'product_description': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, wholesale_qs=None, **kwargs):
        super().__init__(*args, **kwargs)
        if wholesale_qs is not None:
            self.fields['wholesale_plan'].queryset = wholesale_qs
        self.fields['wholesale_plan'].label = 'Base wholesale plan'
        self.fields['retail_premium'].label = 'Your retail premium (R)'
        self.fields['client_cover_amount'].label = 'Client-facing cover amount (R)'

    def clean(self):
        cleaned = super().clean()
        retail = cleaned.get('retail_premium')
        plan = cleaned.get('wholesale_plan')
        if retail is not None and plan is not None:
            if retail < plan.premium:
                # Warn but do NOT block — branch owner sees the flag on review
                self.add_warning = True  # template reads this to show yellow banner
        return cleaned


class BulkProductImportForm(forms.Form):
    """
    Form for branch owners to bulk import SchemeProducts from CSV/XLSX.
    File format: 
      wholesale_plan_id | product_name | product_description | retail_premium | client_cover_amount | policy_type
    """
    import_file = forms.FileField(
        label='CSV or Excel file',
        help_text='Upload a .csv or .xlsx file with product data. See template for format.',
        widget=forms.FileInput(attrs={
            'accept': '.csv,.xlsx,.xls',
            'class': 'form-control-file',
        })
    )

    def clean_import_file(self):
        f = self.cleaned_data.get('import_file')
        if f:
            # Check file extension
            name = f.name.lower()
            if not (name.endswith('.csv') or name.endswith('.xlsx') or name.endswith('.xls')):
                raise forms.ValidationError('Only CSV and Excel (.xlsx, .xls) files are allowed.')
            # Check file size (max 5MB)
            if f.size > 5 * 1024 * 1024:
                raise forms.ValidationError('File size must not exceed 5 MB.')
        return f

