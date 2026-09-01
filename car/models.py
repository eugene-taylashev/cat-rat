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
class AppSettings(TimestampedModel):
    '''
    Application or System wide settings
    It will be only one row in this table

    Usage: 
        settings = AppSettings.get()

        if settings.control_maturity_advanced:
    '''
    
    #-- Control params
    control_maturity_advanced = models.BooleanField(
        default=False,
        help_text="Enable advanced control maturity assessment (implementation, automation, reporting, documentation)."
    )
    control_effectiveness_enabled = models.BooleanField( default=True )
    control_testing_required = models.BooleanField( default=True )
    default_control_review_months = models.PositiveIntegerField( default=12 )

    #-- Risk params
    risk_auto_calculation = models.BooleanField( default=True )
    default_risk_review_months = models.PositiveIntegerField( default=12 )
    risk_matrix_size = models.PositiveSmallIntegerField( default=5 )  # 3x3 or 5x5
    risk_acceptance_threshold = models.PositiveSmallIntegerField( default=6 )
    high_risk_threshold = models.PositiveSmallIntegerField( default=12 )
    critical_risk_threshold = models.PositiveSmallIntegerField( default=20 )

    #-- Actions and Remediation
    action_overdue_warning_days = models.PositiveIntegerField( default=14 )
    critical_action_due_days = models.PositiveIntegerField( default=30 )
    high_action_due_days = models.PositiveIntegerField( default=60 )
    medium_action_due_days = models.PositiveIntegerField( default=90 )

    #-- Compliance and Audit
    audit_evidence_required = models.BooleanField( default=True )
    policy_review_months = models.PositiveIntegerField( default=12 )
    exception_review_months = models.PositiveIntegerField( default=6 )
    
    #-- Notifications
    email_notifications_enabled = models.BooleanField( default=False )
    notify_risk_owner = models.BooleanField( default=False )
    notify_control_owner = models.BooleanField( default=False )
    notify_action_owner = models.BooleanField( default=False )
    reminder_days_before_due = models.PositiveIntegerField( default=14 )    

    #-- Dashboard / Reporting
    dashboard_show_closed_risks = models.BooleanField( default=False )
    dashboard_default_period_days = models.PositiveIntegerField( default=365 )
    kpi_warning_threshold = models.PositiveIntegerField( default=80 )

    #-- AI Features
    ai_features_enabled = models.BooleanField( default=False )
    ai_risk_suggestions_enabled = models.BooleanField( default=False )
    ai_risk_suggestions_prompt = models.CharField(help_text="Prompt to get risk suggestions", blank=True,null=True)
    ai_control_recommendations_enabled = models.BooleanField( default=False )
    ai_control_recommendations_prompt = models.CharField(help_text="Prompt to get control recommendations", blank=True,null=True)

    class Meta:
        verbose_name = "Application Settings"
        verbose_name_plural = "Application Settings"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


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

    @property
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

    #----------------------
    def cancel(self, user=None):
        if self.status == ActionStatus.COMPLETED:
            raise ValidationError(
                "Completed actions cannot be cancelled."
            )

        self.status = ActionStatus.CANCELLED
        self.save(user=user)    


