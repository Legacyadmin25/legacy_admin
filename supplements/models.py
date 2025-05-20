from django.db import models
from schemes.models import Scheme

class SupplementaryBenefit(models.Model):
    product_name = models.CharField(max_length=255, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    premium = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    underwriter_premium = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    cover = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    scheme = models.ForeignKey(Scheme, on_delete=models.SET_NULL, blank=True, null=True)
    is_ongoing = models.BooleanField(default=False)
    is_laybye = models.BooleanField(default=False)
    modified_user = models.EmailField(null=True, blank=True)
    modified_date = models.DateField(auto_now=True)

    def __str__(self):
        return self.product_name or "Unnamed Benefit"
