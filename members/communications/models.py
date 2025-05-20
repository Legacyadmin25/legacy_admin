from django.db import models
from django.utils import timezone


class SMSLog(models.Model):
    phone_number = models.CharField(max_length=20)
    message      = models.TextField()
    status       = models.CharField(max_length=20)       # e.g. "SENT" or "FAILED"
    detail       = models.TextField(blank=True)           # provider response or error detail
    sent_at      = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"SMS to {self.phone_number} at {self.sent_at:%Y-%m-%d %H:%M}"


class EmailLog(models.Model):
    to           = models.EmailField()
    subject      = models.CharField(max_length=255)
    body         = models.TextField()
    status       = models.CharField(max_length=20)       # e.g. "SENT" or "FAILED"
    error        = models.TextField(blank=True)           # any exception message
    sent_at      = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Email to {self.to} at {self.sent_at:%Y-%m-%d %H:%M}"


class WhatsAppLog(models.Model):
    phone_number = models.CharField(max_length=20)
    message      = models.TextField()
    status       = models.CharField(max_length=20)       # e.g. "SENT" or "FAILED"
    error        = models.TextField(blank=True)
    sent_at      = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"WhatsApp to {self.phone_number} at {self.sent_at:%Y-%m-%d %H:%M}"
