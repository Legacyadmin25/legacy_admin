from django import forms
from .models import Branch

class BranchForm(forms.ModelForm):
    class Meta:
        model = Branch
        fields = [
            'name', 'code', 'phone', 'cell',
            'physical_address', 'street', 'town',
            'province', 'region', 'postal_code',
            'bank', 'account_no',
        ]
