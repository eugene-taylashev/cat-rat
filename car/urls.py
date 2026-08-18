from django.urls import path     # type: ignore

from . import views

urlpatterns = [
    path("", views.main, name="main"),

    #-- manage owners
    path("owner/", views.owner_list, name="owner_list"),
    path("owner/<int:pk>/edit", views.owner_edit, name="owner_edit"),


    #-- manage assets
    path("asset/", views.asset_list, name="asset_list"),
    path("asset/<int:pk>/edit", views.asset_edit, name="asset_edit"),
    #path("asset/<int:pk>/delete/", views.asset_delete, name="asset_delete"),
    #path("asset/<int:pk>/history/", views.asset_history, name="asset_history"),

    #-- manage controls
    path("control/", views.control_list, name="control_list"),
    path("control/<int:pk>/edit/", views.control_edit, name="control_edit"),
    path("control/<int:pk>/history/", views.control_history, name="control_history"),
    path("control/<int:pk>/delete/", views.control_delete, name="control_delete"),
    path("control/<int:pk>/delete/confirm", views.control_delete_confirmed, name="control_delete_confirmed"),

    #-- manage risks
    path("risk/", views.risk_list, name="risk_list"),
    path("risk/<int:pk>/edit/", views.risk_edit, name="risk_edit"),
    path("risk/<int:pk>/delete/", views.risk_delete, name="risk_delete"),

    #-- manage actions/tasks
    path("actions/", views.action_list, name="action_list"),
    path("actions/<int:pk>/", views.action_detail, name="action_detail"),
    path("actions/<int:pk>/edit/", views.action_edit, name="action_edit"),
    path("actions/<int:pk>/start/", views.action_start, name="action_start"),
    path("actions/<int:pk>/complete/", views.action_complete, name="action_complete"),
    path("actions/<int:pk>/reopen/", views.action_reopen, name="action_reopen"),

]