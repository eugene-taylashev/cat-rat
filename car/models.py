from django.db import models
from django.contrib.auth.models import User
from simple_history.models import HistoricalRecords
from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.utils import timezone


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

#==============================================================================
# Choices for Actions
#==============================================================================
class ActionType(models.TextChoices):
    RISK_TREATMENT = "risk_treatment", "Risk Treatment"
    RISK_ASSESSMENT = "risk_assessment", "Risk Assessment"
    CONTROL_IMPROVEMENT = "control_improvement", "Control Improvement"
    CONTROL_ASSESSMENT = "control_assessment", "Control Assessment"
    REVIEW = "review", "Review"
    OTHER = "other", "Other"


class ActionStatus(models.TextChoices):
    PLANNED = "planned", "Planned"
    IN_PROGRESS = "in_progress", "In Progress"
    COMPLETED = "completed", "Completed"
    CANCELLED = "cancelled", "Cancelled"
    
class ActionPriority(models.IntegerChoices):
    LOW = 1, "Low"
    MEDIUM = 2, "Medium"
    HIGH = 3, "High"
    CRITICAL = 4, "Critical"
    
#==============================================================================
class Action(TimestampedModel):
    """
    All actions planned to treat the risk, improve control or assess risks
    """
    action_code = models.CharField(
        max_length=50,
        unique=True,
        help_text="Human-readable action identifier.",)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    action_type = models.CharField(
        max_length=30,
        choices=ActionType.choices,
    )

    owner = models.ForeignKey(
        Owner,
        related_name="actions",
        on_delete=models.PROTECT,
    )

    priority = models.PositiveSmallIntegerField(
        choices=ActionPriority.choices,
        default=ActionPriority.MEDIUM,
    )

    status = models.CharField(
        max_length=20,
        choices=ActionStatus.choices,
        default=ActionStatus.PLANNED,
    )

    due_date = models.DateField(
        null=True,
        blank=True,
    )

    started_at = models.DateTimeField(
        null=True,
        blank=True,
        editable=False,
    )

    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        editable=False,
    )

    completed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="completed_actions",
        editable=False,
    )

    history = HistoricalRecords()

    class Meta:
        ordering = ["due_date", "title"]

    #----------------------
    def __str__(self):
        return f"{self.action_code} - {self.title}"

    #----------------------
    def start(self, user=None):
        self.status = ActionStatus.IN_PROGRESS

        if self.started_at is None:
            self.started_at = timezone.now()

        self.save(user=user)

    #@property
    #----------------------
    def is_overdue(self):
        if self.status in {
            ActionStatus.COMPLETED,
            ActionStatus.CANCELLED,
        }:
            return False

        if self.due_date is None:
            return False

        return self.due_date < timezone.localdate()        

    #----------------------
    def mark_done(self, user=None):
        self.status = ActionStatus.COMPLETED
        self.completed_at = timezone.now()

        if user is not None:
            self.completed_by = user

        self.save(user=user)
    
    #----------------------
    def reopen(self, user=None):
        self.status = ActionStatus.IN_PROGRESS
        self.completed_at = None
        self.completed_by = None

        self.save(user=user)
    
#==============================================================================
# Choices for Risk assessment, ISO 27005 specific
#==============================================================================
class RiskStatus(models.TextChoices):
    IDENTIFIED = "identified", "Identified"
    ASSESSED = "assessed", "Assessed"
    REJECTED = "rejected", "Rejected"
    TREATMENT_PLANNED = "treatment_planned", "Treatment planned"
    TREATMENT_IN_PROGRESS = "treatment_in_progress", "Treatment in progress"
    TREATED = "treated", "Treated / Implemented"
    REVIEWED = "reviewed", "Reviewed"
    ACCEPTED = "accepted", "Accepted"
    CLOSED = "closed", "Closed"


class LikelihoodLevel(models.IntegerChoices):
    """Simple numeric scale — adjust granularities as you need."""
    RARE = 1, "Rare"
    UNLIKELY = 2, "Unlikely"
    POSSIBLE = 3, "Possible"
    LIKELY = 4, "Likely"
    CERTAIN = 5, "Almost certain"


class ImpactLevel(models.IntegerChoices):
    LOW = 1, "Insignificant"
    MEDIUM = 2, "Minor"
    HIGH = 3, "Moderate"
    CRITICAL = 4, "Major"
    CATASTROPHIC = 5, "Catastrophic"


class RiskTreatment(models.TextChoices):
    NONE = "none", "None"
    ACCEPT = "accept", "Accept"
    MITIGATE = "mitigate", "Mitigate"
    TRANSFER = "transfer", "Transfer / Share"
    AVOID = "avoid", "Avoid"

class RiskLevel(models.IntegerChoices):
    ''' Qualitative risk label (Low/Medium/High) '''
    LOW = 1, "Low"
    MEDIUM = 2, "Medium"
    HIGH = 3, "High"
    CRITICAL = 4, "Critical"


