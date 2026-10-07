"""Rutas de Arena Learn (contracts/routes.md)."""

from django.urls import path

from . import views

app_name = "learning"

urlpatterns = [
    path("", views.my_courses, name="my_courses"),
    path("solicitar/", views.request_create, name="request_create"),
    path("registrar/", views.direct_create, name="direct_create"),
    path("por-aprobar/", views.approvals_inbox, name="approvals_inbox"),
    path("solicitudes/<int:pk>/", views.request_detail, name="request_detail"),
    path("solicitudes/<int:pk>/editar/", views.request_edit, name="request_edit"),
    path("solicitudes/<int:pk>/decision/", views.request_decide, name="request_decide"),
    path("solicitudes/<int:pk>/cancelar/", views.request_cancel, name="request_cancel"),
    path("solicitudes/<int:pk>/reasignar/", views.request_reassign, name="request_reassign"),
    path("solicitudes/<int:pk>/pago/", views.request_payment, name="request_payment"),
    path("solicitudes/<int:pk>/comprobante/", views.request_receipt, name="request_receipt"),
    path("solicitudes/<int:pk>/cerrar/", views.request_complete, name="request_complete"),
    path("solicitudes/<int:pk>/resena/", views.review_edit, name="review_edit"),
    path("solicitudes/<int:pk>/no-concluido/", views.request_not_completed, name="request_not_completed"),
    path("solicitudes/<int:pk>/promover/", views.catalog_promote, name="catalog_promote"),
    path("evidencias/<int:pk>/", views.evidence_file, name="evidence_file"),
    path("evidencias/<int:pk>/validar/", views.evidence_validate, name="evidence_validate"),
    path("evidencias/<int:pk>/reemplazar/", views.evidence_replace, name="evidence_replace"),
    path("catalogo/", views.catalog_list, name="catalog_list"),
    path("catalogo/nuevo/", views.catalog_edit, name="catalog_create"),
    path("catalogo/<int:pk>/", views.catalog_detail, name="catalog_detail"),
    path("catalogo/<int:pk>/editar/", views.catalog_edit, name="catalog_edit"),
    path("catalogo/<int:pk>/archivar/", views.catalog_archive, name="catalog_archive"),
    path("personas/", views.people_list, name="people_list"),
    path("personas/<int:pk>/", views.person_profile, name="person_profile"),
    path("cursos/<int:pk>/", views.course_public, name="course_public"),
    path("seguimiento/", views.tracking, name="tracking"),
    path("seguimiento/exportar/", views.tracking_export, name="tracking_export"),
    path("historico/nuevo/", views.historic_create, name="historic_create"),
    path("configuracion/", views.settings_edit, name="settings_edit"),
]
