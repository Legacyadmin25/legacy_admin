from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.conf import settings
import json

User = get_user_model()

class ReportQuery(models.Model):
    """Stores the original user query and AI-parsed parameters"""
    REPORT_TYPES = [
        ('claims', 'Claims Report'),
        ('commissions', 'Commissions Report'),
        ('lapses', 'Policy Lapses Report'),
        ('payments', 'Payments Report'),
        ('debit_orders', 'Debit Order Report'),
    ]
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='report_queries'
    )
    original_query = models.TextField(help_text="The original user query")
    report_type = models.CharField(max_length=50, choices=REPORT_TYPES)
    filters = models.JSONField(default=dict, help_text="JSON structure with filter parameters")
    created_at = models.DateTimeField(auto_now_add=True)
    is_favorite = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Report Query'
        verbose_name_plural = 'Report Queries'
    
    def __str__(self):
        return f"{self.get_report_type_display()} - {self.user.email}"
    
    def save(self, *args, **kwargs):
        # Ensure filters is always a dictionary
        if not isinstance(self.filters, dict):
            self.filters = {}
        super().save(*args, **kwargs)


class ReportExecutionLog(models.Model):
    """Tracks each execution of a report"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('success', 'Success'),
        ('error', 'Error'),
    ]
    
    report_query = models.ForeignKey(
        ReportQuery,
        on_delete=models.CASCADE,
        related_name='executions'
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    executed_at = models.DateTimeField(auto_now_add=True)
    execution_time = models.FloatField(help_text="Execution time in seconds", null=True, blank=True)
    record_count = models.PositiveIntegerField(default=0)
    error_message = models.TextField(blank=True, null=True)
    
    class Meta:
        ordering = ['-executed_at']
        verbose_name = 'Report Execution Log'
        verbose_name_plural = 'Report Execution Logs'
    
    def __str__(self):
        return f"{self.report_query} - {self.get_status_display()}"


class SavedReport(models.Model):
    """Stores saved/favorited reports for quick access"""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='saved_reports'
    )
    name = models.CharField(max_length=255)
    report_query = models.ForeignKey(
        ReportQuery,
        on_delete=models.CASCADE,
        related_name='saved_instances'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    last_accessed = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-last_accessed']
        verbose_name = 'Saved Report'
        verbose_name_plural = 'Saved Reports'
    
    def __str__(self):
        return f"{self.name} - {self.user.email}"
