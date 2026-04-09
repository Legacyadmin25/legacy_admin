from datetime import date

from django import forms
from django.utils import timezone
from django.core.exceptions import ValidationError
from .models import Payment, PaymentReceipt, PaymentImport, ImportRecord

class PaymentForm(forms.ModelForm):
    coverage_month = forms.DateField(
        required=True,
        input_formats=['%Y-%m', '%Y-%m-%d'],
        widget=forms.DateInput(attrs={'type': 'month', 'class': 'form-control'})
    )

    class Meta:
        model = Payment
        fields = ['amount', 'date', 'payment_method', 'status', 'reference_number', 'notes']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'payment_method': forms.Select(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'reference_number': forms.TextInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        initial_month = timezone.now().date().replace(day=1)
        self.fields['coverage_month'].initial = self.initial.get('coverage_month', initial_month)
        self.fields['status'].initial = self.initial.get('status', 'COMPLETED')
    
    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount <= 0:
            raise ValidationError("Payment amount must be greater than zero.")
        return amount
    
    def clean_date(self):
        date = self.cleaned_data.get('date')
        if date and date > timezone.now().date():
            raise ValidationError("Payment date cannot be in the future.")
        return date

    def clean_coverage_month(self):
        coverage_month = self.cleaned_data.get('coverage_month')
        if not coverage_month:
            raise ValidationError('Select the cover month this payment must be allocated to.')
        return coverage_month.replace(day=1)

class PaymentReceiptForm(forms.ModelForm):
    class Meta:
        model = PaymentReceipt
        fields = ['receipt_number']
        widgets = {
            'receipt_number': forms.TextInput(attrs={'class': 'form-control'}),
        }
    
    def clean_receipt_number(self):
        receipt_number = self.cleaned_data.get('receipt_number')
        if PaymentReceipt.objects.filter(receipt_number=receipt_number).exists():
            raise ValidationError("This receipt number already exists. Please use a unique number.")
        return receipt_number

class PaymentFilterForm(forms.Form):
    start_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    end_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    payment_method = forms.ChoiceField(
        required=False,
        choices=[('', 'All Methods')] + Payment.PAYMENT_METHODS,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    status = forms.ChoiceField(
        required=False,
        choices=[('', 'All Statuses')] + Payment.PAYMENT_STATUS,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    min_amount = forms.DecimalField(
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'Min Amount'})
    )
    max_amount = forms.DecimalField(
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'Max Amount'})
    )
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Search by member name, ID, or reference'})
    )

class PaymentImportForm(forms.ModelForm):
    class Meta:
        model = PaymentImport
        fields = ['import_type', 'file', 'notes']
        widgets = {
            'import_type': forms.Select(attrs={'class': 'form-control'}),
            'file': forms.FileInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
    
    def clean_file(self):
        file = self.cleaned_data.get('file')
        import_type = self.cleaned_data.get('import_type')
        
        if not file:
            return file
            
        # Validate file extension based on import type
        if import_type == 'EASYPAY':
            if not (file.name.endswith('.csv') or file.name.endswith('.txt')):
                raise ValidationError("EasyPay imports must be CSV or TXT files.")
        elif import_type == 'LINKSERV':
            if not (file.name.endswith('.xlsx') or file.name.endswith('.xls')):
                raise ValidationError("Linkserv imports must be Excel files.")
                
        return file
