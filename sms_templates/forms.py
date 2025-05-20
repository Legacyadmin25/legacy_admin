from django import forms
from .models import SMSTemplate

class SMSTemplateForm(forms.ModelForm):
    class Meta:
        model = SMSTemplate
        fields = ['name', 'message']
