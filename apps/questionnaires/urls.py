"""Rutas del motor/editor de cuestionarios."""

from django.urls import path

from . import views, views_blocks

app_name = "questionnaires"

urlpatterns = [
    path("admin/", views.admin_list, name="admin_list"),
    path("bloques/", views_blocks.block_admin, name="block_admin"),
    path("bloques/<int:pk>/eliminar/", views_blocks.block_delete, name="block_delete"),
    path("admin/<int:pk>/reordenar/", views.template_reorder, name="template_reorder"),
    path("admin/nuevo/", views.template_create, name="template_create"),
    path("admin/<int:pk>/", views.template_edit, name="template_edit"),
    path("admin/<int:pk>/descartar/", views.template_delete, name="template_delete"),
    path("admin/preguntas/<int:pk>/eliminar/", views.question_delete, name="question_delete"),
    path("admin/secciones/<int:pk>/eliminar/", views.section_delete, name="section_delete"),
    path("admin/escala/<int:pk>/eliminar/", views.scale_option_delete, name="scale_option_delete"),
]
