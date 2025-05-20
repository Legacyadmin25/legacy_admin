"""
Payment detail views for viewing, updating, and deleting payments.
"""
import logging
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse
from django.contrib.auth.mixins import UserPassesTestMixin
from django.views.generic import DetailView, UpdateView, DeleteView

from .models import Payment
from .forms import PaymentForm
from .utils.policy_utils import update_policy_status

logger = logging.getLogger(__name__)

@login_required
def payment_detail(request, pk):
    """
    Show detailed information about a payment.
    """
    payment = get_object_or_404(Payment.objects.select_related('member', 'policy'), pk=pk)
    receipts = payment.receipts.all()
    
    context = {
        'payment': payment,
        'receipts': receipts,
    }
    return render(request, 'payments/payment_detail.html', context)


class PaymentUpdateView(UserPassesTestMixin, UpdateView):
    """
    Update an existing payment (restricted to admins and branch managers).
    """
    model = Payment
    form_class = PaymentForm
    template_name = 'payments/payment_form.html'
    
    def test_func(self):
        # Only allow superusers, admins, and branch managers to update payments
        return self.request.user.is_superuser or \
               self.request.user.groups.filter(name__in=['Admin', 'Branch Manager']).exists()
    
    def form_valid(self, form):
        # Log the user who updated the payment
        payment = form.save(commit=False)
        payment.updated_by = self.request.user
        payment.ip_address = self.request.META.get('REMOTE_ADDR')
        payment.save()
        
        # Update the policy status
        if payment.policy:
            update_policy_status(payment.policy)
        
        messages.success(self.request, 'Payment updated successfully.')
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse('payments:detail', kwargs={'pk': self.object.pk})


class PaymentDeleteView(UserPassesTestMixin, DeleteView):
    """
    Delete a payment (restricted to superusers only).
    """
    model = Payment
    template_name = 'payments/payment_confirm_delete.html'
    
    def test_func(self):
        # Only allow superusers to delete payments
        return self.request.user.is_superuser
    
    def delete(self, request, *args, **kwargs):
        payment = self.get_object()
        policy = payment.policy
        
        # Log the deletion
        logger.warning(f"Payment #{payment.id} deleted by {request.user} (IP: {request.META.get('REMOTE_ADDR')})")
        
        # Delete the payment
        response = super().delete(request, *args, **kwargs)
        
        # Update the policy status
        if policy:
            update_policy_status(policy)
        
        messages.success(request, 'Payment deleted successfully.')
        return response
    
    def get_success_url(self):
        return reverse('payments:payment_list')
