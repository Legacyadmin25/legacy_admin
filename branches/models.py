from django.db import models

class Bank(models.Model):
    name = models.CharField(max_length=255)
    branch_code = models.CharField(max_length=10)

    def __str__(self):
        return self.name


class Branch(models.Model):
    name = models.CharField(max_length=255)
    location = models.CharField(max_length=255, blank=True, null=True)  # Location of the branch
    bank = models.ForeignKey('Bank', on_delete=models.CASCADE, related_name='branches')  # Link to Bank
    code = models.CharField(max_length=100, blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    cell = models.CharField(max_length=20, blank=True, null=True)
    physical_address = models.CharField(max_length=255, blank=True, null=True)
    street = models.CharField(max_length=255, blank=True, null=True)
    town = models.CharField(max_length=100, blank=True, null=True)
    PROVINCE_CHOICES = [
        ('EC', 'Eastern Cape'),
        ('FS', 'Free State'),
        ('GP', 'Gauteng'),
        ('KZN', 'KwaZulu-Natal'),
        ('LP', 'Limpopo'),
        ('MP', 'Mpumalanga'),
        ('NC', 'Northern Cape'),
        ('NW', 'North West'),
        ('WC', 'Western Cape'),
    ]
    province = models.CharField(max_length=100, choices=PROVINCE_CHOICES, blank=True, null=True)
    account_no = models.CharField(max_length=50, blank=True, null=True)
    region = models.CharField(max_length=100, blank=True, null=True)
    postal_code = models.CharField(max_length=10, blank=True, null=True)
    modified_user = models.CharField(max_length=255, blank=True, null=True)
    modified_date = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
