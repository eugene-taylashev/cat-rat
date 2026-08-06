from django.urls import path     # type: ignore

from . import views

urlpatterns = [
    path("", views.main, name="main"),
    path("asset/", views.asset_list, name="asset_list"),
]