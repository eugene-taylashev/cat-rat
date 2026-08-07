from django import forms #type: ignore
from .models import *

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

