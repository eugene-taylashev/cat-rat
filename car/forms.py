from django import forms #type: ignore
from django.forms import inlineformset_factory  
import logging

from .models import *

logger = logging.getLogger(__name__)

#==============================================================================
class OwnerForm(forms.ModelForm):
    class Meta:
        model = Owner
        fields = [
            "name",
            "contact_prim",
        ]

        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "input",
                }
            ),

            "contact_prim": forms.TextInput(
                attrs={
                    "class": "input",
                }
            ),
        }

        labels = {
            "name": "Owner / Team Name",
            "contact_prim": "Primary Contact",
        }


#==============================================================================
class OwnerMembershipForm(forms.ModelForm):

    class Meta:
        model = OwnerMembership
        fields = [
            "user",
            "role",
            "is_primary",
        ]

        widgets = {
            "user": forms.Select(
                attrs={
                    "class": "select",
                }
            ),

            "role": forms.Select(
                attrs={
                    "class": "select",
                }
            ),

            "is_primary": forms.CheckboxInput(
                attrs={
                    "class": "checkbox",
                }
            ),
        }


#==============================================================================
OwnerMembershipFormSet = inlineformset_factory(
    Owner,
    OwnerMembership,
    form=OwnerMembershipForm,
    extra=1,
    can_delete=True,
)


