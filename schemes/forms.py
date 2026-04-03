from django import forms
from .models import Scheme
from branches.models import Bank

class SchemeForm(forms.ModelForm):
    class Meta:
        model = Scheme
        fields = [
            'branch', 'name', 'prefix', 'registration_no', 'fsp_number', 'logo', 'terms',
            'bank', 'branch_code', 'account_no', 'account_type',
            'address', 'city', 'province', 'postal_code',
            'allow_auto_policy_number', 'active',
            'phone', 'email',
        ]
        widgets = {
            'terms': forms.Textarea(attrs={'rows': 3, 'class': 'w-full px-4 py-2 border rounded'}),
            'allow_auto_policy_number': forms.CheckboxInput(attrs={'class': 'form-checkbox h-5 w-5 text-blue-600'}),
            'active': forms.CheckboxInput(attrs={'class': 'form-checkbox h-5 w-5 text-blue-600'}),
            'bank': forms.Select(attrs={'class': 'w-full px-4 py-2 border rounded bank-select'}),
            'branch_code': forms.TextInput(attrs={'class': 'w-full px-4 py-2 border rounded bg-gray-100', 'readonly': True}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Get all banks ordered by name
        self.fields['bank'].queryset = Bank.objects.all().order_by('name')
        
        # Set initial values
        if self.instance:
            # If bank is not set but bank_name exists, try to find a matching bank
            if not self.instance.bank and hasattr(self.instance, 'bank_name') and self.instance.bank_name:
                try:
                    bank = Bank.objects.filter(name__iexact=self.instance.bank_name).first()
                    if bank:
                        self.instance.bank = bank
                        self.initial['bank'] = bank.id
                        self.initial['branch_code'] = bank.branch_code
                except Exception as e:
                    print(f"Error setting initial bank: {e}")
            
            # Set branch code from bank if available
            if self.instance.bank:
                self.initial['branch_code'] = self.instance.bank.branch_code
    
    def clean(self):
        cleaned_data = super().clean()
        bank = cleaned_data.get('bank')
        
        # Update branch code when bank is selected
        if bank:
            cleaned_data['branch_code'] = bank.branch_code
        
        return cleaned_data
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Ensure branch_code is set from bank
        if instance.bank:
            instance.branch_code = instance.bank.branch_code
        
        if commit:
            instance.save()
        
        return instance
