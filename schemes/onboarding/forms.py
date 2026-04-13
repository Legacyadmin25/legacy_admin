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
