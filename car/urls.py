from django.urls import path     # type: ignore

from . import views

urlpatterns = [
    path("", views.main, name="main"),
    path("asset/", views.asset_list, name="asset_list"),
    path("asset/<int:pk>/", views.asset_form, name="asset_form"),
    #path("asset/<int:pk>/edit", views.asset_edit, name="asset_edit"),
    #path("asset/<int:pk>/delete/", views.asset_delete, name="asset_delete"),
    #path("asset/<int:pk>/history/", views.asset_history, name="asset_history"),

    path("control/", views.control_list, name="control_list"),
    path("control/<int:pk>/edit/", views.control_edit, name="control_edit"),
    path("control/<int:pk>/history/", views.control_history, name="control_history"),
    path("control/<int:pk>/delete/", views.control_delete, name="control_delete"),
    path("control/<int:pk>/delete/confirm", views.control_delete_confirmed, name="control_delete_confirmed"),
]