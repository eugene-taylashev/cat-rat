from django.db import models
from django.contrib.auth.models import User
from simple_history.models import HistoricalRecords
from django.conf import settings
from django.utils import timezone
import uuid


#==============================================================================
class TimestampedModel(models.Model):
    """Simple timestamp mixin.
     In app use asset.save(user=request.user)  """
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="%(class)s_created",
        editable=False,
    )

    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="%(class)s_updated",
        editable=False,
    )

    updated_by_username = models.CharField(
        max_length=150,
        blank=True,
        editable=False,
    )

    class Meta:
        abstract = True

    def save(self, *args, user=None, **kwargs):
        """Save the object and record the user who created/updated it."""

        if user is not None:
            # New object
            if self._state.adding:
                self.created_by = user

            # Every save
            self.updated_by = user
            self.updated_by_username = user.get_username()

        super().save(*args, **kwargs)

#==============================================================================
class Owner(TimestampedModel):
    '''List of asset/controls/evidence/risk owners'''
    name = models.CharField(help_text="Person or team responsible for this asset", max_length=150)
    contact_prim = models.CharField(help_text="Primary contact in event of an incident/DR", blank=True,null=True)
    users = models.ManyToManyField(
        User,
        through='OwnerMembership',
        related_name='owners'
    )

    def __str__(self):
        return self.name


#==============================================================================
class OwnerMembership(models.Model):
    '''Many-to-many relationship between Owner and Django users'''
    class Role(models.TextChoices):
        OWNER = "OWNER", "Product Owner"
        MANAGER = "MANAGER", "Manager/Director"
        MEMBER = "MEMBER", "Member"
        VIEWER = "VIEWER", "Viewer"

    owner = models.ForeignKey(
        Owner,
        on_delete=models.CASCADE
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE
    )

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.MEMBER
    )

    is_primary = models.BooleanField(default=False)

    class Meta:
        unique_together = ("owner", "user")


#==============================================================================
class Asset(TimestampedModel):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="children"
    )
    owner = models.ForeignKey(Owner,on_delete=models.PROTECT,blank=True,null=True) 
    is_active = models.BooleanField(default=True)
    history = HistoricalRecords()

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

