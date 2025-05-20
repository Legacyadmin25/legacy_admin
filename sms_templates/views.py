from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import SMSTemplate
from .forms import SMSTemplateForm

# ─── View: List + Create SMS Template ────────────────────────────────
@login_required
def sms_template(request):
    form = SMSTemplateForm(request.POST or None)
    templates = SMSTemplate.objects.order_by('name')

    if request.method == 'POST':
        if form.is_valid():
            form.save()
            messages.success(request, "Template saved.")
            return redirect('settings:sms_template')
        else:
            messages.error(request, "Please fix the errors below.")

    return render(request, 'settings_app/sms_template.html', {
        'form': form,
        'templates': templates,
    })

# ─── View: Edit SMS Template ─────────────────────────────────────────
@login_required
def sms_template_edit(request, pk):
    template = get_object_or_404(SMSTemplate, pk=pk)
    form = SMSTemplateForm(request.POST or None, instance=template)

    if request.method == 'POST':
        if form.is_valid():
            form.save()
            messages.success(request, "Template updated successfully.")
            return redirect('settings:sms_template')

    return render(request, 'settings_app/sms_template_form.html', {
        'form': form,
        'edit_mode': True,
        'template_obj': template,
    })

# ─── View: Delete SMS Template ───────────────────────────────────────
@login_required
def sms_template_delete(request, pk):
    template = get_object_or_404(SMSTemplate, pk=pk)
    if request.method == 'POST':
        template.delete()
        messages.success(request, "Template deleted.")
        return redirect('settings:sms_template')

    return render(request, 'settings_app/sms_template_confirm_delete.html', {
        'template_obj': template
    })
