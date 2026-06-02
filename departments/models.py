from django.db import models


class Department(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    budget_limit = models.DecimalField(max_digits=12, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
