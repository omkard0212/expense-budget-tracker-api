from django.db import models
from django.conf import settings
from departments.models import Department


class Expense(models.Model):
    CATEGORY_CHOICES = [
        ('Travel', 'Travel'),
        ('Food', 'Food'),
        ('Office Supplies', 'Office Supplies'),
        ('Other', 'Other'),
    ]

    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected'),
    ]

    title = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='expenses'
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        related_name='expenses'
    )
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title
