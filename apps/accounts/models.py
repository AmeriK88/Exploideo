from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    class Role(models.TextChoices):
        TRAVELER = "traveler", "Traveler"
        GUIDE = "guide", "Guide"

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.TRAVELER,
    )

    def is_guide(self) -> bool:
        return self.role == self.Role.GUIDE

    def is_traveler(self) -> bool:
        return self.role == self.Role.TRAVELER

    class Meta:
        app_label = "accounts"