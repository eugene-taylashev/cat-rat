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
    '''List of key asset with hierarhical structure'''
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

#==============================================================================
# Choices for Control assessment
#==============================================================================
class SecurityFunction(models.TextChoices):
    IDENTIFY = "IDENTIFY", "Identify"
    PROTECT = "PROTECT", "Protect"
    DETECT = "DETECT", "Detect"
    RESPOND = "RESPOND", "Respond"
    RECOVER = "RECOVER", "Recover"
    GOVERN = "GOVERN", "Govern"

class ControlStatus(models.TextChoices):
    PLANNING = "PLANNING", "Planning"
    ACTIVE = "ACTIVE", "Active"
    RETIRED = "RETIRED", "Retired"

class ImplementationLevel(models.IntegerChoices):
    NONE = 0, "Not implemented"
    PARTIAL = 1, "Partially implemented"
    FULL = 3, "Fully implemented"
    VALIDATED = 5, "Validated and tested regularly"

class DocumentationLevel(models.IntegerChoices):
    NONE = 0, "Not documented"
    DRAFT = 1, "Draft exists"
    REVIEWED = 2, "Reviewed internally"
    APPROVED = 3, "Approved and maintained"

class AutomationLevel(models.IntegerChoices):
    MANUAL = 0, "Manual"
    PARTIAL = 1, "Partially automated"
    MOSTLY = 2, "Mostly automated"
    FULL = 4, "Fully automated"

class ReportingLevel(models.IntegerChoices):
    NONE = 0, "Not reported"
    AD_HOC = 1, "Informal / ad hoc reporting"
    INTERNAL = 2, "Internal reporting"
    BUSINESS = 3, "Regular reporting to business units"


#==============================================================================
class Control(TimestampedModel):
    '''List of "controls", but in reality control activity '''
    control_label = models.CharField(max_length=50, unique=True,
        help_text="Control code/label for reference in documents. I.e. IAM-002, BCP-003"
    )
    title = models.CharField(max_length=200,blank=True, help_text="Control title (optional)")
    description = models.TextField(help_text="Control description")

    sec_function = models.CharField(max_length=10,
        choices=SecurityFunction.choices,
    )
    asset = models.ForeignKey(Asset,related_name="controls",on_delete=models.PROTECT,blank=True,null=True) 
    owner = models.ForeignKey(Owner,related_name="controls",on_delete=models.PROTECT,blank=True,null=True) 
    status = models.CharField(max_length=10, choices=ControlStatus.choices, default=ControlStatus.ACTIVE)
    documentation_url = models.URLField(blank=True, help_text="URL to external control documentation.")
    history = HistoricalRecords()

    #----------------------------
    def __str__(self):
        return self.description

    #----------------------------
    def clean(self):
        super().clean()

        if self.status == ControlStatus.ACTIVE and self.owner is None:
            raise ValidationError({
                "owner": "Active controls must have an owner."
            })
