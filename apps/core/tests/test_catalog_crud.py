"""CRUD de Áreas, Posiciones y Categorías con drawer + cuestionario editable sin respuestas (spec 009)."""

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.urls import reverse

from apps.catalog.models import Area, Position, SeniorityLevel
from apps.core.services import catalogs, questionnaire_editor as editor
from apps.questionnaires.models import Category, QuestionnaireTemplate

User = get_user_model()


@pytest.fixture
def talento(db):
    return User.objects.create_user(
        email="t.crud@arena-analytics.com", password=None, full_name="Talento",
        role=User.Role.TALENTO, photo_data=b"x", photo_mime="image/jpeg",
    )


@pytest.mark.django_db
def test_area_crud_with_usage_guard(client, talento):
    client.force_login(talento)
    url = reverse("catalog:area_admin")
    client.post(url, {"code": "ds", "name": "Ciencia de datos", "is_active": "on"})
    area = Area.objects.get(code="DS")
    client.post(url, {"area": area.pk, "code": "DS", "name": "Data Science"})
    area.refresh_from_db()
    assert area.name == "Data Science" and area.is_active is False          # sin checkbox = inactiva
    assert client.get(url).status_code == 200
    # Clave repetida
    client.post(url, {"code": "ds", "name": "Otra"})
    assert Area.objects.filter(code="DS").count() == 1
    # Con una posición, no se borra; vacía, sí.
    level = SeniorityLevel.objects.create(code="JR", name="Junior", order=1)
    Position.objects.create(area=area, level=level, name="Analista de datos")
    client.post(reverse("catalog:area_delete", args=[area.pk]))
    assert Area.objects.filter(pk=area.pk).exists()
    Position.objects.all().delete()
    client.post(reverse("catalog:area_delete", args=[area.pk]))
    assert not Area.objects.filter(pk=area.pk).exists()


@pytest.mark.django_db
def test_position_crud_unique_and_delete_guard(client, talento):
    area = Area.objects.create(code="PM", name="Gestión de Proyectos")
    level = SeniorityLevel.objects.create(code="MID", name="Mid", order=2)
    client.force_login(talento)
    url = reverse("catalog:position_admin")
    client.post(url, {"area": area.pk, "level": level.pk, "name": "Project Manager", "is_active": "on"})
    pos = Position.objects.get(area=area, level=level)
    client.post(url, {"area": area.pk, "level": level.pk, "name": "Duplicada"})   # mismo área × nivel, sin id
    assert Position.objects.count() == 1 and Position.objects.get().name == "Project Manager"
    client.post(url, {"position": pos.pk, "area": area.pk, "level": level.pk, "name": "PM Sr", "is_active": "on"})
    pos.refresh_from_db()
    assert pos.name == "PM Sr"
    User.objects.create_user(email="x@arena-analytics.com", password=None, full_name="X", area=area, level=level)
    with pytest.raises(ValidationError, match="Desactívala"):
        catalogs.delete_position(pos)
    User.objects.exclude(pk=talento.pk).delete()
    client.post(reverse("catalog:position_delete", args=[pos.pk]))
    assert not Position.objects.exists()


@pytest.mark.django_db
def test_category_crud_and_delete_guard(client, talento):
    client.force_login(talento)
    url = reverse("catalog:category_admin")
    client.post(url, {"name": "Categoría nueva", "order": "9", "is_active": "on"})
    cat = Category.objects.get(name="Categoría nueva")
    client.post(url, {"category": cat.pk, "name": "Categoría editada", "order": "3", "is_active": "on"})
    cat.refresh_from_db()
    assert (cat.name, cat.order) == ("Categoría editada", 3)
    client.post(reverse("catalog:category_delete", args=[cat.pk]))
    assert not Category.objects.filter(pk=cat.pk).exists()
    general, _ = Category.objects.get_or_create(code=Category.GENERAL_CODE, defaults={"name": "General"})
    with pytest.raises(ValidationError, match="General"):
        catalogs.delete_category(general)


@pytest.mark.django_db
def test_published_template_is_editable_in_place_only_archived_is_read_only(ownership_template):
    assert ownership_template.status == QuestionnaireTemplate.Status.PUBLICADO
    assert editor.is_editable(ownership_template)
    ownership_template.status = QuestionnaireTemplate.Status.ARCHIVADO
    assert not editor.is_editable(ownership_template)
