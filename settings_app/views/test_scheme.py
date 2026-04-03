from django.shortcuts import render, redirect
from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic import CreateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from schemes.models import Scheme
from settings_app.forms import SchemeForm

class TestSchemeCreateView(LoginRequiredMixin, CreateView):
    model = Scheme
    form_class = SchemeForm
    template_name = 'settings_app/scheme_setup.html'
    success_url = reverse_lazy('settings:scheme')

    def form_valid(self, form):
        # Print form data for debugging
        print("Form is valid!")
        print(f"Form data: {form.cleaned_data}")
        
        # Save the form
        self.object = form.save()
        
        messages.success(self.request, "Scheme created successfully!")
        return redirect(self.success_url)
        
    def form_invalid(self, form):
        # Print form errors for debugging
        print("Form is invalid!")
        print(f"Form errors: {form.errors}")
        return super().form_invalid(form)

class TestSchemeUpdateView(LoginRequiredMixin, UpdateView):
    model = Scheme
    form_class = SchemeForm
    template_name = 'settings_app/scheme_setup.html'
    success_url = reverse_lazy('settings:scheme')

    def form_valid(self, form):
        # Print form data for debugging
        print("Form is valid!")
        print(f"Form data: {form.cleaned_data}")
        
        # Save the form
        self.object = form.save()
        
        messages.success(self.request, "Scheme updated successfully!")
        return redirect(self.success_url)
        
    def form_invalid(self, form):
        # Print form errors for debugging
        print("Form is invalid!")
        print(f"Form errors: {form.errors}")
        return super().form_invalid(form)
