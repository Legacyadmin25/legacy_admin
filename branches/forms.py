from django import forms
from .models import Branch, Bank

class BranchForm(forms.ModelForm):
    bank = forms.ModelChoiceField(
        queryset=Bank.objects.all(),
        required=True,
        widget=forms.Select(attrs={
            'class': 'hidden',
            'id': 'bank_id_field'
        })
    )
    
    class Meta:
        model = Branch
        fields = [
            'name', 'code', 'phone', 'cell',
            'physical_address', 'street', 'town',
            'province', 'region', 'postal_code',
            'bank', 'account_no',
        ]
        widgets = {
            'code': forms.TextInput(attrs={'readonly': 'readonly'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set the initial bank value if instance exists
        if self.instance and self.instance.pk and self.instance.bank:
            self.fields['bank'].initial = self.instance.bank
