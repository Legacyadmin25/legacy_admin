from django import forms
from .models import Scheme

class SchemeForm(forms.ModelForm):
    class Meta:
        model = Scheme
        fields = [
            'branch', 'name', 'prefix', 'registration_no', 'fsp_number', 'logo', 'terms',
            'bank_name', 'branch_code', 'account_no', 'account_type',
            'address', 'city', 'province', 'postal_code',
            'allow_auto_policy_number', 'active',
            'phone', 'email',
        ]
        widgets = {
            'terms': forms.Textarea(attrs={'rows': 3}),
            'allow_auto_policy_number': forms.CheckboxInput(),
            'active': forms.CheckboxInput(),
        }
