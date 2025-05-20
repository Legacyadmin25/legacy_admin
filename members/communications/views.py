from django.shortcuts import render, redirect
from django.contrib import messages
from .forms import SmsForm

def sms_sending(request):
    form = SmsForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        # Example: Extract data
        cellphone = form.cleaned_data['cellphone']
        message = form.cleaned_data['message']
        # TODO: handle sending logic here

        messages.success(request, f'SMS sent to {cellphone}')
        return redirect('messaging:sms_sending')

    return render(request, 'messaging/sms_sending.html', {'form': form})
