from django import forms

from .models import BranchSchemeOnboarding


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
