"""Rutas de administración de catálogos."""

from django.urls import path

from . import views, views_catalogs, views_org, views_weights

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
    path("areas/", views_org.department_admin, name="department_admin"),
    path("areas/nueva/", views_org.department_edit, name="department_edit"),
    path("areas/<int:pk>/editar/", views_org.department_edit, name="department_edit"),
    path("areas/<int:pk>/borrar/", views_org.department_delete, name="department_delete"),
    path("posiciones/", views_org.area_admin, name="area_admin"),
    path("posiciones/nueva/", views_org.area_edit, name="area_edit"),
    path("posiciones/<int:pk>/editar/", views_org.area_edit, name="area_edit"),
    path("posiciones/<int:pk>/borrar/", views_org.area_delete, name="area_delete"),
    path("niveles/", views_org.level_admin, name="level_admin"),
    path("niveles/nuevo/", views_org.level_edit, name="level_edit"),
    path("niveles/<int:pk>/editar/", views_org.level_edit, name="level_edit"),
    path("niveles/<int:pk>/borrar/", views_org.level_delete, name="level_delete"),
    path("puestos/", views_catalogs.position_admin, name="position_admin"),
    path("puestos/nueva/", views_catalogs.position_edit, name="position_edit_new"),
    path("puestos/<int:pk>/editar/", views_catalogs.position_edit, name="position_edit"),
    path("puestos/<int:pk>/borrar/", views_catalogs.position_delete, name="position_delete"),
    path("categorias/", views_catalogs.category_admin, name="category_admin"),
    path("categorias/<int:pk>/borrar/", views_catalogs.category_delete, name="category_delete"),
    path("escenarios/", views.scenario_admin, name="scenario_admin"),
    path("escenarios/nuevo/", views.scenario_create, name="scenario_create"),
    path("escenarios/<int:pk>/editar/", views.scenario_edit, name="scenario_edit"),
    path("ponderaciones/", views_weights.weight_admin, name="weight_admin"),
    path("ponderaciones/guardar/", views_weights.weight_save, name="weight_save"),
    path("ponderaciones/<int:pk>/editar/", views_weights.weight_edit, name="weight_edit"),
]
