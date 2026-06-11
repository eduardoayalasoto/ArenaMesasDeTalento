"""Rutas de tableros."""

from django.urls import path

from . import views

app_name = "dashboards"

urlpatterns = [
    path("", views.HomeView.as_view(), name="home"),
    path("ayuda/", views.HelpView.as_view(), name="help"),
    path("mi-area/", views.my_area, name="my_area"),
    path("mesa-talento/", views.talent_table, name="talent_table"),
    path("persona/<int:pk>/", views.user_results, name="user_results"),
    path("avance-periodo/", views.period_progress, name="period_progress"),
    path("exportar/calificaciones.csv", views.export_scores_csv, name="export_scores_csv"),
]
