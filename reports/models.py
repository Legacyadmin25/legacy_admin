from django.db import models

class Report(models.Model):
    """
    A model to represent generated reports for the dashboard.
    """
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    data = models.JSONField(blank=True, null=True)

    def __str__(self):
        return self.title