#==============================================================================
class AssetForm(forms.ModelForm):
    class Meta:
        model = Asset
        fields = [
            "name",
            "description",
            "parent",
            "owner",
            "is_active",
        ]

        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "input",
                    "placeholder": "Asset name",
                }
            ),

            "description": forms.Textarea(
                attrs={
                    "class": "textarea",
                    "rows": 5,
                    "placeholder": "Asset description",
                }
            ),

            "parent": forms.Select(
                attrs={
                    "class": "select",
                }
            ),

            "owner": forms.Select(
                attrs={
                    "class": "select",
                }
            ),

            "is_active": forms.CheckboxInput(
                attrs={
                    "class": "checkbox",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Don't allow an Asset to be its own parent
        if self.instance and self.instance.pk:
            self.fields["parent"].queryset = Asset.objects.exclude(
                pk=self.instance.pk
            )

#==============================================================================
class ControlForm(forms.ModelForm):

    class Meta:
        model = Control

        fields = [
            "control_label",
            "title",
            "description",
            "sec_function",
            "asset",
            "owner",
            "status",
            "documentation_url",
        ]

        widgets = {
            "control_label": forms.TextInput(
                attrs={
                    "class": "input",
                    "placeholder": "e.g. IAM-002",
                }
            ),

            "title": forms.TextInput(
                attrs={
                    "class": "input",
                    "placeholder": "Control title",
                }
            ),

            "description": forms.Textarea(
                attrs={
                    "class": "textarea",
                    "rows": 6,
                    "placeholder": "Describe the control activity...",
                }
            ),

            "sec_function": forms.Select(
                attrs={
                    "class": "select",
                }
            ),

            "asset": forms.Select(
                attrs={
                    "class": "select",
                }
            ),

            "owner": forms.Select(
                attrs={
                    "class": "select",
                }
            ),

            "status": forms.Select(
                attrs={
                    "class": "select",
                }
            ),

            "documentation_url": forms.URLInput(
                attrs={
                    "class": "input",
                    "placeholder": "https://...",
                }
            ),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)

        # ------------------------------------------------------------
        # Owner choices
        #
        # Show only Owners to which the current user belongs.
        # ------------------------------------------------------------
        if user is not None:
            self.fields["owner"].queryset = Owner.objects.filter(
                ownermembership__user=user
            ).distinct()

        # ------------------------------------------------------------
        # Asset choices
        #
        # Optional: restrict assets to assets owned by the user's
        # Owners. Remove this section if users should see all assets.
        # ------------------------------------------------------------
        #if user is not None:
        #    self.fields["asset"].queryset = Asset.objects.filter(
        #        ownermembership__user=user
        #    ).distinct()

        # ------------------------------------------------------------
        # Make the empty option more meaningful
        # ------------------------------------------------------------
        self.fields["asset"].empty_label = "— No asset —"
        self.fields["owner"].empty_label = "— No owner —"

        # ------------------------------------------------------------
        # Help text
        # ------------------------------------------------------------
        self.fields["control_label"].help_text = (
            "Unique control reference, e.g. IAM-002 or BCP-003."
        )

        self.fields["title"].help_text = (
            "Short name describing the control activity."
        )

        self.fields["description"].help_text = (
            "Describe what the control does and what it is intended "
            "to accomplish."
        )


#==============================================================================
class RiskForm(forms.ModelForm):

    class Meta:
        model = Risk

        fields = [
            "risk_code",
            "scenario",
            "asset",
            "owner",
            "status",

            # Inherent risk
            "inherent_likelihood",
            "inherent_impact",
            "inherent_assessed_at",

            # Controls / treatment
            "controls",
            "treatment_option",

            # Residual risk
            "residual_likelihood",
            "residual_impact",
            "residual_assessed_at",
            "next_review_date",
        ]

        widgets = {

            "risk_code": forms.TextInput(
                attrs={
                    "class": "input",
                    "placeholder": "RISK-001",
                }
            ),

            "scenario": forms.Textarea(
                attrs={
                    "class": "textarea",
                    "rows": 5,
                    "placeholder": (
                        "Describe the risk scenario "
                        "(cause → event → consequence)"
                    ),
                }
            ),

            "asset": forms.Select(
                attrs={
                    "class": "select",
                }
            ),

            "owner": forms.Select(
                attrs={
                    "class": "select",
                }
            ),

            "status": forms.Select(
                attrs={
                    "class": "select",
                }
            ),

            "inherent_likelihood": forms.Select(
                attrs={
                    "class": "select",
                }
            ),

            "inherent_impact": forms.Select(
                attrs={
                    "class": "select",
                }
            ),

            "inherent_assessed_at": forms.DateTimeInput(
                attrs={
                    "class": "input",
                    "type": "datetime-local",
                }
            ),

            "controls": forms.SelectMultiple(
                attrs={
                    "class": "select",
                    "size": 8,
                }
            ),

            "treatment_option": forms.Select(
                attrs={
                    "class": "select",
                }
            ),

            "residual_likelihood": forms.Select(
                attrs={
                    "class": "select",
                }
            ),

            "residual_impact": forms.Select(
                attrs={
                    "class": "select",
                }
            ),

            "residual_assessed_at": forms.DateTimeInput(
                attrs={
                    "class": "input",
                    "type": "datetime-local",
                }
            ),

            "next_review_date": forms.DateInput(
                attrs={
                    "class": "input",
                    "type": "date",
                }
            ),
        }

        labels = {
            "risk_code": "Risk Code",
            "scenario": "Risk Scenario",
            "asset": "Related Asset",
            "owner": "Risk Owner",
            "status": "Status",

            "inherent_likelihood": "Likelihood",
            "inherent_impact": "Impact",
            "inherent_assessed_at": "Assessment Date",

            "controls": "Compensating Controls",
            "treatment_option": "Treatment Option",

            "residual_likelihood": "Likelihood",
            "residual_impact": "Impact",
            "residual_assessed_at": "Assessment Date",
            "next_review_date": "Next Review",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["asset"].queryset = (
            Asset.objects
            .filter(is_active=True)
            .order_by("name")
        )

        self.fields["owner"].queryset = (
            Owner.objects
            .order_by("name")
        )

        self.fields["controls"].queryset = (
            Control.objects
            .filter(status=ControlStatus.ACTIVE)
            .order_by("control_label")
        )

    def clean(self):
        super().clean()

        if self.cleaned_data.get("status") in [
            RiskStatus.ASSESSED,
            RiskStatus.TREATMENT_PLANNED,
            RiskStatus.TREATMENT_IN_PROGRESS,
            RiskStatus.TREATED,
            RiskStatus.REVIEWED,
            RiskStatus.ACCEPTED,
            RiskStatus.CLOSED,
        ]:
            if not self.cleaned_data.get("inherent_likelihood"):
                self.add_error(
                    "inherent_likelihood",
                    "Likelihood is required for an assessed risk."
                )

            if not self.cleaned_data.get("inherent_impact"):
                self.add_error(
                    "inherent_impact",
                    "Impact is required for an assessed risk."
                )

#==============================================================================
class ActionForm(forms.ModelForm):

    class Meta:
        model = Action

        fields = [
            "action_code",
            "title",
            "description",
            "action_type",
            "owner",
            "priority",
            "due_date",
        ]

        widgets = {
            "action_code": forms.TextInput(
                attrs={
                    "class": "input",
                    "placeholder": "ACT-001",
                }
            ),

            "title": forms.TextInput(
                attrs={
                    "class": "input",
                    "placeholder": "Action title",
                }
            ),

            "description": forms.Textarea(
                attrs={
                    "class": "textarea",
                    "rows": 5,
                }
            ),

            "action_type": forms.Select(
                attrs={
                    "class": "select",
                }
            ),

            "owner": forms.Select(
                attrs={
                    "class": "select",
                }
            ),

            "priority": forms.Select(
                attrs={
                    "class": "select",
                }
            ),

            "status": forms.Select(
                attrs={
                    "class": "select",
                }
            ),

            "due_date": forms.DateInput(
                attrs={
                    "class": "input",
                    "type": "date",
                }
            ),
        }

        labels = {
            "action_code": "Action Code",
            "title": "Title",
            "description": "Description",
            "action_type": "Action Type",
            "owner": "Owner",
            "priority": "Priority",
            "status": "Status",
            "due_date": "Due Date",
        }

    #-------------------------------------
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["owner"].queryset = (
            Owner.objects
            .order_by("name")
        )
        
        logger.debug(
            "ActionForm initialized. instance=%s, bound=%s",
            self.instance,
            self.is_bound,
        )

    #-------------------------------------
    def clean(self):
        """
        Form-wide validation and debugging.
        """

        logger.debug("================================================")
        logger.debug("ActionForm.clean() started")
        logger.debug("Raw form data: %s", self.data)

        cleaned_data = super().clean()

        logger.debug(
            "ActionForm.cleaned_data: %s",
            cleaned_data
        )

        logger.debug(
            "ActionForm.errors after field validation: %s",
            self.errors
        )

        # -------------------------------------------------
        # Example validation
        # -------------------------------------------------

        action_code = cleaned_data.get("action_code")
        title = cleaned_data.get("title")
        owner = cleaned_data.get("owner")
        due_date = cleaned_data.get("due_date")

        logger.debug(
            "action_code=%r",
            action_code
        )

        logger.debug(
            "title=%r",
            title
        )

        logger.debug(
            "owner=%r",
            owner
        )

        logger.debug(
            "due_date=%r",
            due_date
        )

        # -------------------------------------------------
        # Your custom validation can go here
        # -------------------------------------------------

        if not action_code:
            logger.warning(
                "ActionForm validation: action_code is empty"
            )

        if not title:
            logger.warning(
                "ActionForm validation: title is empty"
            )

        if owner is None:
            logger.warning(
                "ActionForm validation: owner is None"
            )

        logger.debug("ActionForm.clean() completed")

        return cleaned_data        
        
#==============================================================================
class AssessmentForm(forms.ModelForm):

    class Meta:
        model = Assessment

        fields = [
            "assessment_code",
            "title",
            "owner",
            "assessment_type",
            "status",
            "start_date",
            "due_date",
            "description",
        ]

        widgets = {
            "assessment_code": forms.TextInput(
                attrs={
                    "class": "input",
                    "placeholder": "e.g. AUD-002",
                    'style': 'width: 150px;',
                }
            ),

            "title": forms.TextInput(
                attrs={
                    "class": "input",
                    "placeholder": "Assessment/Audit title",
                }
            ),

            "description": forms.Textarea(
                attrs={
                    "class": "textarea",
                     "rows": 4,
                    "style": 'width: 350px;',
                    "placeholder": "Provide assessment details...",
                }
            ),
            "start_date": forms.DateInput(
                attrs={"type": "date"}
            ),
            "due_date": forms.DateInput(
                attrs={"type": "date"}
            ),
        }

#==============================================================================
class AssessmentControlScopeForm(forms.ModelForm):

    class Meta:
        model = AssessmentControlScope

        fields = [
            "include_all",
            "controls",
        ]

        widgets = {
            "controls": forms.SelectMultiple(
                attrs={
                    "size": 12,
                }
            ),
        }


#==============================================================================
class AssessmentRiskScopeForm(forms.ModelForm):

    class Meta:
        model = AssessmentRiskScope

        fields = [
            "include_all",
            "risks",
        ]

        widgets = {
            "risks": forms.SelectMultiple(
                attrs={
                    "size": 12,
                }
            ),
        }