#==============================================================================
class Risk(TimestampedModel):
    """
    The central risk entity — links assets, threat, vulnerability and holds assessment and treatment info.
    Aligns to ISO 27005 risk definition and lifecycle.
    """
    risk_code = models.CharField( max_length=50, unique=True, help_text="human-readable risk identifier",)
    scenario = models.TextField(help_text="Concise risk statement / scenario (cause -> event -> consequence)")
    asset = models.ForeignKey(Asset,related_name="risks",on_delete=models.PROTECT,blank=True,null=True) 
    owner = models.ForeignKey(Owner,related_name="risks",on_delete=models.PROTECT,blank=True,null=True) 
    status = models.CharField(max_length=25, choices=RiskStatus.choices, default=RiskStatus.IDENTIFIED)

    # --------------------------------------------------------------
    # Inherent risk
    # --------------------------------------------------------------
    inherent_likelihood = models.PositiveSmallIntegerField(choices=LikelihoodLevel.choices, null=True, blank=True)
    inherent_impact = models.PositiveSmallIntegerField(choices=ImpactLevel.choices, null=True, blank=True)
    inherent_score = models.PositiveSmallIntegerField(null=True, blank=True, editable=False, help_text="Numeric score (likelihood × impact or custom)")
    inherent_level = models.PositiveSmallIntegerField(choices=RiskLevel.choices,
        null=True, blank=True, editable=False, help_text="Qualitative label (Low/Medium/High)")
    inherent_assessed_at = models.DateTimeField(null=True,blank=True, help_text="Assessment date of inherent risk",)

    # --------------------------------------------------------------
    # Related controls
    # --------------------------------------------------------------
    controls = models.ManyToManyField(
        Control,
        related_name='risks',
        blank=True,
        help_text="Compensating controls"
    )
    treatment_option = models.CharField(
        max_length=20,
        choices=RiskTreatment.choices,
        blank=True,
        default=RiskTreatment.NONE,
    )

    # --------------------------------------------------------------
    # Residual risk
    # --------------------------------------------------------------
    residual_likelihood = models.PositiveSmallIntegerField(choices=LikelihoodLevel.choices, null=True, blank=True)
    residual_impact = models.PositiveSmallIntegerField(choices=ImpactLevel.choices, null=True, blank=True)

    # Computed/derived fields
    residual_score = models.PositiveSmallIntegerField(null=True, blank=True, editable=False, help_text="Numeric score (likelihood × impact or custom)")
    residual_level = models.PositiveSmallIntegerField(choices=RiskLevel.choices,
        null=True, blank=True, editable=False, help_text="Qualitative label (Low/Medium/High)")
    residual_assessed_at = models.DateTimeField(null=True,blank=True, help_text="Assessment date of residual risk",)
    next_review_date = models.DateField(null=True,blank=True, help_text="Date for the next assessment",)

    history = HistoricalRecords()


    class Meta:
        ordering = ["risk_code"]

    #----------------------------
    def __str__(self):
        return f"{self.risk_code} - {self.scenario[:80]}"

    #----------------------------
    def calculate_inherent_score(self):
        if self.inherent_likelihood is None or self.inherent_impact is None:
            return None
        return self.inherent_likelihood * self.inherent_impact

    #----------------------------
    def calculate_residual_score(self):
        if self.residual_likelihood is None or self.residual_impact is None:
            return None
        return self.residual_likelihood * self.residual_impact

    #----------------------------
    def calculate_risk_level(self, score):
        if score is None:
            return None
        if score <= 4:
            return RiskLevel.LOW
        elif score <= 9:
            return RiskLevel.MEDIUM
        elif score <= 16:
            return RiskLevel.HIGH
        else:
            return RiskLevel.CRITICAL

    #----------------------------
    def save(self, *args, **kwargs):
        #-- Inherent risk
        self.inherent_score = self.calculate_inherent_score()
        self.inherent_level = self.calculate_risk_level(self.inherent_score)

        #-- Residual risk
        self.residual_score = self.calculate_residual_score()
        self.residual_level = self.calculate_risk_level(self.residual_score)
        
        #-- Default next review to one year after residual assessment
        if self.next_review_date is None and self.residual_assessed_at is not None:
            self.next_review_date = (self.residual_assessed_at + relativedelta(years=1)).date()

        super().save(*args, **kwargs)        


#==============================================================================
class RiskAction(models.Model):
    action = models.OneToOneField(
        Action,
        on_delete=models.PROTECT,
        related_name="risk_action",
    )

    risk = models.ForeignKey(
        Risk,
        on_delete=models.PROTECT,
        related_name="actions",
    )        

#==============================================================================
class ControlAction(models.Model):
    action = models.OneToOneField(
        Action,
        on_delete=models.PROTECT,
        related_name="control_action",
    )

    control = models.ForeignKey(
        Control,
        on_delete=models.PROTECT,
        related_name="actions",
    )

    