from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    ROLE_ADMIN = 'admin'
    ROLE_VIEWER = 'viewer'
    ROLE_CHOICES = [
        (ROLE_ADMIN, 'Admin'),
        (ROLE_VIEWER, 'Viewer'),
    ]
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default=ROLE_VIEWER)

    @property
    def is_admin_role(self):
        return self.role == self.ROLE_ADMIN or self.is_superuser

    def __str__(self):
        return f'{self.username} ({self.role})'
