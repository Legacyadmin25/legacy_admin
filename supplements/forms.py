from django import forms
from .models import SupplementaryBenefit

class SupplementaryBenefitForm(forms.ModelForm):
    class Meta:
        model = SupplementaryBenefit
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.required = False  # make all fields optional
