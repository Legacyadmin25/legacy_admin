from django.db import models

class SMSTemplate(models.Model):
    name = models.CharField(max_length=100, unique=True)
    message = models.TextField(max_length=160)

    def __str__(self):
        return self.name
