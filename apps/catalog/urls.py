"""Rutas de administración de catálogos."""

from django.urls import path

from . import views, views_areas, views_catalogs, views_weights

app_name = "catalog"

urlpatterns = [
    path("proyectos/", views.project_admin, name="project_admin"),
    path("proyectos/nuevo/", views.project_edit, name="project_create"),
    path("proyectos/<int:pk>/", views.project_edit, name="project_edit"),
    path("proyectos/<int:pk>/eliminar/", views.project_delete, name="project_delete"),
    path("proyectos/<int:pk>/reactivar/", views.project_reactivate, name="project_reactivate"),
    path("periodos/", views.period_admin, name="period_admin"),
    path("periodos/nuevo/", views.period_create, name="period_create"),
    path("periodos/<int:pk>/editar/", views.period_edit, name="period_edit"),
    path("periodos/<int:pk>/eliminar/", views.period_delete, name="period_delete"),
    path("areas/", views_areas.area_admin, name="area_admin"),
    path("areas/<int:pk>/borrar/", views_areas.area_delete, name="area_delete"),
    path("puestos/", views_catalogs.position_admin, name="position_admin"),
    path("puestos/<int:pk>/borrar/", views_catalogs.position_delete, name="position_delete"),
    path("categorias/", views_catalogs.category_admin, name="category_admin"),
    path("categorias/<int:pk>/borrar/", views_catalogs.category_delete, name="category_delete"),
    path("escenarios/", views.scenario_admin, name="scenario_admin"),
    path("escenarios/nuevo/", views.scenario_create, name="scenario_create"),
    path("escenarios/<int:pk>/editar/", views.scenario_edit, name="scenario_edit"),
    path("ponderaciones/", views_weights.weight_admin, name="weight_admin"),
    path("ponderaciones/guardar/", views_weights.weight_save, name="weight_save"),
    # Pendiente: CRUD de niveles (hoy vía Django admin)
]
