"""Rutas de flujos de evaluación."""

from django.urls import path

from . import views

app_name = "evaluations"

urlpatterns = [
    # Ownership
    path("ownership/", views.ownership_list, name="ownership_list"),
    path("ownership/iniciar/<int:project_id>/", views.ownership_start, name="ownership_start"),
    path("ownership/lead/iniciar/", views.ownership_lead_start, name="ownership_lead_start"),
    path("ownership/<int:pk>/", views.ownership_view, name="ownership_view"),
    path("ownership/<int:pk>/editar/", views.ownership_edit, name="ownership_edit"),
    path("ownership/<int:pk>/evaluador/", views.ownership_set_evaluator, name="ownership_set_evaluator"),
    path("ownership/<int:pk>/evaluador/agregar/", views.ownership_add_evaluator, name="ownership_add_evaluator"),
    path("ownership/<int:pk>/evaluador/<int:user_pk>/quitar/", views.ownership_remove_evaluator, name="ownership_remove_evaluator"),
    path("ownership/<int:pk>/autosave/", views.ownership_autosave, name="ownership_autosave"),
    path("ownership/<int:pk>/guardar/", views.ownership_save, name="ownership_save"),
    path("ownership/<int:pk>/reabrir/", views.ownership_reopen, name="ownership_reopen"),
    # Validación (líder)
    path("ownership/validacion/", views.ownership_validation, name="ownership_validation"),
    # Entrega de Valor
    path("entrega-valor/", views.value_delivery_list, name="value_delivery_list"),
    path("entrega-valor/capturar/<int:project_id>/", views.value_delivery_capture, name="value_delivery_capture"),
    path("entrega-valor/validar/", views.value_delivery_review, name="value_delivery_review"),
    # Impacto Arena
    path("impacto-arena/", views.arena_impact, name="arena_impact"),
    path("impacto-arena/autosave/", views.arena_impact_autosave, name="arena_impact_autosave"),
]
