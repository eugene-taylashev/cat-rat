"""
URL configuration for app project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
"""

from django.contrib import admin        # type: ignore
from django.urls import include, path   # type: ignore
from django.shortcuts import redirect   # type: ignore

from . import views

urlpatterns = [
    # /
    path("", include("car.urls", namespace='car-redirect')),
    path("car/", include("car.urls", namespace='car')),
    path('accounts/', include('django.contrib.auth.urls')),
    path('admin/', admin.site.urls),
]
