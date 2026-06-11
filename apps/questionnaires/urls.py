"""Rutas del motor/editor de cuestionarios."""

from django.urls import path

from . import views

app_name = "questionnaires"

urlpatterns = [
    path("admin/", views.admin_list, name="admin_list"),
    path("admin/<int:pk>/", views.template_edit, name="template_edit"),
]
