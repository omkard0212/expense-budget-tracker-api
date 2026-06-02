from django.db import models
from django.contrib.auth.models import AbstractUser
from departments.models import Department


class CustomUser(AbstractUser):
    ROLE_CHOICES = [
        ('Admin', 'Admin'),
        ('Manager', 'Manager'),
        ('Employee', 'Employee'),
    ]

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='Employee')
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users'
    )
    phone = models.CharField(max_length=20, blank=True)

    def __str__(self):
        return self.username
