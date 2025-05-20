from django import forms

class SmsForm(forms.Form):
    cellphone = forms.CharField(label='TO Cellphone Number', max_length=20)
    message = forms.CharField(widget=forms.Textarea(attrs={'rows': 5}), label='Message Text')
    all_members = forms.BooleanField(required=False)
    active_members = forms.BooleanField(required=False)
    trial_members = forms.BooleanField(required=False)
    lapsed_members = forms.BooleanField(required=False)
