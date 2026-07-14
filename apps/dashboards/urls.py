"""Rutas de tableros."""

from django.urls import path

from . import views

app_name = "dashboards"

urlpatterns = [
    path("", views.HomeView.as_view(), name="home"),
    path("ayuda/", views.HelpView.as_view(), name="help"),
    path("mi-area/", views.my_area, name="my_area"),
    path("mesa-talento/", views.talent_table, name="talent_table"),
    path("mesa-talento/persona/<int:pk>/", views.talent_person, name="talent_person"),
    path("mesa-talento/persona/<int:pk>/nota/", views.talent_note_autosave, name="talent_note_autosave"),
    path("mesa-talento/persona/<int:pk>/proyecto/<int:project_id>/revisado/", views.talent_mesa_project_toggle, name="talent_mesa_project_toggle"),
    path("mesa-talento/persona/<int:pk>/escenario/<str:tipo>/", views.talent_scenario_toggle, name="talent_scenario_toggle"),
    path("mesa-talento/persona/<int:pk>/responsable/agregar/", views.talent_responsable_add, name="talent_responsable_add"),
    path("mesa-talento/persona/<int:pk>/responsable/<int:rid>/quitar/", views.talent_responsable_remove, name="talent_responsable_remove"),
    path("persona/<int:pk>/", views.user_results, name="user_results"),
    path("retroalimentacion/", views.feedback_session_list, name="feedback_session_list"),
    path("retroalimentacion/<int:pk>/", views.feedback_session_detail, name="feedback_session_detail"),
    path("avance-periodo/", views.period_progress, name="period_progress"),
    path("exportar/calificaciones.csv", views.export_scores_csv, name="export_scores_csv"),
]
