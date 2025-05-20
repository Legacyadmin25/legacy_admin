from django import forms
from schemes.models import Scheme

POLICY_STATUS_CHOICES = (
    ('active', 'Active'),
    ('lapsed', 'Lapsed'),
)

class ReportFilterForm(forms.Form):
    scheme = forms.ModelChoiceField(queryset=Scheme.objects.all(), required=True)
    status = forms.ChoiceField(choices=POLICY_STATUS_CHOICES, required=False)
