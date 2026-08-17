from django import forms #type: ignore
from django.forms import inlineformset_factory  

from .models import *

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

