"""Rutas de administración de catálogos."""

from django.urls import path

from . import views

app_name = "catalog"

urlpatterns = [
    path("proyectos/", views.project_admin, name="project_admin"),
    path("proyectos/nuevo/", views.project_edit, name="project_create"),
    path("proyectos/<int:pk>/", views.project_edit, name="project_edit"),
    path("proyectos/<int:pk>/eliminar/", views.project_delete, name="project_delete"),
    path("proyectos/<int:pk>/reactivar/", views.project_reactivate, name="project_reactivate"),
    path("periodos/", views.period_admin, name="period_admin"),
    path("periodos/nuevo/", views.period_create, name="period_create"),
    # Pendiente: weight_admin, area/level admin (hoy vía Django admin)
]
