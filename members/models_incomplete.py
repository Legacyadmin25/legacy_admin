from django.conf import settings
from django.db import models
from django.utils import timezone
import uuid

class IncompleteApplication(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('in_progress', 'In Progress'),
        ('abandoned', 'Abandoned'),
    ]
    
    token = models.UUIDField(unique=True, default=uuid.uuid4, editable=False)
    agent = models.ForeignKey('settings_app.Agent', on_delete=models.SET_NULL, null=True, blank=True)
    scheme = models.ForeignKey('schemes.Scheme', on_delete=models.SET_NULL, null=True, blank=True)
    branch = models.ForeignKey('branches.Branch', on_delete=models.SET_NULL, null=True, blank=True)
    current_step = models.PositiveSmallIntegerField(default=1)
    form_data = models.JSONField(default=dict)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_activity = models.DateTimeField(default=timezone.now)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    session_key = models.CharField(max_length=40, blank=True, null=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        ordering = ['-updated_at']
        verbose_name = 'Incomplete Application'
        verbose_name_plural = 'Incomplete Applications'
        indexes = [
            models.Index(fields=['token']),
            models.Index(fields=['status']),
            models.Index(fields=['agent']),
            models.Index(fields=['created_at']),
            models.Index(fields=['session_key']),
        ]

    def __str__(self):
        return f"Application {self.token} - {self.get_status_display()}"

    def update_activity(self):
        """Update last activity timestamp"""
        self.last_activity = timezone.now()
        self.save(update_fields=['last_activity'])

    def save_step_data(self, step, form_data):
        """Save form data for a specific step"""
        current_data = self.form_data or {}
        current_data[f'step_{step}'] = form_data
        self.form_data = current_data
        self.current_step = step
        self.status = 'in_progress'
        self.last_activity = timezone.now()
        self.save()

    def get_step_data(self, step=None):
        """Get data for a specific step or all data"""
        if step:
            return self.form_data.get(f'step_{step}', {})
        return self.form_data

    def get_resume_url(self):
        """Get URL to resume this application"""
        from django.urls import reverse
        return reverse('members:diy_resume_application', kwargs={'token': self.token})
        
    def mark_abandoned(self):
        """Mark application as abandoned"""
        self.status = 'abandoned'
        self.save(update_fields=['status'])
        
    def mark_completed(self):
        """Mark application as completed"""
        self.status = 'completed'
        self.save(update_fields=['status'])
