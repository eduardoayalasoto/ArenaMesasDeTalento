"""Rutas de Catálogos → Perfiles y permisos (spec 005)."""

from django.urls import path

from . import views

app_name = "access"

urlpatterns = [
    path("", views.profile_list, name="profile_list"),
    path("acceso/<int:user_pk>/", views.effective_access, name="effective_access"),
    path("<slug:slug>/", views.profile_matrix, name="profile_matrix"),
    path("<slug:slug>/duplicar/", views.profile_duplicate, name="profile_duplicate"),
    path("<slug:slug>/eliminar/", views.profile_delete, name="profile_delete"),
    path("<slug:slug>/asignar/", views.profile_assign, name="profile_assign"),
]
