from django.contrib import admin # type: ignore

from .models import *

admin.site.register(Owner)
admin.site.register(OwnerMembership)
admin.site.register(Asset)
admin.site.register(Control)

@admin.register(AppSettings)
class AppSettingsAdmin(admin.ModelAdmin):

    def has_add_permission(self, request):
        return not AppSettings.objects.exists()