#==============================================================================
# Choices for Risk assessment, ISO 27005 lifecycle
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
    The central risk entity with persistent risk parameters — links assets, 
        threat, etc.
    Aligns to ISO 27005 risk definition and lifecycle.
    """
    risk_code = models.CharField( max_length=50, unique=True, help_text="human-readable risk identifier",) #i.e. RISK-002
    scenario = models.TextField(help_text="Concise risk statement / scenario (cause -> event -> consequence)")
    asset = models.ForeignKey(Asset,related_name="risks",on_delete=models.PROTECT,blank=True,null=True) 
    owner = models.ForeignKey(Owner,related_name="risks",on_delete=models.PROTECT,blank=True,null=True) 
    status = models.CharField(max_length=25, choices=RiskStatus.choices, default=RiskStatus.IDENTIFIED)

    # --------------------------------------------------------------
    # Inherent rating = risk before considering controls
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
    # Residual rating = risk after considering existing controls
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

#==============================================================================
# Choices for Assessment / Audit
#==============================================================================
class AssessmentType(models.TextChoices):
    RISK = "risk", "Risk Assessment"
    CONTROL = "control", "Control Assessment"
    AUDIT = "audit", "Audit/Test of controls"
    OTHER = "other", "Other"

class AssessmentStatus(models.TextChoices):
    PLANNED = "planned", "Planned"
    IN_PROGRESS = "in_progress", "In Progress"
    COMPLETED = "completed", "Completed"
    CANCELLED = "cancelled", "Cancelled"

class AssessmentItemStatus(models.TextChoices):
    NOT_STARTED = "not_started", "Not Started"
    ASSIGNED = "assigned", "Assigned"
    IN_PROGRESS = "in_progress", "In Progress"
    COMPLETED = "completed", "Completed"
    NOT_APPLICABLE = "not_applicable", "Not Applicable"

#==============================================================================
class Assessment(models.Model):
    '''

Assessment
    │
    ├── AssessmentItem → Risk
    │       └── RiskAssessment
    │
    └── AssessmentItem → Control
            ├── ControlMaturityAssessment
            └── ControlTest
                    └── TestResult
                            └── CollectedArtifact    
    '''

    assessment_code = models.CharField( max_length=50, unique=True, help_text="human-readable audit identifier",) #i.e. AUDIT-002)
    title = models.CharField( max_length=255,)
    owner = models.ForeignKey( Owner, related_name="assessments", on_delete=models.PROTECT, blank=True,null=True, help_text="Overall owner for the assessment", )
    assessment_type = models.CharField(max_length=20,choices=AssessmentType.choices,)
    status = models.CharField( max_length=20, choices=AssessmentStatus.choices,
        default=AssessmentStatus.PLANNED, )

    start_date = models.DateField( null=True, blank=True, )
    due_date = models.DateField( null=True, blank=True,)
    completed_at = models.DateTimeField( null=True, blank=True, )

    description = models.TextField( blank=True, )
    history = HistoricalRecords()

    class Meta:
        ordering = ["-start_date", "assessment_code"]

    def __str__(self):
        return f"{self.assessment_code} - {self.title}"   



#==============================================================================
class AssessmentItemType(models.TextChoices):
    RISK = "RISK", "Risk Assessment"
    CONTROL_MATURITY = "CONTROL_MATURITY", "Control Maturity"
    CONTROL_TEST = "CONTROL_TEST", "Control Test"

#==============================================================================
class AssessmentItem(models.Model):
    '''
    AssessmentItem = work management
    Concept: "Somebody has been assigned to perform this assessment."
    '''
    assessment = models.ForeignKey( Assessment, related_name="items", on_delete=models.CASCADE, )

    item_type = models.CharField(
        max_length=30,
        choices=AssessmentItemType.choices,
        null=True, blank=True,
    )

    risk = models.ForeignKey( Risk, related_name="assessment_items", on_delete=models.PROTECT, null=True, blank=True,)
    control = models.ForeignKey( Control, related_name="assessment_items", on_delete=models.PROTECT, null=True, blank=True,)
    owner = models.ForeignKey( Owner, related_name="assessment_items", on_delete=models.PROTECT, )

    status = models.CharField( max_length=20, choices=AssessmentItemStatus.choices,
        default=AssessmentItemStatus.NOT_STARTED,
    )

    assigned_at = models.DateTimeField( null=True, blank=True, )
    completed_at = models.DateTimeField( null=True, blank=True, )
    completed_by = models.ForeignKey( settings.AUTH_USER_MODEL, null=True, blank=True, 
        on_delete=models.SET_NULL,
        related_name="completed_assessment_items",
    )

    comments = models.TextField( blank=True,)

    history = HistoricalRecords()

    class Meta:
        ordering = ["status", "id"]       
        #-- an item points to either a Risk or a Control, but not both
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(risk__isnull=False) ^
                    models.Q(control__isnull=False)
                ),
                name="assessment_item_one_target",
            ),
        ]     


#==============================================================================
class RiskAssessmentType(models.TextChoices):
    INITIAL = "INITIAL", "Initial Assessment"
    PERIODIC = "PERIODIC", "Periodic Assessment"
    EVENT = "EVENT", "Event-Driven Assessment"
    REVIEW = "REVIEW", "Risk Review"

#==============================================================================
class RiskAssessment(models.Model):
    '''


Risk
  │
  ├── RiskAssessment
  │      Initial
  │      Inherent: 25
  │      Residual: 10
  │
  ├── RiskAssessment
  │      Periodic
  │      Inherent: 20
  │      Residual: 10
  │
  └── RiskAssessment
         Event
         Inherent: 25
         Residual: 15    
    '''
    risk = models.ForeignKey(
        Risk,
        related_name="assessments",
        on_delete=models.PROTECT,
    )

    assessment_item = models.OneToOneField(
        AssessmentItem,
        related_name="risk_assessment",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )

    assessment_type = models.CharField(
        max_length=20,
        choices=RiskAssessmentType.choices,
    )

    inherent_likelihood = models.PositiveSmallIntegerField(
        choices=LikelihoodLevel.choices,
    )

    inherent_impact = models.PositiveSmallIntegerField(
        choices=ImpactLevel.choices,
    )

    residual_likelihood = models.PositiveSmallIntegerField(
        choices=LikelihoodLevel.choices,
        null=True,
        blank=True,
    )

    residual_impact = models.PositiveSmallIntegerField(
        choices=ImpactLevel.choices,
        null=True,
        blank=True,
    )

    rationale = models.TextField(blank=True)

    assessed_at = models.DateTimeField(auto_now_add=True)

    assessed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.SET_NULL,
    )

    history = HistoricalRecords()


#==============================================================================
class MaturityDimension(models.TextChoices):
    IMPLEMENTED = "IMPLEMENTED", "Implemented"
    DOCUMENTED = "DOCUMENTED", "Documented"
    AUTOMATED = "AUTOMATED", "Automated"
    REPORTED = "REPORTED", "Reported"
    TESTED = "TESTED", "Tested"
    
#==============================================================================
class ControlTestStep(TimestampedModel):
    '''
Control
   │
   ├── TestStep
   ├── TestStep
   └── TestStep    
    '''
    control = models.ForeignKey(
        Control,
        related_name="test_steps",
        on_delete=models.CASCADE,
    )

    sequence = models.PositiveIntegerField(default=1)

    title = models.CharField(max_length=200)

    description = models.TextField()

    is_required = models.BooleanField(default=True)

    history = HistoricalRecords()

    class Meta:
        ordering = ["sequence"]
        constraints = [
            models.UniqueConstraint(
                fields=["control", "sequence"],
                name="unique_control_test_step_sequence",
            )
        ]
        

#==============================================================================
class ControlImplemented(models.IntegerChoices):
    NOT_IMPLEMENTED = 0, "Not implemented"
    PARTIALLY_IMPLEMENTED = 1, "Partially implemented"
    FULLY_IMPLEMENTED = 3, "Fully implemented"
    VALIDATED_AND_TESTED = 5, "Validated and tested regularly"

class ControlDocumented(models.IntegerChoices):
    NOT_DOCUMENTED = 0, "Not documented"
    DRAFT_EXISTS = 1, "Draft exists"
    REVIEWED_INTERNALLY = 2, "Reviewed internally"
    APPROVED_AND_MAINTAINED = 3, "Approved and maintained"

class ControlAutomated(models.IntegerChoices):
    NOT_APPLICABLE = -1, "Not applicable"
    MANUAL = 0, "Manual"
    PARTIALLY_AUTOMATED = 1, "Partially automated"
    MOSTLY_AUTOMATED = 2, "Mostly automated"
    FULLY_AUTOMATED = 4, "Fully automated"

class ControlReported(models.IntegerChoices):
    NOT_REPORTED = 0, "Not reported"
    INFORMAL = 1, "Informal / ad hoc reporting"
    INTERNAL = 2, "Internal reporting"
    REGULAR_BUSINESS = 3, "Regular reporting to business"    
#==============================================================================
class ControlMaturityAssessment(models.Model):
    '''
Assessment
    │
    └── AssessmentItem
             │
             ├── ControlMaturityAssessment
             │
             └── ControlTest
                       │
                       ├── TestResult
                       │       └── CollectedArtifact
                       │
                       └── TestResult
                               └── CollectedArtifact    
    '''
    assessment_item = models.OneToOneField(
        AssessmentItem,
        related_name="maturity_assessment",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )

    #-- Basic model
    measure = models.PositiveSmallIntegerField( null=True, blank=True, )

    #-- Advanced model
    implemented = models.IntegerField( choices=ControlImplemented.choices, null=True, blank=True, )
    documented = models.IntegerField( choices=ControlDocumented.choices, null=True, blank=True, )
    automated = models.IntegerField( choices=ControlAutomated.choices, null=True, blank=True, )
    reported = models.IntegerField( choices=ControlReported.choices, null=True, blank=True, )

    comments = models.TextField(blank=True)

    history = HistoricalRecords()

    #-------------------------------
    @property
    def control_score(self):
        """
        Returns normalized score between 0.0 and 1.0.
        """

        settings = AppSettings.get()

        if not settings.control_maturity_advanced:
            if self.measure is None:
                return None

            # CIS measure 0-5 -> 0.0-1.0
            return round(self.measure / 5, 2)

        implemented = self.implemented or 0
        documented = self.documented or 0
        automated = self.automated or 0
        reported = self.reported or 0

        if automated > 0:
            # Maximum score = 15
            score = (
                implemented +
                documented +
                automated +
                reported
            ) / 15
        else :
            # Maximum score = 11
            score = (
                implemented +
                documented +
                reported
            ) / 11
            
        return round(score, 2)

    #-------------------------------
    @property
    def maturity_level(self):
        score = self.control_score

        if score is None:
            return "Not Assessed"

        if score < 0.25:
            return "Initial"

        if score < 0.50:
            return "Basic"

        if score < 0.75:
            return "Advanced"

        return "Mature"


#==============================================================================
class ControlTestConclusion(models.TextChoices):
    PASS = "PASS", "Pass"
    FAIL = "FAIL", "Fail"
    PARTIAL = "PARTIAL", "Partially Effective"
    NOT_APPLICABLE = "NA", "Not Applicable"


#==============================================================================
class ControlTest(models.Model):
    assessment_item = models.OneToOneField(
        AssessmentItem,
        related_name="control_test",
        on_delete=models.CASCADE,
    )

    conclusion = models.CharField(
        max_length=20,
        choices=ControlTestConclusion.choices,
        blank=True,
    )

    summary = models.TextField(blank=True)

    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    history = HistoricalRecords()
    

#==============================================================================
class TestResultStatus(models.TextChoices):
    PASS = "PASS", "Pass"
    FAIL = "FAIL", "Fail"
    MORE_INFO = "MORE_INFO", "Need more information"
    NOT_APPLICABLE = "NA", "Not Applicable"

#==============================================================================
class TestResult(models.Model):
    '''
TestResult
    |
    +── Artifact
    +── Artifact    
    '''
    control_test = models.ForeignKey(
        ControlTest,
        related_name="results",
        on_delete=models.CASCADE,
    )

    test_step = models.ForeignKey(
        ControlTestStep,
        related_name="results",
        on_delete=models.PROTECT,
    )

    result = models.CharField(
        max_length=20,
        choices=TestResultStatus.choices,
    )

    notes = models.TextField(blank=True)

    tested_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    tested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="control_test_results",
    )

    history = HistoricalRecords()


#==============================================================================
class CollectedArtifact(models.Model):
    test_result = models.ForeignKey(
        TestResult,
        related_name="artifacts",
        on_delete=models.CASCADE,
    )

    name = models.CharField(max_length=255)

    description = models.TextField(blank=True)

    file = models.FileField(
        upload_to="assessment-artifacts/",
        blank=True,
        null=True,
    )

    external_url = models.URLField(
        blank=True,
    )

    collected_at = models.DateTimeField(
        auto_now_add=True,
    )

    collected_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.SET_NULL,
    )

    history = HistoricalRecords()

#==============================================================================
class AssessmentControlScope(models.Model):
    '''
    Defines Control scope for an assessment
    Currently: all controls or manually selected
    '''
    assessment = models.OneToOneField(
        Assessment,
        related_name="control_scope",
        on_delete=models.CASCADE,
    )

    include_all = models.BooleanField(default=False)

    controls = models.ManyToManyField(
        Control,
        blank=True,
        related_name="assessment_scopes",
    )


#==============================================================================
class AssessmentRiskScope(models.Model):
    '''
    Defines Risk scope for an assessment
    Currently: all controls or manually selected
    '''
    assessment = models.OneToOneField(
        Assessment,
        related_name="risk_scope",
        on_delete=models.CASCADE,
    )

    include_all = models.BooleanField(default=False)

    risks = models.ManyToManyField(
        Risk,
        blank=True,
        related_name="assessment_scopes",
    )    