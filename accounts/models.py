"""
accounts/models.py — Custom User model (shared across all tenants)
Lives in the public schema.
"""
import uuid
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Extended User with uid, phone, role, and Expo push token.
    This model lives in the PUBLIC schema (shared by all tenants).
    """
    ROLE_CHOICES = [('customer', 'Customer'), ('owner', 'Owner')]

    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, db_index=True)
    # email must be unique because it is used as USERNAME_FIELD
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=15, blank=True)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='customer')

    # Expo push token — stored per user for notifications
    expo_push_token = models.CharField(max_length=200, blank=True)

    # Track which tenant zone this user belongs to
    tenant_schema = models.CharField(max_length=100, blank=True,
        help_text="Schema name of the primary tenant this user operates in")

    USERNAME_FIELD = 'email'
    # username is still required by AbstractUser internals; we set it = email on register
    REQUIRED_FIELDS = ['username']

    class Meta:
        verbose_name = 'User'

    def __str__(self):
        return f"{self.email} ({self.role})"    
