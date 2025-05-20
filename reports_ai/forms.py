from django import forms
from django.forms import ModelForm, Textarea, TextInput
from .models import ReportQuery, SavedReport


class ReportQueryForm(forms.ModelForm):
    """Form for submitting a report query"""
    class Meta:
        model = ReportQuery
        fields = ['original_query']
        widgets = {
            'original_query': TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'E.g., Show me commissions for agents in March 2024',
                'autocomplete': 'off',
            })
        }
        labels = {
            'original_query': 'Describe the report you need'
        }


class SaveReportForm(forms.ModelForm):
    """Form for saving a report"""
    class Meta:
        model = SavedReport
        fields = ['name']
        widgets = {
            'name': TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'E.g., March 2024 Commissions',
                'autocomplete': 'off',
            })
        }
        labels = {
            'name': 'Report Name'
        }
    
    def clean_name(self):
        """Ensure report name is unique for the user"""
        name = self.cleaned_data.get('name')
        if not name:
            raise forms.ValidationError("Please enter a name for the report.")
        
        # Check if a report with this name already exists for the user
        if hasattr(self, 'user') and self.user.is_authenticated:
            if SavedReport.objects.filter(user=self.user, name__iexact=name).exists():
                raise forms.ValidationError("You already have a saved report with this name.")
        
        return name


class ReportFilterForm(forms.Form):
    """Form for filtering reports"""
    REPORT_TYPES = [
        ('', 'All Report Types'),
        ('claims', 'Claims Report'),
        ('commissions', 'Commissions Report'),
        ('lapses', 'Policy Lapses Report'),
        ('payments', 'Payments Report'),
        ('debit_orders', 'Debit Order Report'),
    ]
    
    DATE_RANGES = [
        ('', 'All Time'),
        ('today', 'Today'),
        ('yesterday', 'Yesterday'),
        ('this_week', 'This Week'),
        ('last_week', 'Last Week'),
        ('this_month', 'This Month'),
        ('last_month', 'Last Month'),
        ('this_year', 'This Year'),
        ('last_year', 'Last Year'),
        ('custom', 'Custom Range'),
    ]
    
    report_type = forms.ChoiceField(
        choices=REPORT_TYPES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Report Type'
    )
    
    date_range = forms.ChoiceField(
        choices=DATE_RANGES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Date Range'
    )
    
    start_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        label='From'
    )
    
    end_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        label='To'
    )
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search reports...',
        }),
        label='Search'
    )
    
    def clean(self):
        cleaned_data = super().clean()
        date_range = cleaned_data.get('date_range')
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        if date_range == 'custom' and (not start_date or not end_date):
            raise forms.ValidationError("Please select both start and end dates for custom range.")
        
        if start_date and end_date and start_date > end_date:
            raise forms.ValidationError("Start date must be before end date.")
        
        return cleaned_data
